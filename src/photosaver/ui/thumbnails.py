"""Thumbnails made in background threads, a few at a time, only when they are shown."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage, QPixmap

from ..core import thumbs

THREADS = 4
MEMORY = 600  # thumbnails kept in memory


class _Emitter(QObject):
    ready = Signal(str, QImage)  # hash, thumbnail (null when it can't be made)


class _Job(QRunnable):
    def __init__(self, key: str, make: Callable[[], bytes | None], emitter: _Emitter):
        super().__init__()
        self.key, self.make, self.emitter = key, make, emitter

    def run(self) -> None:
        image = QImage()
        try:
            data = self.make()
        except Exception:  # a broken photo must not stop the others
            data = None
        if data:
            image.loadFromData(data)
        self.emitter.ready.emit(self.key, image)


class ThumbnailLoader(QObject):
    """Ask with :meth:`request`; ``ready(hash)`` says when :meth:`get` has it."""

    ready = Signal(str)

    def __init__(self, sources: Callable[[str, str], list[Path]], parent: QObject | None = None):
        """``sources(hash, path)`` lists where the photo can be read (one per disk)."""
        super().__init__(parent)
        self._sources = sources
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(THREADS)
        self._emitter = _Emitter(self)
        self._emitter.ready.connect(self._done)
        self._cache: OrderedDict[str, QPixmap | None] = OrderedDict()
        self._pending: set[str] = set()

    def get(self, key: str) -> QPixmap | None:
        pixmap = self._cache.get(key)
        if pixmap is not None:
            self._cache.move_to_end(key)
        return pixmap

    def failed(self, key: str) -> bool:
        return key in self._cache and self._cache[key] is None

    def request(self, key: str, path: str) -> None:
        if key in self._cache or key in self._pending:
            return
        self._pending.add(key)
        sources = self._sources(key, path)
        self._pool.start(_Job(key, lambda: self.make(key, sources), self._emitter))

    def make(self, key: str, sources: list[Path]) -> bytes | None:
        """In a worker thread: the thumbnail of the first readable copy."""
        for source in sources:
            try:
                return thumbs.make_thumbnail(source)
            except thumbs.NoThumbnail:
                continue
        return None

    def _done(self, key: str, image: QImage) -> None:
        self._pending.discard(key)
        self._cache[key] = None if image.isNull() else QPixmap.fromImage(image)
        while len(self._cache) > MEMORY:
            self._cache.popitem(last=False)
        self.ready.emit(key)

    def wait(self, msecs: int = 10000) -> None:
        self._pool.waitForDone(msecs)
