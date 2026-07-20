from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .config import ConfigStore
from .controller import OverlayController
from .theme import app_icon


def _configure_logging() -> None:
    store = ConfigStore()
    try:
        store.base_dir.mkdir(parents=True, exist_ok=True)
        log_path = store.base_dir / "monitor-dim-overlay.log"
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except OSError:
        logging.basicConfig(level=logging.INFO)


def main() -> int:
    _configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Monitor Dim Overlay")
    app.setApplicationDisplayName("Monitor Dim Overlay")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MonitorDimOverlay")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    project_root = Path(__file__).resolve().parent.parent
    try:
        controller = OverlayController(app, project_root)
    except Exception as exc:  # Last-resort startup feedback before the tray exists.
        logging.exception("Application startup failed")
        QMessageBox.critical(None, "Monitor Dim Overlay", f"No se pudo iniciar la aplicación:\n\n{exc}")
        return 1
    exit_code = app.exec()
    controller.cleanup()
    return exit_code
