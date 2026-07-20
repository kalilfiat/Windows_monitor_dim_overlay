from __future__ import annotations

import logging
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QCursor, QGuiApplication
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import ConfigStore
from .logic import dim_targets
from .models import AppMode, Settings
from .overlay import OverlayWindow
from .settings_window import ScreenDescriptor, SettingsWindow
from .theme import app_icon
from .winapi import GlobalHotkeyManager, foreground_window, set_launch_at_startup

LOGGER = logging.getLogger(__name__)
TOGGLE_HOTKEY_ID = 1
PEEK_HOTKEY_ID = 2


class OverlayController(QObject):
    def __init__(self, app: QApplication, project_root: Path):
        super().__init__()
        self.app = app
        self.project_root = project_root
        self.store = ConfigStore(legacy_path=project_root / "monitor_dim_overlay_config.json")
        self.settings = self.store.load()
        self.overlays: dict[str, OverlayWindow] = {}
        self.settings_window: SettingsWindow | None = None
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_enabled_action: QAction | None = None
        self.mode_actions: dict[AppMode, QAction] = {}
        self.opacity_actions: dict[float, QAction] = {}
        self._connected_screen_ids: set[int] = set()
        self._cleanup_done = False
        self._peek_active = False
        self._last_activity_monitor: str | None = None
        self._last_activity_at = 0.0

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.update_overlays)
        self.poll_timer.setInterval(self.settings.poll_interval_ms)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.rebuild_overlays)

        self.peek_timer = QTimer(self)
        self.peek_timer.setSingleShot(True)
        self.peek_timer.timeout.connect(self._finish_peek)

        self.hotkeys = GlobalHotkeyManager()
        self.app.installNativeEventFilter(self.hotkeys)
        self.app.screenAdded.connect(self.schedule_rebuild)
        self.app.screenRemoved.connect(self.schedule_rebuild)
        if hasattr(self.app, "primaryScreenChanged"):
            self.app.primaryScreenChanged.connect(self.schedule_rebuild)

        self._create_tray()
        self._configure_hotkeys(notify=True)
        self.rebuild_overlays()
        self.poll_timer.start()
        QTimer.singleShot(0, self._complete_startup)
        self.app.aboutToQuit.connect(self.cleanup)

    def _create_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            raise RuntimeError("La bandeja del sistema no está disponible")
        menu = QMenu()
        self.tray_enabled_action = QAction("Overlays activados", self)
        self.tray_enabled_action.setCheckable(True)
        self.tray_enabled_action.setChecked(self.settings.enabled)
        self.tray_enabled_action.triggered.connect(self.set_enabled)
        menu.addAction(self.tray_enabled_action)

        open_settings = QAction("Abrir preferencias…", self)
        open_settings.triggered.connect(self.show_settings)
        menu.addAction(open_settings)
        menu.addSeparator()

        mode_menu = menu.addMenu("Modo")
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        for mode in AppMode:
            action = QAction(mode.label, self)
            action.setCheckable(True)
            action.setChecked(self.settings.mode is mode)
            action.triggered.connect(lambda _checked=False, selected=mode: self.set_mode(selected))
            mode_group.addAction(action)
            mode_menu.addAction(action)
            self.mode_actions[mode] = action

        opacity_menu = menu.addMenu("Intensidad")
        opacity_group = QActionGroup(self)
        opacity_group.setExclusive(True)
        for value in (0.70, 0.85, 0.95):
            action = QAction(f"{round(value * 100)}%", self)
            action.setCheckable(True)
            action.setChecked(abs(self.settings.opacity - value) < 0.001)
            action.triggered.connect(lambda _checked=False, opacity=value: self.set_opacity(opacity))
            opacity_group.addAction(action)
            opacity_menu.addAction(action)
            self.opacity_actions[value] = action

        peek = QAction("Revelar temporalmente", self)
        peek.triggered.connect(self.peek)
        menu.addAction(peek)
        menu.addSeparator()
        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.app.quit)
        menu.addAction(exit_action)

        self.tray_icon = QSystemTrayIcon(app_icon(64), self.app)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
        self._sync_tray()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_enabled()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_settings()

    def show_settings(self) -> None:
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
            self.settings_window.settingsApplied.connect(self.apply_settings)
            self.settings_window.previewRequested.connect(self.preview_monitor)
            self.settings_window.visibilityChanged.connect(lambda _visible: self.update_overlays())
        self.settings_window.show_settings(self.settings, self.screen_descriptors())
        self.update_overlays()

    def _complete_startup(self) -> None:
        self.rebuild_overlays()
        for overlay in self.overlays.values():
            overlay.ensure_on_top()
        self.update_overlays(animate=False)
        if self.settings.show_settings_on_startup:
            QTimer.singleShot(120, self.show_settings)

    def screen_descriptors(self) -> list[ScreenDescriptor]:
        primary = QGuiApplication.primaryScreen()
        result = []
        for screen in QGuiApplication.screens():
            geometry = screen.geometry()
            model = " ".join(part for part in (screen.manufacturer(), screen.model()) if part).strip()
            label = model or screen.name() or "Monitor"
            result.append(
                ScreenDescriptor(
                    name=self._screen_name(screen),
                    label=label,
                    primary=screen is primary,
                    resolution=f"{geometry.width()} × {geometry.height()}  ·  {screen.devicePixelRatio():g}×",
                )
            )
        return result

    def schedule_rebuild(self, *_args) -> None:
        self.refresh_timer.start(250)

    def rebuild_overlays(self) -> None:
        screens = QGuiApplication.screens()
        primary = QGuiApplication.primaryScreen()
        eligible: dict[str, object] = {}
        for screen in screens:
            self._connect_screen(screen)
            name = self._screen_name(screen)
            pref = self.settings.monitor_preference(name)
            if pref.enabled and (screen is not primary or self.settings.dim_primary):
                eligible[name] = screen

        for name in list(self.overlays):
            if name not in eligible:
                self.overlays.pop(name).close_overlay()

        for name, screen in eligible.items():
            pref = self.settings.monitor_preference(name)
            opacity = pref.opacity if pref.opacity is not None else self.settings.opacity
            overlay = self.overlays.get(name)
            if overlay is None:
                overlay = OverlayWindow(
                    screen,
                    opacity,
                    self.settings.fade_duration_ms,
                    self.settings.restore_delay_ms,
                    self.settings.dim_color,
                    self.settings.exclude_from_capture,
                )
                self.overlays[name] = overlay
            else:
                overlay.screen = screen
                overlay.sync_to_screen()
                overlay.update_settings(
                    opacity,
                    self.settings.fade_duration_ms,
                    self.settings.restore_delay_ms,
                    self.settings.dim_color,
                    self.settings.exclude_from_capture,
                )
        self.update_overlays(animate=False)

    def _connect_screen(self, screen) -> None:
        identity = id(screen)
        if identity in self._connected_screen_ids:
            return
        self._connected_screen_ids.add(identity)
        for signal_name in ("geometryChanged", "availableGeometryChanged", "logicalDotsPerInchChanged", "orientationChanged"):
            signal = getattr(screen, signal_name, None)
            if signal is not None:
                signal.connect(self.schedule_rebuild)

    def update_overlays(self, animate: bool = True) -> None:
        if not self.overlays:
            return
        reveal_all = self._peek_active
        activity_monitor: str | None = None
        foreground = None
        needs_foreground = (
            self.settings.mode is AppMode.ACTIVE_WINDOW
            or self.settings.pause_fullscreen
            or bool(self.settings.excluded_apps)
        )
        if needs_foreground:
            foreground = foreground_window()
            if foreground and foreground.process_name in self.settings.excluded_apps:
                reveal_all = True
            if foreground and self.settings.pause_fullscreen and foreground.fullscreen:
                reveal_all = True
        if self.settings.mode is AppMode.CURSOR:
            screen = QGuiApplication.screenAt(QCursor.pos())
            activity_monitor = self._screen_name(screen) if screen else None
        elif self.settings.mode is AppMode.ACTIVE_WINDOW:
            if foreground:
                center = QPoint(
                    (foreground.monitor_rect[0] + foreground.monitor_rect[2]) // 2,
                    (foreground.monitor_rect[1] + foreground.monitor_rect[3]) // 2,
                )
                screen = QGuiApplication.screenAt(center)
                if screen:
                    activity_monitor = self._screen_name(screen)
                    self._last_activity_monitor = activity_monitor
                    self._last_activity_at = time.monotonic()
            if activity_monitor is None and time.monotonic() - self._last_activity_at < 0.8:
                activity_monitor = self._last_activity_monitor
        targets = dim_targets(
            list(self.overlays),
            self.settings.mode,
            activity_monitor,
            self.settings.enabled,
            reveal_all,
        )
        settings_monitor = self._settings_monitor_name()
        if settings_monitor in targets:
            targets[settings_monitor] = False
        for name, should_dim in targets.items():
            self.overlays[name].set_should_dim(should_dim, delayed=animate, animate=animate)

    def _settings_monitor_name(self) -> str | None:
        if self.settings_window is None or not self.settings_window.isVisible():
            return None
        center = self.settings_window.frameGeometry().center()
        screen = QGuiApplication.screenAt(center)
        return self._screen_name(screen) if screen else None

    def preview_monitor(self, monitor_name: str, opacity: float) -> None:
        overlay = self.overlays.get(monitor_name)
        if overlay is None:
            self._notify(
                "Vista previa no disponible",
                "Activá este monitor y aplicá los cambios antes de probar su intensidad.",
                warning=True,
            )
            return
        overlay.preview_at(max(0.10, min(0.98, opacity)))

    def set_enabled(self, enabled: bool) -> None:
        self.settings.enabled = bool(enabled)
        self.store.save(self.settings)
        self._sync_tray()
        self.update_overlays()

    def toggle_enabled(self) -> None:
        self.set_enabled(not self.settings.enabled)

    def set_mode(self, mode: AppMode) -> None:
        self.settings.mode = mode
        self.settings.active_profile = "Personalizado"
        self.store.save(self.settings)
        self._sync_tray()
        self.update_overlays()

    def set_opacity(self, opacity: float) -> None:
        self.settings.opacity = opacity
        self.settings.active_profile = "Personalizado"
        self.store.save(self.settings)
        self._sync_tray()
        self.rebuild_overlays()

    def peek(self) -> None:
        self._peek_active = True
        self.peek_timer.start(self.settings.peek_duration_ms)
        self.update_overlays()

    def _finish_peek(self) -> None:
        self._peek_active = False
        self.update_overlays()

    def apply_settings(self, settings: Settings) -> None:
        previous_startup = self.settings.launch_at_startup
        self.settings = Settings.from_dict(settings.to_dict())
        self.store.save(self.settings)
        if previous_startup != self.settings.launch_at_startup:
            success = set_launch_at_startup(self.settings.launch_at_startup, self.project_root / "monitor_dim_overlay.py")
            if not success:
                self._notify("Inicio con Windows", "No se pudo modificar el inicio automático.")
        self.poll_timer.setInterval(self.settings.poll_interval_ms)
        self._configure_hotkeys(notify=True)
        self._sync_tray()
        self.rebuild_overlays()
        self._notify("Preferencias actualizadas", "La nueva configuración ya está activa.")

    def _configure_hotkeys(self, notify: bool) -> None:
        failures = []
        ok, error = self.hotkeys.register(TOGGLE_HOTKEY_ID, self.settings.toggle_hotkey, self.toggle_enabled)
        if not ok:
            failures.append(error)
        ok, error = self.hotkeys.register(PEEK_HOTKEY_ID, self.settings.peek_hotkey, self.peek)
        if not ok:
            failures.append(error)
        if failures and notify:
            self._notify("Atajo no disponible", "\n".join(failures), warning=True)

    def _sync_tray(self) -> None:
        if self.tray_enabled_action:
            self.tray_enabled_action.blockSignals(True)
            self.tray_enabled_action.setChecked(self.settings.enabled)
            self.tray_enabled_action.blockSignals(False)
        for mode, action in self.mode_actions.items():
            action.setChecked(self.settings.mode is mode)
        for opacity, action in self.opacity_actions.items():
            action.setChecked(abs(self.settings.opacity - opacity) < 0.001)
        if self.tray_icon:
            state = "Activo" if self.settings.enabled else "Pausado"
            self.tray_icon.setToolTip(f"Monitor Dim Overlay · {state} · {self.settings.mode.label}")

    def _notify(self, title: str, message: str, warning: bool = False) -> None:
        if self.tray_icon and QSystemTrayIcon.supportsMessages():
            icon = QSystemTrayIcon.MessageIcon.Warning if warning else QSystemTrayIcon.MessageIcon.Information
            self.tray_icon.showMessage(title, message, icon, 4500)
        if warning:
            LOGGER.warning("%s: %s", title, message)

    @staticmethod
    def _screen_name(screen) -> str:
        return screen.name() if screen is not None and screen.name() else "unknown-monitor"

    def cleanup(self) -> None:
        if self._cleanup_done:
            return
        self._cleanup_done = True
        self.poll_timer.stop()
        self.refresh_timer.stop()
        self.peek_timer.stop()
        self.hotkeys.unregister_all()
        for overlay in list(self.overlays.values()):
            overlay.close_overlay()
        self.overlays.clear()
        if self.settings_window:
            self.settings_window.close()
        if self.tray_icon:
            self.tray_icon.hide()
