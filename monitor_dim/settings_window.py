from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QRectF, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QAbstractButton,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .models import AppMode, FocusProfile, MonitorPreference, Settings
from .theme import ACCENT, APP_STYLESHEET, app_icon


@dataclass(frozen=True)
class ScreenDescriptor:
    name: str
    label: str
    primary: bool
    resolution: str


class Card(QFrame):
    def __init__(self, title: str, description: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(18, 16, 18, 18)
        self.content.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        self.content.addWidget(title_label)
        if description:
            label = QLabel(description)
            label.setObjectName("Muted")
            label.setWordWrap(True)
            self.content.addWidget(label)


class LabeledSlider(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, minimum: int, maximum: int, suffix: str):
        super().__init__()
        self.suffix = suffix
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.value_label = QLabel()
        self.value_label.setObjectName("Accent")
        self.value_label.setMinimumWidth(58)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._changed)

    def _changed(self, value: int) -> None:
        self.value_label.setText(f"{value}{self.suffix}")
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(48, 26)
        self.setAccessibleName("Interruptor")

    def sizeHint(self) -> QSize:
        return QSize(48, 26)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        if not self.isEnabled():
            track = QColor("#1B2A3D")
            knob = QColor("#63758A")
        elif self.isChecked():
            track = QColor(ACCENT)
            knob = QColor("#FFFFFF")
        else:
            track = QColor("#29405C")
            knob = QColor("#B8C5D5")
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 2, 48, 22), 11, 11)
        x = 26 if self.isChecked() else 4
        painter.setBrush(knob)
        painter.drawEllipse(QRectF(x, 4, 18, 18))


def toggle_setting(title: str, description: str, control: ToggleSwitch) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 3, 0, 3)
    text = QVBoxLayout()
    text.setSpacing(2)
    title_label = QLabel(title)
    title_label.setStyleSheet("font-weight: 600;")
    text.addWidget(title_label)
    if description:
        description_label = QLabel(description)
        description_label.setObjectName("Muted")
        description_label.setWordWrap(True)
        text.addWidget(description_label)
    layout.addLayout(text, 1)
    layout.addWidget(control)
    return row


class MonitorRow(QFrame):
    previewRequested = pyqtSignal(str, float)

    def __init__(
        self,
        screen: ScreenDescriptor,
        preference: MonitorPreference,
        global_opacity: float,
        primary_allowed: bool,
    ):
        super().__init__()
        self.setObjectName("MonitorRow")
        self.screen = screen
        self.global_opacity = global_opacity
        self._primary_allowed = primary_allowed
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(app_icon(48).pixmap(30, 30))
        names = QVBoxLayout()
        name = QLabel(screen.label)
        name.setStyleSheet("font-weight: 700;")
        detail = QLabel(screen.resolution + ("  ·  Principal" if screen.primary else ""))
        detail.setObjectName("Muted")
        names.addWidget(name)
        names.addWidget(detail)
        self.enabled_toggle = ToggleSwitch(preference.enabled)
        header.addWidget(icon)
        header.addLayout(names, 1)
        header.addWidget(QLabel("Oscurecer"))
        header.addWidget(self.enabled_toggle)
        layout.addLayout(header)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #1D3049;")
        layout.addWidget(line)

        controls = QGridLayout()
        controls.setHorizontalSpacing(14)
        self.custom_toggle = ToggleSwitch(preference.opacity is not None)
        controls.addWidget(QLabel("Intensidad individual"), 0, 0)
        controls.addWidget(self.custom_toggle, 0, 1)
        self.opacity_slider = LabeledSlider(10, 98, "%")
        self.opacity_slider.setValue(round((preference.opacity or global_opacity) * 100))
        controls.addWidget(self.opacity_slider, 1, 0, 1, 2)
        self.preview_button = QPushButton("Probar en pantalla")
        self.preview_button.setToolTip("Muestra este nivel durante 1,4 segundos")
        controls.addWidget(self.preview_button, 1, 2)
        self.source_label = QLabel()
        self.source_label.setObjectName("Muted")
        controls.addWidget(self.source_label, 2, 0, 1, 3)
        layout.addLayout(controls)

        self.custom_toggle.toggled.connect(self._sync_controls)
        self.enabled_toggle.toggled.connect(self._sync_controls)
        self.opacity_slider.slider.sliderPressed.connect(lambda: self.custom_toggle.setChecked(True))
        self.preview_button.clicked.connect(
            lambda: self.previewRequested.emit(self.screen.name, self.effective_opacity())
        )
        self.set_primary_allowed(primary_allowed)

    def set_primary_allowed(self, allowed: bool) -> None:
        self._primary_allowed = allowed
        self._sync_controls()

    def set_global_opacity(self, opacity: float) -> None:
        self.global_opacity = opacity
        if not self.custom_toggle.isChecked():
            self.opacity_slider.setValue(round(opacity * 100))
        self._sync_controls()

    def preference(self) -> MonitorPreference:
        opacity = self.opacity_slider.value() / 100 if self.custom_toggle.isChecked() else None
        return MonitorPreference(self.enabled_toggle.isChecked(), opacity)

    def effective_opacity(self) -> float:
        return self.opacity_slider.value() / 100 if self.custom_toggle.isChecked() else self.global_opacity

    def _sync_controls(self) -> None:
        protected = self.screen.primary and not self._primary_allowed
        active = self.enabled_toggle.isChecked() and not protected
        self.enabled_toggle.setEnabled(not protected)
        self.custom_toggle.setEnabled(active)
        self.opacity_slider.setEnabled(active)
        self.preview_button.setEnabled(active)
        if protected:
            self.source_label.setText("Monitor principal protegido")
        elif not self.enabled_toggle.isChecked():
            self.source_label.setText("Overlay desactivado para esta pantalla")
        elif self.custom_toggle.isChecked():
            self.source_label.setText("Usa una intensidad propia")
        else:
            self.source_label.setText(f"Usa la intensidad general: {round(self.global_opacity * 100)}%")


