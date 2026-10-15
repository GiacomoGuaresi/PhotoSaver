"""Screens around connecting the disks: waiting for them, the first check, the goodbye."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from ..core import detect
from . import theme
from .screen import Banner, Screen
from .session import disk_name

HELP_AFTER_MS = 30_000


class Spinner(QLabel):
    """A slowly turning circle: the app is listening, not frozen."""

    def __init__(self, size: int = 28, parent: QWidget | None = None):
        super().__init__(parent)
        self._base = theme.icon_pixmap("loader-circle", size, theme.TEXT_MUTED)
        self._angle = 0
        self.setFixedSize(size + 8, size + 8)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer = QTimer(self, interval=80)
        self._timer.timeout.connect(self._turn)
        self._timer.start()
        self._turn()

    def _turn(self) -> None:
        self._angle = (self._angle + 30) % 360
        pixmap = self._base.transformed(
            QTransform().rotate(self._angle), Qt.TransformationMode.SmoothTransformation
        )
        pixmap.setDevicePixelRatio(self._base.devicePixelRatio())
        self.setPixmap(pixmap)


class ConnectScreen(Screen):
    """'Connect the two photo disks': updates by itself as disks come and go."""

    one_disk_requested = Signal()
    prepare_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            self.tr("Connect the two photo disks"),
            self.tr(
                "Take the two disks with the PhotoSaver label and plug them into the USB "
                "ports of the computer with their cable."
            ),
            parent,
        )
        picture = QLabel()
        picture.setPixmap(theme.icon_pixmap("usb", 96, theme.ACCENT_HOVER))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(picture)

        self._rows = QGridLayout()
        self._rows.setHorizontalSpacing(16)
        self._rows.setVerticalSpacing(12)
        rows = QHBoxLayout()
        rows.addStretch(1)
        rows.addLayout(self._rows)
        rows.addStretch(1)
        self.body.addLayout(rows)

        self.message = Banner()
        self.message.hide()
        self.body.addWidget(self.message)
        self.help = theme.set_role(
            QLabel(
                self.tr(
                    "I can't see any disk. Check that the cable is plugged in well; "
                    "if the disk has a small light, it must be on."
                )
            ),
            "muted",
        )
        self.help.setWordWrap(True)
        self.help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help.hide()
        self.body.addWidget(self.help)
        self.body.addStretch(1)

        links = QHBoxLayout()
        self.one_disk = theme.set_role(
            QPushButton(self.tr("I only have one disk with me ›")), "link"
        )
        self.one_disk.clicked.connect(self.one_disk_requested)
        self.first_time = theme.set_role(QPushButton(self.tr("Is it the first time? ›")), "link")
        self.first_time.clicked.connect(self.prepare_requested)
        links.addWidget(self.one_disk)
        links.addStretch(1)
        links.addWidget(self.first_time)
        self.body.addLayout(links)

        self._help_timer = QTimer(self, singleShot=True, interval=HELP_AFTER_MS)
        self._help_timer.timeout.connect(self._show_help)
        self._help_timer.start()
        self._nothing_found = True
        self.update_state(detect.Found(), detect.Assessment(detect.WAITING))

    def _show_help(self) -> None:
        self.help.setVisible(self._nothing_found)

    def update_state(self, found: detect.Found, assessment: detect.Assessment) -> None:
        while self._rows.count():
            old = self._rows.takeAt(0).widget()
            old.hide()
            old.deleteLater()
        labels = assessment.all_labels or ["A", "B"]
        connected = {d.label for d in assessment.disks}
        for row, label in enumerate(labels):
            here = label in connected and assessment.situation != detect.MIXED
            picture = QLabel() if here else Spinner(22)
            if here:
                picture.setPixmap(theme.icon_pixmap("circle-check", 26, theme.SAFE))
            name = theme.set_role(
                QLabel(self.tr("Disk %1").replace("%1", disk_name(label))), "heading"
            )
            state = QLabel(self.tr("found") if here else self.tr("waiting…"))
            theme.set_role(state, "safe" if here else "muted")
            self._rows.addWidget(picture, row, 0)
            self._rows.addWidget(name, row, 1)
            self._rows.addWidget(state, row, 2)

        self._nothing_found = not (found.disks or found.empty or found.other)
        if not self._nothing_found:
            self.help.hide()
        self.one_disk.setEnabled(assessment.situation == detect.PARTIAL)

        if assessment.situation == detect.MIXED:
            self.message.set(
                self.tr(
                    "These two disks are not of the same photo collection. Unplug one of them."
                ),
                "danger",
            )
        elif found.empty and assessment.situation == detect.WAITING:
            self.message.set(
                self.tr("This disk is new. Do you want to prepare it for your photos?"),
                "warning",
                self.tr("Prepare"),
                self.prepare_requested.emit,
            )
        elif found.unreadable and not found.disks:
            self.message.set(
                self.tr("I can't read this disk. Unplug it and plug it in again."), "danger"
            )
        elif found.other and not found.disks:
            self.message.set(
                self.tr("This is not a photo disk. Connect the disks with the PhotoSaver label."),
                "warning",
            )
        else:
            self.message.hide()
            return
        self.message.show()


class BusyScreen(Screen):
    """Something is going on: what, and a progress bar."""

    cancel_requested = Signal()

    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(title, subtitle, parent)
        row = QHBoxLayout()
        row.addWidget(Spinner(32))
        self.detail = theme.set_role(QLabel(), "muted")
        row.addWidget(self.detail, 1)
        self.body.addLayout(row)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.body.addWidget(self.bar)
        self.body.addStretch(1)

    def set_progress(self, done: int, total: int, detail: str = "") -> None:
        if total > 0:
            self.bar.setRange(0, 1000)
            self.bar.setValue(round(1000 * done / total))
        if detail:
            self.detail.setText(detail)


class DoneScreen(Screen):
    """Goodbye: the disks can be unplugged."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            self.tr("You can unplug the disks now"),
            self.tr("Put them away in a safe place. See you next time!"),
            parent,
        )
        picture = QLabel()
        picture.setPixmap(theme.icon_pixmap("circle-check", 96, theme.SAFE))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(picture)
        self.body.addStretch(1)
        self.set_primary(self.tr("Close PhotoSaver"), lambda: self.window().close())
