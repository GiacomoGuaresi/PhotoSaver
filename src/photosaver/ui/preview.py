"""A photo or a video, big: arrows (or ← →) to go through the folder, Esc to go back."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import scanner, thumbs
from ..core.index import FileRecord
from . import theme
from .screen import Screen

KEEP = 5  # photos kept in memory: the current one and its neighbours


class _Emitter(QObject):
    ready = Signal(str, QImage)


class _Load(QRunnable):
    def __init__(self, key: str, sources: list[Path], emitter: _Emitter):
        super().__init__()
        self.key, self.sources, self.emitter = key, sources, emitter

    def run(self) -> None:
        image = QImage()
        for source in self.sources:
            try:
                picture = thumbs.load_preview(source)
            except thumbs.NoThumbnail:
                continue
            data = picture.tobytes()
            image = QImage(data, picture.width, picture.height, 3 * picture.width,
                           QImage.Format.Format_RGB888).copy()  # fmt: skip
            break
        self.emitter.ready.emit(self.key, image)


class PhotoView(QLabel):
    """A picture always fitted to the space it has."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(QSize(200, 200))
        self._pixmap: QPixmap | None = None

    def set_picture(self, pixmap: QPixmap | None, message: str = "") -> None:
        self._pixmap = pixmap
        if pixmap is None:
            self.setPixmap(QPixmap())
            self.setText(message)
        else:
            self.setText("")
            self._fit()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt)
        super().resizeEvent(event)
        self._fit()

    def _fit(self) -> None:
        if self._pixmap is not None:
            ratio = self.devicePixelRatioF()
            scaled = self._pixmap.scaled(
                self.size() * ratio,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(ratio)
            self.setPixmap(scaled)


class VideoView(QWidget):
    """A video player with play/pause and a position bar. Created only for videos."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.video = QVideoWidget()
        self.message = theme.set_role(QLabel(), "heading")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.video)
        self.stack.addWidget(self.message)
        layout.addWidget(self.stack, 1)
        controls = QHBoxLayout()
        self.play = QPushButton(theme.icon("pause"), "")
        self.play.setIconSize(QSize(28, 28))
        self.play.clicked.connect(self.toggle)
        self.position = QSlider(Qt.Orientation.Horizontal)
        controls.addWidget(self.play)
        controls.addWidget(self.position, 1)
        layout.addLayout(controls)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.durationChanged.connect(lambda d: self.position.setRange(0, d))
        self.player.positionChanged.connect(self._moved)
        self.position.sliderMoved.connect(self.player.setPosition)
        self.player.errorOccurred.connect(self._error)
        self.player.playbackStateChanged.connect(self._state)

    def open(self, path: Path) -> None:
        self.stack.setCurrentWidget(self.video)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def stop(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())

    def toggle(self) -> None:
        if self.player.playbackState() == self.player.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _moved(self, position: int) -> None:
        if not self.position.isSliderDown():
            self.position.setValue(position)

    def _state(self, state) -> None:
        playing = state == self.player.PlaybackState.PlayingState
        self.play.setIcon(theme.icon("pause" if playing else "play"))

    def _error(self, *_) -> None:
        self.message.setText(self.tr("This video can't be played on this computer."))
        self.stack.setCurrentWidget(self.message)


class PreviewScreen(Screen):
    """Photos and videos of a folder, one at a time."""

    def __init__(
        self,
        records: list[FileRecord],
        row: int,
        sources: Callable[[str], list[Path]],
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.records = records
        self.row = row
        self._sources = sources
        self._cache: OrderedDict[str, QPixmap | None] = OrderedDict()
        self._loading: set[str] = set()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)
        self._emitter = _Emitter(self)
        self._emitter.ready.connect(self._loaded)

        self.views = QStackedWidget()
        self.photo = PhotoView()
        self.views.addWidget(self.photo)
        self.video: VideoView | None = None
        self.body.addWidget(self.views, 1)

        self.counter = theme.set_role(QLabel(), "muted")
        self.previous = QPushButton(theme.icon("chevron-left"), self.tr("Previous"))
        self.previous.clicked.connect(lambda: self.go(-1))
        self.next = QPushButton(theme.icon("chevron-right"), self.tr("Next"))
        self.next.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next.clicked.connect(lambda: self.go(1))
        self._footer.insertWidget(1, self.counter)
        for button in (self.previous, self.next):
            button.setIconSize(QSize(24, 24))
            button.setMinimumWidth(140)
            self._footer.addWidget(button)
            button.show()
        self._update_footer()

        for key, step in ((Qt.Key.Key_Left, -1), (Qt.Key.Key_Right, 1)):
            QShortcut(QKeySequence(key), self, lambda s=step: self.go(s))
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.back_requested.emit)
        self.show_current()

    @property
    def record(self) -> FileRecord:
        return self.records[self.row]

    def go(self, step: int) -> None:
        row = self.row + step
        if 0 <= row < len(self.records):
            self.row = row
            self.show_current()

    def show_current(self) -> None:
        record = self.record
        folder, _, name = record.path.rpartition("/")
        self.set_texts(name, folder.replace("/", " › "))
        self.counter.setText(
            self.tr("%1 of %2")
            .replace("%1", str(self.row + 1))
            .replace("%2", str(len(self.records)))
        )
        self.previous.setEnabled(self.row > 0)
        self.next.setEnabled(self.row < len(self.records) - 1)
        if self.video is not None:
            self.video.stop()
        if scanner.kind_of(name) == scanner.VIDEO:
            self._show_video(record)
            return
        self.views.setCurrentWidget(self.photo)
        if record.hash in self._cache:
            self._show_photo(record.hash)
        else:
            self.photo.set_picture(None, self.tr("Loading…"))
        for neighbour in (self.row, self.row + 1, self.row - 1):
            if 0 <= neighbour < len(self.records):
                self._load(self.records[neighbour])

    def _show_video(self, record: FileRecord) -> None:
        if self.video is None:
            try:
                self.video = VideoView()
            except ImportError:  # Qt Multimedia or a system library is missing
                self.photo.set_picture(
                    None, self.tr("This video can't be played on this computer.")
                )
                self.views.setCurrentWidget(self.photo)
                return
            self.views.addWidget(self.video)
        self.views.setCurrentWidget(self.video)
        sources = [p for p in self._sources(record.path) if p.exists()]
        if sources:
            self.video.open(sources[0])
        else:
            self.video._error()

    def _load(self, record: FileRecord) -> None:
        if record.hash in self._cache or record.hash in self._loading:
            return
        if scanner.kind_of(record.path) == scanner.VIDEO:
            return
        self._loading.add(record.hash)
        self._pool.start(_Load(record.hash, self._sources(record.path), self._emitter))

    def _loaded(self, key: str, image: QImage) -> None:
        self._loading.discard(key)
        self._cache[key] = None if image.isNull() else QPixmap.fromImage(image)
        while len(self._cache) > KEEP:
            self._cache.popitem(last=False)
        if key == self.record.hash:
            self._show_photo(key)

    def _show_photo(self, key: str) -> None:
        self.photo.set_picture(
            self._cache[key], self.tr("This photo can't be opened: it may be damaged.")
        )

    def wait(self) -> None:
        self._pool.waitForDone(10000)

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt)
        if self.video is not None:
            self.video.stop()
        super().hideEvent(event)
