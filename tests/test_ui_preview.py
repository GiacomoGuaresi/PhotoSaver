from datetime import datetime

import pytest
from PySide6.QtCore import Qt

from photosaver.core import hashing
from photosaver.core.index import FileRecord
from photosaver.devtools.fake_media import make_photo, make_video
from photosaver.ui import app as app_mod
from photosaver.ui.preview import PreviewScreen


@pytest.fixture
def folder(tmp_path):
    archive = tmp_path / "Foto"
    paths = [
        make_photo(archive / "MARE" / "a.jpg", taken=datetime(2026, 1, 1), size=(800, 600), seed=1),
        make_photo(archive / "MARE" / "b.jpg", size=(600, 800), seed=2),
        make_video(archive / "MARE" / "c.mp4"),
    ]
    (archive / "MARE" / "d.jpg").write_bytes(b"broken")
    paths.append(archive / "MARE" / "d.jpg")
    records = [
        FileRecord(p.relative_to(archive).as_posix(), p.stat().st_size, 0, hashing.hash_file(p))
        for p in paths
    ]
    return archive, records


@pytest.fixture
def preview(qtbot, folder):
    app_mod.create_application([])
    archive, records = folder
    screen = PreviewScreen(records, 0, lambda path: [archive.joinpath(*path.split("/"))])
    qtbot.addWidget(screen)
    screen.resize(1000, 700)
    screen.show()
    yield screen
    screen.wait()
    if screen.video is not None:
        screen.video.stop()


def test_photo_is_shown(qtbot, preview):
    assert preview.title.text() == "a.jpg" and preview.subtitle.text() == "MARE"
    assert preview.counter.text() == "1 of 4" and not preview.previous.isEnabled()
    qtbot.waitUntil(
        lambda: preview.photo.pixmap() is not None and not preview.photo.pixmap().isNull()
    )


def test_navigation_with_buttons_and_keys(qtbot, preview):
    preview.next.click()
    assert preview.title.text() == "b.jpg" and preview.previous.isEnabled()
    qtbot.keyClick(preview, Qt.Key.Key_Left)
    assert preview.title.text() == "a.jpg"
    preview.go(-1)  # already the first
    assert preview.row == 0


def test_neighbours_are_preloaded(qtbot, preview):
    qtbot.waitUntil(lambda: len(preview._cache) == 2)  # a.jpg and b.jpg


def test_broken_photo(qtbot, preview):
    preview.go(3)
    qtbot.waitUntil(lambda: "damaged" in preview.photo.text())
    assert not preview.next.isEnabled()


def test_video(qtbot, preview):
    preview.go(2)
    assert preview.video is not None and preview.views.currentWidget() is preview.video
    preview.go(1)
    assert preview.views.currentWidget() is preview.photo


def test_escape_goes_back(qtbot, preview):
    back = []
    preview.back_requested.connect(lambda: back.append(1))
    qtbot.keyClick(preview, Qt.Key.Key_Escape)
    assert back == [1]
