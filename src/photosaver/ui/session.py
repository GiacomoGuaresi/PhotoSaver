"""Watching for disks: the app notices by itself when a disk is plugged in or out."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from ..core import detect

POLL_MS = 1500


class Session(QObject):
    """Looks at the candidate folders every :data:`POLL_MS` and emits ``changed`` when
    what is connected changes."""

    changed = Signal()

    def __init__(self, roots: Callable[[], list[Path]], parent: QObject | None = None):
        super().__init__(parent)
        self._roots = roots
        self.found = detect.Found()
        self.assessment = detect.Assessment(detect.WAITING)
        self._key: tuple = ()
        self._timer = QTimer(self, interval=POLL_MS)
        self._timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh(force=True)
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def refresh(self, force: bool = False) -> None:
        found = detect.scan_roots(self._roots())
        key = (
            tuple((str(d.root), d.id) for d in found.disks),
            tuple(map(str, found.empty)),
            tuple(map(str, found.other)),
            tuple(map(str, found.unreadable)),
        )
        if key == self._key and not force:
            return
        self._key = key
        self.found = found
        self.assessment = detect.assess(found)
        self.changed.emit()


def disk_name(label: str) -> str:
    """Disk A, B… are shown as Disk 1, 2…: numbers are easier to stick on a label."""
    if len(label) == 1 and label.isalpha():
        return str(ord(label.upper()) - ord("A") + 1)
    return label
