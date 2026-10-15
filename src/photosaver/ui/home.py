"""The home screen: how the photos are, and a few big buttons."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QToolButton, QWidget

from . import theme
from .screen import Banner, Screen


class HomeScreen(Screen):
    add_requested = Signal()
    browse_requested = Signal()
    check_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(self.tr("Your photos"), parent=parent)
        self.status = Banner()
        self.body.addWidget(self.status)

        grid = QGridLayout()
        grid.setSpacing(20)
        self.add = self._tile("image-plus", self.tr("Add photos"), self.add_requested)
        self.browse = self._tile("images", self.tr("Look at your photos"), self.browse_requested)
        self.check = self._tile("search-check", self.tr("Check the disks"), self.check_requested)
        for column, tile in enumerate((self.add, self.browse, self.check)):
            grid.addWidget(tile, 0, column)
        self.body.addLayout(grid)
        self.body.addStretch(1)
        self.set_status(self.tr("Your photos are safe on both disks."), "safe")

    def _tile(self, icon_name: str, text: str, signal) -> QToolButton:
        tile = theme.set_role(QToolButton(), "tile")
        tile.setIcon(theme.icon(icon_name, theme.ACCENT_HOVER))
        tile.setText(text)
        tile.setIconSize(QSize(64, 64))
        tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tile.setMinimumHeight(190)
        tile.setCursor(Qt.CursorShape.PointingHandCursor)
        tile.clicked.connect(signal)
        return tile

    def set_status(self, text: str, role: str = "safe") -> None:
        self.status.set(text, role)

    def set_read_only(self, read_only: bool) -> None:
        """With one disk only, photos can be looked at but not added or checked."""
        self.add.setEnabled(not read_only)
        self.check.setEnabled(not read_only)
