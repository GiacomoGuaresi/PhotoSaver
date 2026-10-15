import pytest

from photosaver.devtools import dev_disks
from photosaver.ui import app as app_mod
from photosaver.ui.controller import HOME
from photosaver.ui.viewer import ROLE_ENTRY, ViewerScreen


@pytest.fixture
def dev(tmp_path):
    root = tmp_path / "dev-disks"
    dev_disks.setup(root)
    return root


@pytest.fixture
def ui(qtbot, dev):
    app_mod.create_application([])
    window, controller = app_mod.build([dev / "disk-a", dev / "disk-b"])
    qtbot.addWidget(window)
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    yield window, controller
    controller.session.stop()
    if isinstance(window.current, ViewerScreen):
        window.current.loader.wait()


def entries(viewer):
    return [viewer.model.index(r).data(ROLE_ENTRY) for r in range(viewer.model.rowCount())]


def test_open_from_home(qtbot, ui):
    window, controller = ui
    window.current.browse.click()
    viewer = window.current
    assert isinstance(viewer, ViewerScreen)
    assert [e.name for e in entries(viewer)] == ["FOTO 2024", "FOTO 2025"]
    assert viewer.tree.topLevelItem(0).text(1) == "41"


def test_folders_and_thumbnails(qtbot, ui):
    window, controller = ui
    viewer = controller.show_viewer()
    viewer.show_folder("FOTO 2024/NEVE 2024")
    assert viewer.title.text() == "NEVE 2024"
    photos = entries(viewer)
    assert len(photos) == 10 and all(e.record is not None for e in photos)
    first = viewer.model.index(0)
    assert first.data(0x1) is None  # DecorationRole: asked, not ready yet
    qtbot.waitUntil(lambda: viewer.model.index(0).data(0x1) is not None, timeout=5000)
    assert viewer.model.index(0).data(0x1).width() == 320


def test_double_click_folder_opens_it(qtbot, ui):
    window, controller = ui
    viewer = controller.show_viewer()
    viewer._open(viewer.model.index(0))
    assert viewer.folder.path == "FOTO 2024"


def test_one_disk_is_enough(qtbot, dev):
    app_mod.create_application([])
    window, controller = app_mod.build([dev / "disk-b"])
    qtbot.addWidget(window)
    controller.start()
    window.current.one_disk.click()
    viewer = controller.show_viewer()
    viewer.show_folder("FOTO 2025/LAGO 2025")
    qtbot.waitUntil(lambda: viewer.model.index(0).data(0x1) is not None, timeout=5000)
    controller.session.stop()
    viewer.loader.wait()


def test_photo_that_cant_be_read(qtbot, ui, dev):
    window, controller = ui
    viewer = controller.show_viewer()
    viewer.show_folder("FOTO 2024/NEVE 2024")
    record = entries(viewer)[0].record
    for disk in ("disk-a", "disk-b"):
        (dev / disk / "Foto" / record.path).write_bytes(b"broken")
    viewer.model.index(0).data(0x1)
    qtbot.waitUntil(lambda: viewer.loader.failed(record.hash), timeout=5000)
    assert viewer.model.index(0).data(0x1) is None
