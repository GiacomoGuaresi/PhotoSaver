"""PhotoSaver's look: one dark theme for every platform, made to be easy to read.

Design tokens (colours, radii) as in PrintPicker, with bigger text, higher contrast and
large click areas: the app must work for people who barely use a computer.
:func:`apply_theme` installs Fusion style + palette + one global style sheet. Widgets opt
into variants with :func:`set_role` (``primary``, ``title``…).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

RESOURCES = Path(__file__).resolve().parent.parent / "resources"
FONTS_DIR = RESOURCES / "fonts"
ICONS_DIR = RESOURCES / "icons"
FONT_FAMILY = "Inter"
BASE_POINT_SIZE = 12.5  # bigger than the usual 9-10 pt

# Surfaces, from the window background up: neutral greys, not black
BG = QColor("#2B2B2D")
SURFACE = QColor("#333336")
SURFACE_2 = QColor("#3C3C3F")
SURFACE_3 = QColor("#47474A")
BORDER = QColor("#4A4A4E")
BORDER_STRONG = QColor("#626267")

# Text: high contrast
TEXT = QColor("#F2F2F5")
TEXT_MUTED = QColor("#B4B4BA")
TEXT_FAINT = QColor("#85858B")

# Accents
ACCENT = QColor("#3B82F6")  # actions and focus
ACCENT_HOVER = QColor("#5B97F8")
ACCENT_PRESSED = QColor("#2563EB")
ON_ACCENT = QColor("#FFFFFF")
SAFE = QColor("#34C77B")  # "your photos are safe"
WARNING = QColor("#FFB020")  # something to look at, photos not at risk
DANGER = QColor("#F0616D")  # deleting, real problems

RADIUS = 10
RADIUS_LARGE = 16


def css(color: QColor) -> str:
    if color.alpha() == 255:
        return color.name()
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def set_role(widget: QWidget, role: str) -> QWidget:
    """Give ``widget`` a style variant of the global style sheet."""
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


ICON_SIZES = (16, 20, 24, 32, 48, 64, 96, 128)


def svg_pixmap(svg: bytes, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg)).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


@cache
def _icon(name: str, color: str) -> QIcon:
    source = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
    result = QIcon()
    for mode, fill in ((QIcon.Mode.Normal, color), (QIcon.Mode.Disabled, TEXT_FAINT.name())):
        svg = source.replace("currentColor", fill).encode()
        for size in ICON_SIZES:
            result.addPixmap(svg_pixmap(svg, size), mode)
    return result


def icon(name: str, color: QColor = TEXT) -> QIcon:
    """A Lucide line icon (``resources/icons/<name>.svg``) drawn in ``color``."""
    return _icon(name, color.name())


def icon_pixmap(name: str, size: int, color: QColor = TEXT) -> QPixmap:
    """An icon as a pixmap, sharp on high-DPI screens."""
    app = QGuiApplication.instance()
    ratio = app.devicePixelRatio() if app is not None else 1.0
    pixmap = icon(name, color).pixmap(round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def palette() -> QPalette:
    p = QPalette()
    roles = QPalette.ColorRole
    for role, color in (
        (roles.Window, BG),
        (roles.WindowText, TEXT),
        (roles.Base, SURFACE),
        (roles.AlternateBase, SURFACE_2),
        (roles.Text, TEXT),
        (roles.PlaceholderText, TEXT_MUTED),
        (roles.Button, SURFACE_2),
        (roles.ButtonText, TEXT),
        (roles.Highlight, ACCENT),
        (roles.HighlightedText, ON_ACCENT),
        (roles.Link, ACCENT_HOVER),
        (roles.ToolTipBase, SURFACE_3),
        (roles.ToolTipText, TEXT),
        (roles.Light, SURFACE_3),
        (roles.Midlight, SURFACE_2),
        (roles.Mid, BORDER),
        (roles.Accent, ACCENT),
    ):
        p.setColor(role, color)
    disabled = QPalette.ColorGroup.Disabled
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        p.setColor(disabled, role, TEXT_FAINT)
    return p


STYLE_SHEET = """
QToolTip {
    background: @SURFACE_3; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: 6px; padding: 6px 10px;
}

QLabel[role="title"] { font-size: 26pt; font-weight: 700; }
QLabel[role="subtitle"] { font-size: 15pt; color: @TEXT_MUTED; }
QLabel[role="heading"] { font-size: 16pt; font-weight: 600; }
QLabel[role="muted"] { color: @TEXT_MUTED; }
QLabel[role="safe"] { color: @SAFE; font-weight: 600; }
QLabel[role="warning"] { color: @WARNING; font-weight: 600; }
QLabel[role="danger"] { color: @DANGER; font-weight: 600; }

