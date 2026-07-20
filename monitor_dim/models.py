from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AppMode(str, Enum):
    CURSOR = "cursor"
    ACTIVE_WINDOW = "active_window"
    MANUAL = "manual"

    @property
    def label(self) -> str:
        return {
            self.CURSOR: "Seguir el cursor",
            self.ACTIVE_WINDOW: "Ventana activa (Smart Focus)",
            self.MANUAL: "Oscurecimiento fijo",
        }[self]


@dataclass
class MonitorPreference:
    enabled: bool = True
    opacity: float | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "MonitorPreference":
        if not isinstance(value, dict):
            return cls()
        opacity = value.get("opacity")
        try:
            opacity = None if opacity is None else _clamp(float(opacity), 0.10, 0.98)
        except (TypeError, ValueError):
            opacity = None
        return cls(enabled=bool(value.get("enabled", True)), opacity=opacity)


@dataclass
class FocusProfile:
    mode: AppMode = AppMode.CURSOR
    opacity: float = 0.85
    restore_delay_ms: int = 1000
    fade_duration_ms: int = 180
    pause_fullscreen: bool = False

    @classmethod
    def from_dict(cls, value: Any) -> "FocusProfile":
        if not isinstance(value, dict):
            return cls()
        return cls(
            mode=_mode(value.get("mode")),
            opacity=_clamp(_float(value.get("opacity"), 0.85), 0.10, 0.98),
            restore_delay_ms=_clamp_int(value.get("restore_delay_ms"), 1000, 0, 10_000),
            fade_duration_ms=_clamp_int(value.get("fade_duration_ms"), 180, 0, 2_000),
            pause_fullscreen=bool(value.get("pause_fullscreen", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        return data


def default_profiles() -> dict[str, FocusProfile]:
    return {
        "Trabajo": FocusProfile(AppMode.ACTIVE_WINDOW, 0.86, 900, 180, False),
        "Gaming": FocusProfile(AppMode.MANUAL, 0.92, 0, 120, False),
        "Noche": FocusProfile(AppMode.CURSOR, 0.72, 1400, 260, False),
    }


@dataclass
class Settings:
    schema_version: int = 5
    enabled: bool = True
    mode: AppMode = AppMode.CURSOR
    opacity: float = 0.85
    restore_delay_ms: int = 1000
    poll_interval_ms: int = 90
    fade_duration_ms: int = 180
    toggle_hotkey: str = "F9"
    peek_hotkey: str = "Ctrl+Shift+F9"
    peek_duration_ms: int = 4000
    launch_at_startup: bool = False
    show_settings_on_startup: bool = True
    pause_fullscreen: bool = False
    exclude_from_capture: bool = False
    dim_primary: bool = True
    dim_color: str = "#020711"
    active_profile: str = "Personalizado"
    excluded_apps: list[str] = field(default_factory=list)
    monitors: dict[str, MonitorPreference] = field(default_factory=dict)
    profiles: dict[str, FocusProfile] = field(default_factory=default_profiles)

    @classmethod
    def from_dict(cls, value: Any) -> "Settings":
        if not isinstance(value, dict):
            return cls()
        previous_schema = _clamp_int(value.get("schema_version"), 1, 1, 99)
        monitors_raw = value.get("monitors", {})
        profiles_raw = value.get("profiles", {})
        profiles = default_profiles()
        if isinstance(profiles_raw, dict):
            profiles.update({str(k): FocusProfile.from_dict(v) for k, v in profiles_raw.items()})
        if previous_schema < 3:
            for profile in profiles.values():
                profile.pause_fullscreen = False
        excluded = value.get("excluded_apps", [])
        if not isinstance(excluded, list):
            excluded = []
        color = str(value.get("dim_color", "#020711"))
        if not _valid_color(color):
            color = "#020711"
        return cls(
            schema_version=5,
            enabled=bool(value.get("enabled", True)),
            mode=_mode(value.get("mode")),
            opacity=_clamp(_float(value.get("opacity"), 0.85), 0.10, 0.98),
            restore_delay_ms=_clamp_int(value.get("restore_delay_ms"), 1000, 0, 10_000),
            poll_interval_ms=_clamp_int(value.get("poll_interval_ms"), 90, 30, 1000),
            fade_duration_ms=_clamp_int(value.get("fade_duration_ms"), 180, 0, 2000),
            toggle_hotkey=str(value.get("toggle_hotkey", "F9")),
            peek_hotkey=str(value.get("peek_hotkey", "Ctrl+Shift+F9")),
            peek_duration_ms=_clamp_int(value.get("peek_duration_ms"), 4000, 500, 30_000),
            launch_at_startup=bool(value.get("launch_at_startup", False)),
            show_settings_on_startup=(
                bool(value.get("show_settings_on_startup", True)) if previous_schema >= 5 else True
            ),
            pause_fullscreen=bool(value.get("pause_fullscreen", False)) if previous_schema >= 3 else False,
            exclude_from_capture=bool(value.get("exclude_from_capture", False)),
            dim_primary=bool(value.get("dim_primary", True)) if previous_schema >= 4 else True,
            dim_color=color,
            active_profile=str(value.get("active_profile", "Personalizado")),
            excluded_apps=sorted({str(x).strip().lower() for x in excluded if str(x).strip()}),
            monitors={str(k): MonitorPreference.from_dict(v) for k, v in monitors_raw.items()}
            if isinstance(monitors_raw, dict)
            else {},
            profiles=profiles,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "mode": self.mode.value,
            "opacity": self.opacity,
            "restore_delay_ms": self.restore_delay_ms,
            "poll_interval_ms": self.poll_interval_ms,
            "fade_duration_ms": self.fade_duration_ms,
            "toggle_hotkey": self.toggle_hotkey,
            "peek_hotkey": self.peek_hotkey,
            "peek_duration_ms": self.peek_duration_ms,
            "launch_at_startup": self.launch_at_startup,
            "show_settings_on_startup": self.show_settings_on_startup,
            "pause_fullscreen": self.pause_fullscreen,
            "exclude_from_capture": self.exclude_from_capture,
            "dim_primary": self.dim_primary,
            "dim_color": self.dim_color,
            "active_profile": self.active_profile,
            "excluded_apps": list(self.excluded_apps),
            "monitors": {key: asdict(pref) for key, pref in self.monitors.items()},
            "profiles": {key: profile.to_dict() for key, profile in self.profiles.items()},
        }

    def apply_profile(self, name: str) -> None:
        profile = self.profiles[name]
        self.mode = profile.mode
        self.opacity = profile.opacity
        self.restore_delay_ms = profile.restore_delay_ms
        self.fade_duration_ms = profile.fade_duration_ms
        self.pause_fullscreen = profile.pause_fullscreen
        self.active_profile = name

    def monitor_preference(self, name: str) -> MonitorPreference:
        return self.monitors.get(name, MonitorPreference())


def _mode(value: Any) -> AppMode:
    try:
        return AppMode(str(value))
    except ValueError:
        return AppMode.CURSOR


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _valid_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    try:
        int(value[1:], 16)
    except ValueError:
        return False
    return True
