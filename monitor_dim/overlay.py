from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PyQt6.QtWidgets import QWidget

from .logic import OverlayAction, OverlayIntent
from .winapi import make_window_click_through


class OverlayState(str, Enum):
    DIMMED = "dimmed"
    REVEALED = "revealed"
    RESTORE_PENDING = "restore_pending"
    TRANSITIONING = "transitioning"


class OverlayWindow(QWidget):
    def __init__(
        self,
        screen,
        opacity: float,
        fade_duration_ms: int,
        restore_delay_ms: int,
        color: str,
        exclude_from_capture: bool,
    ):
        super().__init__(None)
        self.screen = screen
        self.dim_opacity = opacity
        self.restore_delay_ms = restore_delay_ms
        self.exclude_from_capture = exclude_from_capture
        self.target_opacity = opacity
        self.state = OverlayState.DIMMED
        self.intent = OverlayIntent(desired_dimmed=True)
        self.preview_active = False

        self.restore_timer = QTimer(self)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self._restore_now)

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._finish_preview)

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_animation.setDuration(fade_duration_ms)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_animation.finished.connect(self._animation_finished)

        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setStyleSheet(f"background-color: {color};")
        self.sync_to_screen()
        self.setWindowOpacity(opacity)
        self.show()
        make_window_click_through(int(self.winId()), exclude_from_capture)

    def sync_to_screen(self) -> None:
        self.setGeometry(self.screen.geometry())

    def ensure_on_top(self) -> None:
        if not self.isVisible():
            self.show()
        make_window_click_through(int(self.winId()), self.exclude_from_capture)

    def update_settings(
        self,
        opacity: float,
        fade_duration_ms: int,
        restore_delay_ms: int,
        color: str,
        exclude_from_capture: bool,
    ) -> None:
        self.dim_opacity = opacity
        self.restore_delay_ms = restore_delay_ms
        self.fade_animation.setDuration(fade_duration_ms)
        self.setStyleSheet(f"background-color: {color};")
        self.exclude_from_capture = exclude_from_capture
        make_window_click_through(int(self.winId()), exclude_from_capture)
        if self.intent.desired_dimmed and not self.intent.restore_pending and not self.preview_active:
            self._animate_to(opacity)

    def set_should_dim(self, should_dim: bool, delayed: bool = True, animate: bool = True) -> None:
        action = self.intent.request(should_dim, delayed and self.restore_delay_ms > 0)
        if action is OverlayAction.NONE:
            return
        if action is OverlayAction.REVEAL:
            self.restore_timer.stop()
        if self.preview_active:
            return
        self._execute_action(action, animate)

    def reveal_temporarily(self) -> None:
        self.set_should_dim(False)

    def preview_at(self, opacity: float, duration_ms: int = 1400) -> None:
        self.preview_active = True
        self.restore_timer.stop()
        self._set_target(opacity, True)
        self.preview_timer.start(duration_ms)

    def close_overlay(self) -> None:
        self.restore_timer.stop()
        self.preview_timer.stop()
        self.fade_animation.stop()
        self.close()
        self.deleteLater()

    def _restore_now(self) -> None:
        self._execute_action(self.intent.timer_expired(), True)

    def _finish_preview(self) -> None:
        self.preview_active = False
        self._execute_action(self.intent.settle_after_preview(), True)

    def _execute_action(self, action: OverlayAction, animate: bool) -> None:
        if action is OverlayAction.REVEAL:
            self._set_target(0.0, animate)
        elif action is OverlayAction.SCHEDULE_DIM:
            self.restore_timer.start(self.restore_delay_ms)
            self.state = OverlayState.RESTORE_PENDING
        elif action is OverlayAction.DIM_NOW:
            self.restore_timer.stop()
            self._set_target(self.dim_opacity, animate)

    def _set_target(self, opacity: float, animate: bool) -> None:
        self.target_opacity = opacity
        if animate:
            self._animate_to(opacity)
        else:
            self.fade_animation.stop()
            self.setWindowOpacity(opacity)
            self.state = OverlayState.DIMMED if opacity > 0 else OverlayState.REVEALED

    def _animate_to(self, opacity: float) -> None:
        current = self.windowOpacity()
        self.target_opacity = opacity
        if abs(current - opacity) < 0.002:
            self.fade_animation.stop()
            self.setWindowOpacity(opacity)
            self._animation_finished()
            return
        self.fade_animation.stop()
        self.fade_animation.setStartValue(current)
        self.fade_animation.setEndValue(opacity)
        self.state = OverlayState.TRANSITIONING
        self.fade_animation.start()

    def _animation_finished(self) -> None:
        self.state = OverlayState.DIMMED if self.target_opacity > 0 else OverlayState.REVEALED