QFrame#card { background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx; }
QFrame#banner { background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx; }
QFrame#banner[role="safe"] { border-color: @SAFE; }
QFrame#banner[role="warning"] { border-color: @WARNING; }
QFrame#banner[role="danger"] { border-color: @DANGER; }
QFrame#diskBar { background: @SURFACE; border-top: 1px solid @BORDER; }
QFrame#footer { border-top: 1px solid @BORDER; }

QPushButton {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: @RADIUSpx; padding: 10px 20px; min-height: 24px;
}
QPushButton:hover { background: @SURFACE_3; }
QPushButton:pressed { background: @SURFACE; }
QPushButton:focus { border-color: @ACCENT; }
QPushButton:disabled { color: @TEXT_FAINT; background: @SURFACE; border-color: @SURFACE_2; }
QPushButton[role="primary"] {
    background: @ACCENT; color: @ON_ACCENT; border: 2px solid @ACCENT;
    font-size: 15pt; font-weight: 600; padding: 12px 32px; min-height: 30px;
}
QPushButton[role="primary"]:hover { background: @ACCENT_HOVER; border-color: @ACCENT_HOVER; }
QPushButton[role="primary"]:pressed { background: @ACCENT_PRESSED; }
QPushButton[role="primary"]:focus { border-color: @TEXT; }
QPushButton[role="primary"]:disabled {
    background: @SURFACE_2; color: @TEXT_FAINT; border-color: @SURFACE_2;
}
QPushButton[role="danger"] {
    background: @DANGER; color: #1B0507; border: 2px solid @DANGER; font-weight: 600;
}
QPushButton[role="link"] {
    background: transparent; border: none; color: @ACCENT_HOVER; padding: 6px 4px;
    text-align: left;
}
QPushButton[role="link"]:hover { text-decoration: underline; }
QToolButton[role="tile"] {
    background: @SURFACE; border: 1px solid @BORDER; border-radius: @RADIUS_LARGEpx;
    font-size: 16pt; font-weight: 600; padding: 24px;
}
QToolButton[role="tile"]:hover { background: @SURFACE_2; border-color: @ACCENT; }
QToolButton[role="tile"]:focus { border-color: @ACCENT; }
QToolButton[role="tile"]:disabled { color: @TEXT_FAINT; background: @BG; }

QToolButton {
    background: transparent; color: @TEXT; border: 1px solid transparent;
    border-radius: @RADIUSpx; padding: 8px 12px;
}
QToolButton:hover { background: @SURFACE_2; }
QToolButton::menu-indicator { image: none; }

QLineEdit, QComboBox, QSpinBox {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: @RADIUSpx; padding: 8px 12px; min-height: 22px;
    selection-background-color: @ACCENT; selection-color: @ON_ACCENT;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: @ACCENT; }

QCheckBox, QRadioButton { spacing: 10px; }
QCheckBox::indicator, QRadioButton::indicator { width: 20px; height: 20px; }

QProgressBar {
    background: @SURFACE_2; border: none; border-radius: 7px; min-height: 14px; max-height: 14px;
    color: transparent;
}
QProgressBar::chunk { background: @ACCENT; border-radius: 7px; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: @SURFACE_3; border-radius: 4px; min-height: 32px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QMenu {
    background: @SURFACE_2; color: @TEXT; border: 1px solid @BORDER_STRONG;
    border-radius: @RADIUSpx; padding: 6px;
}
QMenu::item { padding: 10px 28px 10px 14px; border-radius: 6px; }
QMenu::item:selected { background: @SURFACE_3; }
QMenu::separator { height: 1px; background: @BORDER; margin: 4px 8px; }

QListWidget, QTreeWidget, QTableWidget {
    background: @SURFACE; color: @TEXT; border: 1px solid @BORDER; border-radius: @RADIUSpx;
    outline: none;
}
QListWidget::item, QTreeWidget::item { padding: 8px; }
QHeaderView::section {
    background: @SURFACE_2; color: @TEXT_MUTED; border: none; padding: 8px; font-weight: 600;
}

QDialog { background: @BG; }
"""


def style_sheet() -> str:
    tokens = {
        name: css(value) if isinstance(value, QColor) else str(value)
        for name, value in globals().items()
        if name.isupper() and isinstance(value, (QColor, int))
    }
    text = STYLE_SHEET
    # Longest names first, so @SURFACE_2 is not read as @SURFACE + "_2"
    for name in sorted(tokens, key=len, reverse=True):
        text = text.replace(f"@{name}", tokens[name])
    return text


def load_fonts() -> bool:
    """Register the bundled Inter font; False if it is missing (the system font stays)."""
    loaded = False
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        loaded |= QFontDatabase.addApplicationFont(str(path)) != -1
    return loaded


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont(FONT_FAMILY) if load_fonts() else app.font()
    font.setPointSizeF(BASE_POINT_SIZE)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)
    app.setPalette(palette())
    app.setStyleSheet(style_sheet())
    QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
