"""'Prepare the disks': the first time, two new disks become the home of the photos.

Steps: introduction → for Disk 1 then Disk 2: choose the new disk, confirm it may be
erased, prepare it, stick a label on it → done. Only empty disks can be chosen for now:
formatting real disks comes later (roadmap M5).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ..core import archive, detect
from ..core.disk import Disk
from . import theme
from .connect import Spinner
from .main_window import MainWindow
from .screen import Banner, Screen
from .session import Session, disk_name

LABELS = ("A", "B")


class IntroScreen(Screen):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            self.tr("Let's prepare the disks"),
            self.tr(
                "You need two new disks: your photos will be kept on both, so if one breaks "
                "they are still safe on the other."
            ),
            parent,
        )
        picture = QLabel()
        picture.setPixmap(theme.icon_pixmap("hard-drive", 96, theme.ACCENT_HOVER))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(picture)
        self.body.addWidget(
            Banner(self.tr("Everything on the two disks will be erased."), "warning")
        )
        self.body.addStretch(1)
        self.set_primary(self.tr("Start"))


class ChooseDiskScreen(Screen):
    """Pick the new disk that becomes Disk N. Updates as disks are plugged in."""

    def __init__(self, label: str, parent: QWidget | None = None):
        name = disk_name(label)
        super().__init__(
            self.tr("Connect the new disk for Disk %1").replace("%1", name),
            self.tr("Plug it in, then choose it here."),
            parent,
        )
        self._group = QButtonGroup(self)
        self._choices: dict[QRadioButton, Path] = {}
        self._list = QWidget()
        self._layout = QVBoxLayout(self._list)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self.body.addWidget(self._list)
        self.waiting = QWidget()
        row = QHBoxLayout(self.waiting)
        row.addWidget(Spinner(24))
        row.addWidget(theme.set_role(QLabel(self.tr("Waiting for a new disk…")), "muted"), 1)
        self.body.addWidget(self.waiting)
        self.note = theme.set_role(QLabel(), "muted")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)
        self.body.addStretch(1)
        self.set_primary(self.tr("Next")).setEnabled(False)
        self._group.buttonToggled.connect(
            lambda *_: self.primary.setEnabled(self.chosen is not None)
        )

    @property
    def chosen(self) -> Path | None:
        button = self._group.checkedButton()
        return self._choices.get(button)

    def update_disks(self, found: detect.Found, exclude: list[Path]) -> None:
        previous = self.chosen
        for button in list(self._choices):
            self._group.removeButton(button)
            button.hide()
            button.deleteLater()
        self._choices.clear()
        candidates = [root for root in found.empty if root not in exclude]
        for root in candidates:
            free = detect.free_space(root)
            size = (
                QLocale().formattedDataSize(free, 1, QLocale.DataSizeFormat.DataSizeSIFormat)
                if free is not None
                else ""
            )
            button = QRadioButton(f"{root.name}   ·   {size}" if size else root.name)
            button.setIcon(theme.icon("hard-drive", theme.TEXT))
            button.setIconSize(QSize(32, 32))
            theme.set_role(button, "choice")
            self._group.addButton(button)
            self._layout.addWidget(button)
            self._choices[button] = root
            if root == previous or len(candidates) == 1:
                button.setChecked(True)
        self.waiting.setVisible(not candidates)
        self.note.setText(
            self.tr("A disk that already contains files can't be used yet: it must be empty.")
            if found.other
            else ""
        )
        self.primary.setEnabled(self.chosen is not None)


class ConfirmScreen(Screen):
    def __init__(self, label: str, root: Path, parent: QWidget | None = None):
        name = disk_name(label)
        super().__init__(
            self.tr("Prepare “%1” as Disk %2?").replace("%1", root.name).replace("%2", name),
            parent=parent,
        )
        self.body.addWidget(
            Banner(
                self.tr("Everything on this disk will be erased. This can't be undone."),
                "danger",
            )
        )
        self.agree = QCheckBox(self.tr("Yes, this disk can be erased"))
        self.body.addWidget(self.agree)
        self.body.addStretch(1)
        button = theme.set_role(
            self.set_primary(self.tr("Prepare Disk %1").replace("%1", name)), "danger"
        )
        button.setEnabled(False)
        self.agree.toggled.connect(button.setEnabled)


class PreparedScreen(Screen):
    def __init__(self, label: str, last: bool, parent: QWidget | None = None):
        name = disk_name(label)
        super().__init__(
            self.tr("Disk %1 is ready").replace("%1", name),
            self.tr(
                "Write “Disk %1” on a sticker and put it on the disk, "
                "so you'll always know which one it is."
            ).replace("%1", name),
            parent,
        )
        picture = QLabel()
        picture.setPixmap(theme.icon_pixmap("circle-check", 96, theme.SAFE))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(picture)
        if last:
            self.body.addWidget(
                Banner(self.tr("The disks are ready! Now you can add your photos."), "safe")
            )
        self.body.addStretch(1)
        self.set_primary(
            self.tr("Done")
            if last
            else self.tr("Next: Disk %1").replace("%1", disk_name(LABELS[1]))
        )


class PrepareFlow(QObject):
    """Drives the steps; ``finished(True)`` when both disks are ready."""

    finished = Signal(bool)

    def __init__(self, window: MainWindow, session: Session, parent: QObject | None = None):
        super().__init__(parent)
        self.window = window
        self.session = session
        self.disks: list[Disk] = []
        self._choose: ChooseDiskScreen | None = None
        session.changed.connect(self._on_disks_changed)

    def start(self) -> None:
        intro = self.window.open(IntroScreen())
        intro.primary.clicked.connect(lambda: self._choose_disk(LABELS[0]))
        intro.back_requested.connect(lambda: self._end(False))

    def _end(self, done: bool) -> None:
        self.session.changed.disconnect(self._on_disks_changed)
        self.finished.emit(done)

    def _used(self) -> list[Path]:
        return [disk.root for disk in self.disks]

    def _choose_disk(self, label: str) -> None:
        self._choose = ChooseDiskScreen(label)
        self.window.open(self._choose)
        if label != LABELS[0]:
            self._choose.set_back(False)
        self._choose.update_disks(self.session.found, self._used())
        self._choose.primary.clicked.connect(lambda: self._confirm(label, self._choose.chosen))

    def _on_disks_changed(self) -> None:
        if self._choose is not None and self.window.current is self._choose:
            self._choose.update_disks(self.session.found, self._used())

    def _confirm(self, label: str, root: Path | None) -> None:
        if root is None:
            return
        screen = self.window.open(ConfirmScreen(label, root))
        screen.primary.clicked.connect(lambda: self._prepare(label, root))

    def _prepare(self, label: str, root: Path) -> None:
        archive_dir = self.tr("Photos")
        if not self.disks:
            disk = archive.create_archive(root, label=label, archive_dir=archive_dir)
        else:
            disk = archive.join_archive(self.disks[0], root, label=label)
        self.disks.append(disk)
        last = len(self.disks) == len(LABELS)
        screen = self.window.reset(PreparedScreen(label, last))
        self._choose = None
        if last:
            screen.primary.clicked.connect(lambda: self._end(True))
        else:
            screen.primary.clicked.connect(lambda: self._choose_disk(LABELS[len(self.disks)]))
        self.session.refresh(force=True)
