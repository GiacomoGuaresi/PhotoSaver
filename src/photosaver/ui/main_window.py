"""The main window: one screen at a time, and a bar at the bottom that is always there.

Screens are stacked: opening a step pushes it, "Back" pops it, "home" goes back to the
start. The bottom bar shows the disks and holds "More" (history, trash) and "I'm done".
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .screen import Screen


class DiskBar(QFrame):
    """Bottom bar: state of each disk, "More" menu, "I'm done"."""

    done_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, objectName="diskBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 16, 10)
        layout.setSpacing(24)
        self._disks = QHBoxLayout()
        self._disks.setSpacing(24)
        layout.addLayout(self._disks)
        layout.addStretch(1)
        self.more = QToolButton(text=self.tr("More"))
        self.more.setIcon(theme.icon("ellipsis-vertical"))
        self.more.setToolButtonStyle(self.more.toolButtonStyle().ToolButtonTextBesideIcon)
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu = QMenu(self.more)
        self.more.setMenu(self.menu)
        layout.addWidget(self.more)
        self.done = QPushButton(theme.icon("log-out"), self.tr("I'm done"))
        self.done.setToolTip(self.tr("Finish and unplug the disks safely"))
        self.done.clicked.connect(self.done_requested)
        layout.addWidget(self.done)

    def set_disks(self, disks: list[tuple[str, bool, str]]) -> None:
        """``(name, connected, detail)`` for each disk of the archive."""
        while self._disks.count():
            item = self._disks.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for name, connected, detail in disks:
            chip = QWidget()
            row = QHBoxLayout(chip)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            picture = QLabel()
            color = theme.SAFE if connected else theme.TEXT_FAINT
            picture.setPixmap(theme.icon_pixmap("hard-drive", 22, color))
            row.addWidget(picture)
            text = QLabel(f"<b>{name}</b>  {detail}")
            theme.set_role(text, "" if connected else "muted")
            row.addWidget(text)
            self._disks.addWidget(chip)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("PhotoSaver")
        self.setMinimumSize(QSize(900, 640))
        self.resize(1100, 760)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.disk_bar = DiskBar()
        layout.addWidget(self.disk_bar)
        self.setCentralWidget(central)

    # Navigation

    @property
    def current(self) -> Screen | None:
        return self.stack.currentWidget()

    def open(self, screen: Screen) -> Screen:
        """Show ``screen`` on top of the current one ("Back" returns to it)."""
        screen.back_requested.connect(self.back)
        self.stack.addWidget(screen)
        screen.set_back(self.stack.count() > 1)
        self.stack.setCurrentWidget(screen)
        screen.shown()
        return screen

    def replace(self, screen: Screen) -> Screen:
        """Show ``screen`` instead of the current one."""
        old = self.current
        if old is not None:
            self.stack.removeWidget(old)
            old.deleteLater()
        return self.open(screen)

    def reset(self, screen: Screen) -> Screen:
        """Show ``screen`` as the only one: the start of a new path."""
        while self.stack.count():
            old = self.stack.widget(0)
            self.stack.removeWidget(old)
            old.deleteLater()
        return self.open(screen)

    def back(self) -> None:
        if self.stack.count() <= 1:
            return
        old = self.current
        self.stack.removeWidget(old)
        old.deleteLater()
        self.current.shown()
