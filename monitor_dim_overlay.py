import sys
import ctypes
import ctypes.wintypes
import json
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import (
    QAbstractNativeEventFilter,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PyQt6.QtGui import QAction, QActionGroup, QCursor, QGuiApplication
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon, QWidget


# Easy-to-change prototype settings.
OVERLAY_OPACITY = 0.90
RESTORE_DELAY_MS = 1000
POLL_INTERVAL_MS = 100
FADE_DURATION_MS = 180
TOGGLE_HOTKEY = "F9"
HOTKEY_ID = 1
WM_HOTKEY = 0x0312
VK_F9 = 0x78
CONFIG_PATH = Path(__file__).with_name("monitor_dim_overlay_config.json")
OPACITY_OPTIONS = {
    "Opacity 70%": 0.70,
    "Opacity 85%": 0.85,
    "Opacity 95%": 0.95,
}


def load_opacity_setting() -> float:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        opacity = float(data.get("opacity", OVERLAY_OPACITY))
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return OVERLAY_OPACITY

    if 0.0 <= opacity <= 1.0:
        return opacity
    return OVERLAY_OPACITY


def save_opacity_setting(opacity: float) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps({"opacity": opacity}, indent=2), encoding="utf-8")
    except OSError:
        pass


class OverlayWindow(QWidget):
    def __init__(self, screen, opacity: float):
        super().__init__(None)
        self.screen = screen
        self.opacity = opacity
        self.mouse_inside = False
        self.target_opacity = opacity

        self.restore_timer = QTimer(self)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self.restore_overlay)

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_animation.setDuration(FADE_DURATION_MS)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setWindowFlags(flags)

        self.setStyleSheet("background-color: black;")
        self.setWindowOpacity(self.opacity)
        self.sync_to_screen()
        self.show()

    def sync_to_screen(self) -> None:
        geometry = self.screen.geometry()
        self.setGeometry(geometry)

    def animate_to(self, target_opacity: float) -> None:
        current_opacity = self.windowOpacity()
        if abs(current_opacity - target_opacity) < 0.001:
            self.fade_animation.stop()
            self.setWindowOpacity(target_opacity)
            self.target_opacity = target_opacity
            return

        self.fade_animation.stop()
        self.fade_animation.setStartValue(current_opacity)
        self.fade_animation.setEndValue(target_opacity)
        self.target_opacity = target_opacity
        self.fade_animation.start()

    def set_overlay_visible(self, visible: bool, animate: bool = True) -> None:
        target = self.opacity if visible else 0.0
        if animate:
            self.animate_to(target)
        else:
            self.fade_animation.stop()
            self.target_opacity = target
            self.setWindowOpacity(target)

    def hide_overlay_immediately(self) -> None:
        self.restore_timer.stop()
        self.set_overlay_visible(False, animate=True)

    def schedule_restore(self) -> None:
        self.restore_timer.start(RESTORE_DELAY_MS)

    def restore_overlay(self) -> None:
        if not self.mouse_inside:
            self.set_overlay_visible(True, animate=True)

    def set_selected_opacity(self, opacity: float, visible_now: bool) -> None:
        self.opacity = opacity
        self.set_overlay_visible(visible_now, animate=True)