class SettingsWindow(QMainWindow):
    settingsApplied = pyqtSignal(object)
    previewRequested = pyqtSignal(str, float)
    visibilityChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor Dim Overlay — Preferencias")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(900, 680)
        self.resize(980, 740)
        self.setStyleSheet(APP_STYLESHEET)
        self._settings = Settings()
        self._screens: list[ScreenDescriptor] = []
        self._monitor_rows: dict[str, MonitorRow] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 20, 14, 18)
        brand = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(app_icon(64).pixmap(38, 38))
        brand_text = QVBoxLayout()
        title = QLabel("Monitor Dim")
        title.setStyleSheet("font-size: 12pt; font-weight: 700;")
        subtitle = QLabel("FOCUS CONTROL")
        subtitle.setObjectName("Accent")
        subtitle.setStyleSheet(f"color: {ACCENT}; font-size: 7pt; font-weight: 700;")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addWidget(icon)
        brand.addLayout(brand_text)
        side_layout.addLayout(brand)
        side_layout.addSpacing(20)
        self.navigation = QListWidget()
        for label in ("General", "Monitores", "Automatización", "Aplicaciones", "Acerca de"):
            self.navigation.addItem(label)
        self.navigation.setCurrentRow(0)
        side_layout.addWidget(self.navigation, 1)
        version = QLabel("VERSION 2.1.2")
        version.setObjectName("Muted")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(version)
        main.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 20)
        content_layout.setSpacing(16)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._general_page())
        self.stack.addWidget(self._monitors_page())
        self.stack.addWidget(self._automation_page())
        self.stack.addWidget(self._applications_page())
        self.stack.addWidget(self._about_page())
        content_layout.addWidget(self.stack, 1)

        footer = QHBoxLayout()
        defaults = QPushButton("Restaurar valores")
        defaults.clicked.connect(self._restore_defaults)
        cancel = QPushButton("Cerrar")
        cancel.clicked.connect(self.hide)
        self.save_status = QLabel("")
        self.save_status.setObjectName("Accent")
        self.apply_button = QPushButton("Aplicar cambios")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self._apply)
        footer.addWidget(defaults)
        footer.addWidget(self.save_status)
        footer.addStretch()
        footer.addWidget(cancel)
        footer.addWidget(self.apply_button)
        content_layout.addLayout(footer)
        main.addWidget(content, 1)
        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.opacity_slider.valueChanged.connect(self._sync_global_opacity)

    def _page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        outer.addWidget(heading)
        detail = QLabel(subtitle)
        detail.setObjectName("Muted")
        outer.addWidget(detail)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        body = QWidget()
        body.setObjectName("PageBody")
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 16, 8, 8)
        body_layout.setSpacing(14)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        return page, body_layout

    def _general_page(self) -> QWidget:
        page, layout = self._page("Control de enfoque", "Elegí cómo se adaptan los monitores a tu forma de trabajar.")
        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QGridLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_title = QLabel("Oscurecimiento inteligente")
        hero_title.setStyleSheet("font-size: 14pt; font-weight: 700;")
        hero_description = QLabel("Reduce el ruido visual sin bloquear el mouse ni interrumpir tus ventanas.")
        hero_description.setObjectName("Muted")
        self.enabled_check = ToggleSwitch()
        enabled_row = QHBoxLayout()
        enabled_label = QLabel("Sistema activo")
        enabled_label.setStyleSheet("font-weight: 650;")
        enabled_row.addWidget(enabled_label)
        enabled_row.addWidget(self.enabled_check)
        hero_layout.addWidget(hero_title, 0, 0)
        hero_layout.addWidget(hero_description, 1, 0)
        hero_layout.addLayout(enabled_row, 0, 1, 2, 1)
        layout.addWidget(hero)

        profile = Card("Perfiles", "Cargá un comportamiento predefinido o guardá tu combinación actual.")
        profile_row = QHBoxLayout()
        self.profile_combo = QComboBox()
        load_profile = QPushButton("Cargar")
        save_profile = QPushButton("Guardar como…")
        load_profile.clicked.connect(self._load_profile)
        save_profile.clicked.connect(self._save_profile)
        profile_row.addWidget(self.profile_combo, 1)
        profile_row.addWidget(load_profile)
        profile_row.addWidget(save_profile)
        profile.content.addLayout(profile_row)
        layout.addWidget(profile)

        behavior = Card("Comportamiento principal")
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.addWidget(QLabel("Modo"), 0, 0)
        self.mode_combo = QComboBox()
        for mode in AppMode:
            self.mode_combo.addItem(mode.label, mode.value)
        grid.addWidget(self.mode_combo, 0, 1)
        self.mode_help = QLabel()
        self.mode_help.setObjectName("Muted")
        self.mode_help.setWordWrap(True)
        grid.addWidget(self.mode_help, 1, 1)
        grid.addWidget(QLabel("Intensidad general"), 2, 0)
        self.opacity_slider = LabeledSlider(10, 98, "%")
        grid.addWidget(self.opacity_slider, 2, 1)
        grid.addWidget(QLabel("Color del overlay"), 3, 0)
        self.color_button = QPushButton("Seleccionar color")
        self.color_button.clicked.connect(self._choose_color)
        grid.addWidget(self.color_button, 3, 1)
        behavior.content.addLayout(grid)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_help)
        layout.addWidget(behavior)
        layout.addStretch()
        return page

    def _monitors_page(self) -> QWidget:
        page, layout = self._page(
            "Monitores",
            "Cada pantalla puede usar la intensidad general o una intensidad propia que podés probar antes de guardar.",
        )
        self.monitors_container = QWidget()
        self.monitors_layout = QVBoxLayout(self.monitors_container)
        self.monitors_layout.setContentsMargins(0, 0, 0, 0)
        self.monitors_layout.setSpacing(12)
        layout.addWidget(self.monitors_container)
        advanced = Card("Opciones de pantalla")
        self.dim_primary_check = ToggleSwitch()
        self.capture_check = ToggleSwitch()
        advanced.content.addWidget(
            toggle_setting(
                "Permitir oscurecer el monitor principal",
                "Activado por defecto: todos los monitores responden al cursor o a Smart Focus.",
                self.dim_primary_check,
            )
        )
        advanced.content.addWidget(
            toggle_setting(
                "Ocultar overlays en capturas compatibles",
                "Usa la protección de contenido de Windows cuando está disponible.",
                self.capture_check,
            )
        )
        self.dim_primary_check.toggled.connect(self._refresh_monitor_availability)
        layout.addWidget(advanced)
        layout.addStretch()
        return page

    def _automation_page(self) -> QWidget:
        page, layout = self._page("Automatización", "Ajustá tiempos, atajos y comportamiento con aplicaciones fullscreen.")
        timing = Card("Transiciones")
        grid = QGridLayout()
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10_000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setSuffix(" ms")
        self.fade_spin = QSpinBox()
        self.fade_spin.setRange(0, 2000)
        self.fade_spin.setSingleStep(20)
        self.fade_spin.setSuffix(" ms")
        grid.addWidget(QLabel("Espera antes de oscurecer"), 0, 0)
        grid.addWidget(self.delay_spin, 0, 1)
        grid.addWidget(QLabel("Duración del fade"), 1, 0)
        grid.addWidget(self.fade_spin, 1, 1)
        timing.content.addLayout(grid)
        layout.addWidget(timing)

        shortcuts = Card("Atajos globales", "Formatos compatibles: F9, Ctrl+F9, Ctrl+Shift+F9.")
        shortcut_grid = QGridLayout()
        self.toggle_hotkey_edit = QLineEdit()
        self.peek_hotkey_edit = QLineEdit()
        self.peek_duration_spin = QSpinBox()
        self.peek_duration_spin.setRange(500, 30_000)
        self.peek_duration_spin.setSingleStep(500)
        self.peek_duration_spin.setSuffix(" ms")
        shortcut_grid.addWidget(QLabel("Activar / desactivar"), 0, 0)
        shortcut_grid.addWidget(self.toggle_hotkey_edit, 0, 1)
        shortcut_grid.addWidget(QLabel("Vista temporal"), 1, 0)
        shortcut_grid.addWidget(self.peek_hotkey_edit, 1, 1)
        shortcut_grid.addWidget(QLabel("Duración de la vista"), 2, 0)
        shortcut_grid.addWidget(self.peek_duration_spin, 2, 1)
        shortcuts.content.addLayout(shortcut_grid)
        layout.addWidget(shortcuts)

        system = Card("Integración con Windows")
        self.open_settings_check = ToggleSwitch()
        self.startup_check = ToggleSwitch()
        self.fullscreen_check = ToggleSwitch()
        system.content.addWidget(
            toggle_setting(
                "Abrir Preferencias al iniciar",
                "Muestra esta ventana al abrir la aplicación; al cerrarla, la app continúa en la bandeja.",
                self.open_settings_check,
            )
        )
        system.content.addWidget(
            toggle_setting(
                "Iniciar automáticamente con Windows",
                "Ejecuta la aplicación en segundo plano al iniciar tu sesión.",
                self.startup_check,
            )
        )
        system.content.addWidget(
            toggle_setting(
                "Revelar todos los monitores en fullscreen",
                "Opcional: al detectar un juego o presentación fullscreen, pausa todos los overlays.",
                self.fullscreen_check,
            )
        )
        layout.addWidget(system)
        layout.addStretch()
        return page

    def _applications_page(self) -> QWidget:
        page, layout = self._page("Aplicaciones excluidas", "Cuando una de estas aplicaciones tenga el foco, todos los monitores se revelarán.")
        card = Card("Lista de exclusión", "Escribí un ejecutable por línea, por ejemplo: photoshop.exe")
        self.excluded_apps_edit = QPlainTextEdit()
        self.excluded_apps_edit.setPlaceholderText("powerpnt.exe\nobs64.exe\nphotoshop.exe")
        self.excluded_apps_edit.setMinimumHeight(280)
        card.content.addWidget(self.excluded_apps_edit)
        layout.addWidget(card)
        hint = Card("Consejo", "Usá esta lista para software de presentación, captura o color crítico. No hace falta incluir juegos si la pausa fullscreen está activa.")
        layout.addWidget(hint)
        layout.addStretch()
        return page

    def _about_page(self) -> QWidget:
        page, layout = self._page("Acerca de", "Una utilidad discreta para recuperar atención en espacios multimonitor.")
        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Monitor Dim Overlay 2.1.2")
        title.setObjectName("Title")
        description = QLabel(
            "Smart Focus detecta dónde estás trabajando, atenúa el resto del escritorio y se aparta cuando lo necesitás."
        )
        description.setWordWrap(True)
        description.setObjectName("Muted")
        hero_layout.addWidget(title)
        hero_layout.addWidget(description)
        layout.addWidget(hero)
        details = Card("Atajos rápidos")
        details.content.addWidget(QLabel("F9  ·  Activar o desactivar overlays"))
        details.content.addWidget(QLabel("Ctrl + Shift + F9  ·  Revelar temporalmente"))
        details.content.addWidget(QLabel("Doble clic en el tray  ·  Alternar estado"))
        layout.addWidget(details)
        layout.addStretch()
        return page

    def show_settings(self, settings: Settings, screens: list[ScreenDescriptor]) -> None:
        self._settings = Settings.from_dict(settings.to_dict())
        self._screens = screens
        self._populate()
        self.show()
        self.raise_()
        self.activateWindow()

    def _populate(self) -> None:
        s = self._settings
        self.enabled_check.setChecked(s.enabled)
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(s.mode.value)))
        self.opacity_slider.setValue(round(s.opacity * 100))
        self.delay_spin.setValue(s.restore_delay_ms)
        self.fade_spin.setValue(s.fade_duration_ms)
        self.toggle_hotkey_edit.setText(s.toggle_hotkey)
        self.peek_hotkey_edit.setText(s.peek_hotkey)
        self.peek_duration_spin.setValue(s.peek_duration_ms)
        self.open_settings_check.setChecked(s.show_settings_on_startup)
        self.startup_check.setChecked(s.launch_at_startup)
        self.fullscreen_check.setChecked(s.pause_fullscreen)
        self.capture_check.setChecked(s.exclude_from_capture)
        self.dim_primary_check.setChecked(s.dim_primary)
        self.excluded_apps_edit.setPlainText("\n".join(s.excluded_apps))
        self._set_color_button(s.dim_color)
        self.profile_combo.clear()
        self.profile_combo.setPlaceholderText("Personalizado")
        self.profile_combo.addItems(sorted(s.profiles))
        if s.active_profile in s.profiles:
            self.profile_combo.setCurrentText(s.active_profile)
        else:
            self.profile_combo.setCurrentIndex(-1)
        self._populate_monitors()
        self._update_mode_help()

    def _populate_monitors(self) -> None:
        while self.monitors_layout.count():
            item = self.monitors_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._monitor_rows.clear()
        for screen in self._screens:
            pref = self._settings.monitor_preference(screen.name)
            row = MonitorRow(screen, pref, self._settings.opacity, self.dim_primary_check.isChecked())
            row.previewRequested.connect(self.previewRequested)
            self.monitors_layout.addWidget(row)
            self._monitor_rows[screen.name] = row
        if not self._screens:
            empty = QLabel("No se detectaron monitores.")
            empty.setObjectName("Muted")
            self.monitors_layout.addWidget(empty)

    def _collect(self) -> Settings:
        result = Settings.from_dict(self._settings.to_dict())
        result.enabled = self.enabled_check.isChecked()
        result.mode = AppMode(self.mode_combo.currentData())
        result.opacity = self.opacity_slider.value() / 100
        result.restore_delay_ms = self.delay_spin.value()
        result.fade_duration_ms = self.fade_spin.value()
        result.toggle_hotkey = self.toggle_hotkey_edit.text().strip() or "F9"
        result.peek_hotkey = self.peek_hotkey_edit.text().strip() or "Ctrl+Shift+F9"
        result.peek_duration_ms = self.peek_duration_spin.value()
        result.show_settings_on_startup = self.open_settings_check.isChecked()
        result.launch_at_startup = self.startup_check.isChecked()
        result.pause_fullscreen = self.fullscreen_check.isChecked()
        result.exclude_from_capture = self.capture_check.isChecked()
        result.dim_primary = self.dim_primary_check.isChecked()
        result.dim_color = self.color_button.property("color") or "#020711"
        result.excluded_apps = sorted(
            {line.strip().lower() for line in self.excluded_apps_edit.toPlainText().splitlines() if line.strip()}
        )
        result.active_profile = "Personalizado"
        for name, row in self._monitor_rows.items():
            result.monitors[name] = row.preference()
        return result

    def _apply(self) -> None:
        settings = self._collect()
        if settings.toggle_hotkey.lower() == settings.peek_hotkey.lower():
            QMessageBox.warning(self, "Atajos duplicados", "Los dos atajos globales deben ser diferentes.")
            return
        self._settings = settings
        self.settingsApplied.emit(settings)
        self.save_status.setText("Cambios aplicados")
        self.apply_button.setText("Aplicado")
        QTimer.singleShot(1800, self._clear_save_status)

    def _load_profile(self) -> None:
        name = self.profile_combo.currentText()
        if name not in self._settings.profiles:
            return
        self._settings.apply_profile(name)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(self._settings.mode.value))
        self.opacity_slider.setValue(round(self._settings.opacity * 100))
        self.delay_spin.setValue(self._settings.restore_delay_ms)
        self.fade_spin.setValue(self._settings.fade_duration_ms)
        self.fullscreen_check.setChecked(self._settings.pause_fullscreen)

    def _save_profile(self) -> None:
        name, accepted = QInputDialog.getText(self, "Guardar perfil", "Nombre del nuevo perfil:")
        name = name.strip()
        if not accepted or not name:
            return
        current = self._collect()
        current.profiles[name] = FocusProfile(
            current.mode,
            current.opacity,
            current.restore_delay_ms,
            current.fade_duration_ms,
            current.pause_fullscreen,
        )
        current.active_profile = name
        self._settings = current
        self.profile_combo.clear()
        self.profile_combo.addItems(sorted(current.profiles))
        self.profile_combo.setCurrentText(name)

    def _choose_color(self) -> None:
        initial = QColor(self.color_button.property("color") or "#020711")
        color = QColorDialog.getColor(initial, self, "Color del overlay")
        if color.isValid():
            self._set_color_button(color.name())

    def _set_color_button(self, color: str) -> None:
        self.color_button.setProperty("color", color)
        self.color_button.setText(f"  {color.upper()}")
        text_color = "#03101F" if QColor(color).lightness() > 160 else "#F5F8FC"
        self.color_button.setStyleSheet(
            f"text-align: left; background: {color}; color: {text_color}; border: 1px solid #28405E;"
        )

    def _sync_global_opacity(self, value: int) -> None:
        for row in self._monitor_rows.values():
            row.set_global_opacity(value / 100)

    def _refresh_monitor_availability(self) -> None:
        for row in self._monitor_rows.values():
            row.set_primary_allowed(self.dim_primary_check.isChecked())

    def _update_mode_help(self) -> None:
        mode_value = self.mode_combo.currentData()
        descriptions = {
            AppMode.CURSOR.value: "Revela inmediatamente el monitor donde entra el puntero y vuelve a oscurecerlo después de la espera.",
            AppMode.ACTIVE_WINDOW.value: "Mantiene visible el monitor de la ventana en primer plano. El cambio de foco decide qué pantalla se revela.",
            AppMode.MANUAL.value: "Mantiene oscurecidos los monitores activados hasta que pauses el sistema o uses la vista temporal.",
        }
        self.mode_help.setText(descriptions.get(mode_value, ""))

    def _clear_save_status(self) -> None:
        self.save_status.clear()
        self.apply_button.setText("Aplicar cambios")

    def _restore_defaults(self) -> None:
        answer = QMessageBox.question(self, "Restaurar valores", "¿Restaurar la configuración predeterminada?")
        if answer == QMessageBox.StandardButton.Yes:
            profiles = self._settings.profiles
            self._settings = Settings(profiles=profiles)
            self._populate()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.visibilityChanged.emit(True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.visibilityChanged.emit(False)
