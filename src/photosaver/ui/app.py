"""Application entry point: ``photosaver`` or ``python -m photosaver``."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from .. import __version__
from . import theme
from .home import HomeScreen
from .main_window import MainWindow

APP_NAME = "PhotoSaver"
I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


def install_translations(app: QApplication, locale: QLocale | None = None) -> list[QTranslator]:
    """Load PhotoSaver's and Qt's translations for ``locale`` (default: the system's).

    English is the source language: without a matching translation texts stay English.
    """
    locale = locale or QLocale.system()
    translators = []
    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name, directory in (("qtbase", qt_dir), ("photosaver", str(I18N_DIR))):
        translator = QTranslator(app)
        if translator.load(locale, name, "_", directory):
            app.installTranslator(translator)
            translators.append(translator)
    return translators


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(theme.icon("shield-check", theme.ACCENT))
    theme.apply_theme(app)
    return app


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = create_application(argv)
    install_translations(app)
    window = MainWindow()
    window.reset(HomeScreen())
    window.show()
    return app.exec()