class OverlayController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.selected_opacity = load_opacity_setting()
        self.overlays_enabled = True
        self.overlays: Dict[str, OverlayWindow] = {}
        self.primary_screen = QGuiApplication.primaryScreen()
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.opacity_actions: Dict[float, QAction] = {}

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.update_mouse_tracking)
        self.poll_timer.start(POLL_INTERVAL_MS)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.rebuild_overlays)

        self.app.screenAdded.connect(self.schedule_rebuild)
        self.app.screenRemoved.connect(self.schedule_rebuild)

        self.hotkey_filter: Optional[GlobalHotkeyFilter] = None
        self.install_hotkey()
        self.create_tray_icon()
        self.rebuild_overlays()

    def install_hotkey(self) -> None:
        self.hotkey_filter = GlobalHotkeyFilter(self.toggle_overlays)
        self.app.installNativeEventFilter(self.hotkey_filter)
        if not self.hotkey_filter.register():
            raise RuntimeError(f"Could not register global hotkey {TOGGLE_HOTKEY}")

    def create_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            raise RuntimeError("System tray is not available on this system")

        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        tray_menu = QMenu()
        opacity_group = QActionGroup(self)
        opacity_group.setExclusive(True)

        for label, value in OPACITY_OPTIONS.items():
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(abs(value - self.selected_opacity) < 0.001)
            action.triggered.connect(lambda checked, opacity=value: self.set_selected_opacity(opacity))
            opacity_group.addAction(action)
            tray_menu.addAction(action)
            self.opacity_actions[value] = action

        tray_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_application)
        tray_menu.addAction(exit_action)

        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Monitor Dim Overlay")
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def schedule_rebuild(self, *_args) -> None:
        self.refresh_timer.start(250)

    def rebuild_overlays(self) -> None:
        current_screens = QGuiApplication.screens()
        self.primary_screen = QGuiApplication.primaryScreen()
        current_names = {screen.name() for screen in current_screens}

        for name in list(self.overlays.keys()):
            if name not in current_names or self.overlays[name].screen == self.primary_screen:
                self.overlays[name].close()
                del self.overlays[name]

        for screen in current_screens:
            if screen == self.primary_screen:
                continue

            name = screen.name()
            overlay = self.overlays.get(name)
            if overlay is None:
                overlay = OverlayWindow(screen, self.selected_opacity)
                self.overlays[name] = overlay
            else:
                overlay.screen = screen
                overlay.sync_to_screen()
                overlay.opacity = self.selected_opacity

            overlay.set_overlay_visible(self.overlays_enabled and not overlay.mouse_inside, animate=False)

    def toggle_overlays(self) -> None:
        self.overlays_enabled = not self.overlays_enabled
        for overlay in self.overlays.values():
            overlay.restore_timer.stop()
            overlay.set_overlay_visible(self.overlays_enabled and not overlay.mouse_inside, animate=True)

    def set_selected_opacity(self, opacity: float) -> None:
        if abs(self.selected_opacity - opacity) < 0.001:
            return

        self.selected_opacity = opacity
        save_opacity_setting(opacity)

        for value, action in self.opacity_actions.items():
            action.setChecked(abs(value - opacity) < 0.001)

        for overlay in self.overlays.values():
            visible_now = self.overlays_enabled and not overlay.mouse_inside
            overlay.set_selected_opacity(opacity, visible_now)

    def update_mouse_tracking(self) -> None:
        cursor_pos = QCursorCompat.pos()
        for overlay in self.overlays.values():
            inside = overlay.geometry().contains(cursor_pos)
            if inside == overlay.mouse_inside:
                continue

            overlay.mouse_inside = inside
            if inside:
                overlay.hide_overlay_immediately()
            elif self.overlays_enabled:
                overlay.schedule_restore()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.ApplicationStateChange and self.overlays_enabled:
            self.update_mouse_tracking()
        return super().eventFilter(watched, event)

    def cleanup(self) -> None:
        for overlay in self.overlays.values():
            overlay.restore_timer.stop()
            overlay.fade_animation.stop()
            overlay.close()

        if self.tray_icon is not None:
            self.tray_icon.hide()

        if self.hotkey_filter is not None:
            self.hotkey_filter.unregister()

    def exit_application(self) -> None:
        self.cleanup()
        self.app.quit()


class QCursorCompat:
    @staticmethod
    def pos() -> QPoint:
        return QCursor.pos()


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.user32 = ctypes.windll.user32
        self.registered = False

    def register(self) -> bool:
        self.registered = bool(self.user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_F9))
        return self.registered

    def unregister(self) -> None:
        if self.registered:
            self.user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0

        msg = ctypes.wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            self.callback()
            return True, 0

        return False, 0


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Monitor Dim Overlay")
    app.setQuitOnLastWindowClosed(False)

    controller = OverlayController(app)
    app.installEventFilter(controller)

    exit_code = app.exec()
    controller.cleanup()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
