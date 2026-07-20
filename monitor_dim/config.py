from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .models import Settings

LOGGER = logging.getLogger(__name__)


class ConfigStore:
    def __init__(self, base_dir: Path | None = None, legacy_path: Path | None = None):
        if base_dir is None:
            appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            base_dir = Path(appdata) / "MonitorDimOverlay" if appdata else Path.home() / ".monitor_dim_overlay"
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "settings.json"
        self.legacy_path = legacy_path

    def load(self) -> Settings:
        data = self._read_json(self.path)
        if data is not None:
            return Settings.from_dict(data)
        legacy = self._read_json(self.legacy_path) if self.legacy_path else None
        if legacy is not None:
            settings = Settings.from_dict(legacy)
            self.save(settings)
            return settings
        return Settings()

    def save(self, settings: Settings) -> bool:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temp_path, self.path)
            return True
        except OSError:
            LOGGER.exception("Could not save settings to %s", self.path)
            return False

    @staticmethod
    def _read_json(path: Path | None) -> dict[str, Any] | None:
        if path is None:
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError):
            LOGGER.exception("Could not read settings from %s", path)
            return None
