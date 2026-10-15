"""Long work in a background thread, so the window never freezes.

A job is a function of ``on_progress`` and ``should_stop`` keyword arguments. It must open
its own archive: SQLite connections cannot move between threads.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from ..core import hashing


class Worker(QThread):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, job: Callable[..., object], parent=None) -> None:
        super().__init__(parent)
        self._job = job
        self._stop = False

    def cancel(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            result = self._job(on_progress=self.progress.emit, should_stop=lambda: self._stop)
        except hashing.Cancelled:
            self.cancelled.emit()
        except Exception as error:  # shown to the user, never crash the thread
            self.failed.emit(str(error) or type(error).__name__)
        else:
            self.succeeded.emit(result)
