"""The building block of the interface: one screen = one step.

Every screen says where you are (title), what to do now (subtitle) and what happens next
(the buttons at the bottom: one big primary action, maybe a few smaller ones, and "Back").
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import theme

MARGIN = 48


class Screen(QWidget):
    """A titled screen with a body and a footer of buttons.

    Subclasses fill :attr:`body`; :meth:`set_primary`, :meth:`add_secondary` and
    :meth:`set_back` fill the footer. ``back_requested`` asks the window to go back.
    """

    back_requested = Signal()

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(MARGIN, MARGIN - 8, MARGIN, 24)
        layout.setSpacing(12)
        self.title = theme.set_role(QLabel(title), "title")
        self.title.setWordWrap(True)
        self.subtitle = theme.set_role(QLabel(subtitle), "subtitle")
        self.subtitle.setWordWrap(True)
        self.subtitle.setVisible(bool(subtitle))
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addSpacing(16)
        self.body = QVBoxLayout()
        self.body.setSpacing(16)
        layout.addLayout(self.body, 1)
        outer.addWidget(content, 1)

        self.footer = QFrame(objectName="footer")
        self._footer = QHBoxLayout(self.footer)
        self._footer.setContentsMargins(MARGIN, 16, MARGIN, 16)
        self._footer.setSpacing(12)
        self.back_button = QPushButton(theme.icon("arrow-left"), self.tr("Back"))
        self.back_button.clicked.connect(self.back_requested)
        self.back_button.hide()
        self._footer.addWidget(self.back_button)
        self._footer.addStretch(1)
        self.primary: QPushButton | None = None
        self.footer.hide()
        outer.addWidget(self.footer)

    def set_texts(self, title: str, subtitle: str = "") -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.subtitle.setVisible(bool(subtitle))

    def set_back(self, visible: bool = True) -> None:
        self.back_button.setVisible(visible)
        self._update_footer()

    def set_primary(self, text: str, slot: Callable[[], None] | None = None) -> QPushButton:
        """The one big action of the screen, at the bottom right."""
        if self.primary is None:
            self.primary = theme.set_role(QPushButton(), "primary")
            self.primary.setDefault(True)
            self._footer.addWidget(self.primary)
        self.primary.setText(text)
        if slot is not None:
            self.primary.clicked.connect(slot)
        self._update_footer()
        return self.primary

    def add_secondary(self, text: str, slot: Callable[[], None]) -> QPushButton:
        """A smaller action, before the primary one."""
        button = QPushButton(text)
        button.clicked.connect(slot)
        index = self._footer.indexOf(self.primary) if self.primary else self._footer.count()
        self._footer.insertWidget(index, button)
        self._update_footer()
        return button

    def _update_footer(self) -> None:
        has_buttons = not self.back_button.isHidden() or self._footer.count() > 2
        self.footer.setVisible(has_buttons)

    def shown(self) -> None:
        """Called every time the screen becomes the current one."""


class Banner(QFrame):
    """A reassuring (``safe``) or warning (``warning``, ``danger``) message, changeable."""

    ICONS = {"safe": "shield-check", "warning": "shield-alert", "danger": "shield-alert"}

    def __init__(self, text: str = "", role: str = "safe", parent: QWidget | None = None):
        super().__init__(parent, objectName="banner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        self.picture = QLabel()
        layout.addWidget(self.picture, 0, Qt.AlignmentFlag.AlignTop)
        self.label = theme.set_role(QLabel(), "heading")
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 1)
        self.set(text, role)

    def set(self, text: str, role: str = "safe") -> None:
        color = {"safe": theme.SAFE, "warning": theme.WARNING, "danger": theme.DANGER}[role]
        theme.set_role(self, role)
        self.picture.setPixmap(theme.icon_pixmap(self.ICONS[role], 36, color))
        self.label.setText(text)

    @property
    def role(self) -> str:
        return self.property("role")
