"""Application entry point: ``photosaver`` or ``python -m photosaver``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from .. import __version__
from ..core import detect
from . import theme
from .controller import Controller
from .main_window import MainWindow
from .session import Session

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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="photosaver")
    parser.add_argument(
        "--disks",
        type=Path,
        nargs="+",
        default=None,
        help=f"folders to look for disks in (development; or the {detect.ENV_DISKS} variable)",
    )
    return parser.parse_args(argv)


def build(roots: list[Path]) -> tuple[MainWindow, Controller]:
    window = MainWindow()
    session = Session(lambda: roots, window)
    controller = Controller(window, session, window)
    return window, controller


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    args = parse_args(argv[1:])
    app = create_application(argv[:1])
    install_translations(app)
    roots = args.disks if args.disks is not None else detect.configured_roots()
    window, controller = build(roots)
    window.show()
    controller.start()
    return app.exec()
