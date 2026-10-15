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
    controller.shutdown()


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
    controller.shutdown()


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


def cached(dev):
    return {
        disk: len(list((dev / disk / ".photosaver" / "miniature").rglob("*.jpg")))
        for disk in ("disk-a", "disk-b")
    }


def test_thumbnails_are_made_in_the_background(qtbot, ui, dev):
    # 41 files, one is a video
    qtbot.waitUntil(lambda: cached(dev) == {"disk-a": 40, "disk-b": 40}, timeout=20000)


def test_viewer_saves_thumbnails_on_the_disks(qtbot, ui, dev):
    window, controller = ui
    controller.stop_thumbnails()
    viewer = controller.show_viewer()
    viewer.show_folder("FOTO 2025/LAGO 2025")
    for row in range(viewer.model.rowCount()):
        viewer.model.index(row).data(0x1)
    viewer.loader.wait()
    assert cached(dev)["disk-a"] >= 14 and cached(dev)["disk-b"] >= 14


def test_operations_stop_the_background_thumbnails(qtbot, ui):
    window, controller = ui
    window.current.add.click()
    assert controller._filler is None


def test_double_click_photo_opens_preview(qtbot, ui):
    from photosaver.ui.preview import PreviewScreen

    window, controller = ui
    viewer = controller.show_viewer()
    viewer.show_folder("FOTO 2024/NEVE 2024")
    viewer._open(viewer.model.index(3))
    preview = window.current
    assert isinstance(preview, PreviewScreen) and preview.row == 3
    assert len(preview.records) == 10
    preview.back_button.click()
    assert window.current is viewer


def test_badges(qtbot, dev):
    from photosaver.ui.viewer import ROLE_PROBLEM

    dev_disks.break_disks(dev, ["delete"], seed=1)  # a photo missing on disk 1
    app_mod.create_application([])
    window, controller = app_mod.build([dev / "disk-a", dev / "disk-b"])
    qtbot.addWidget(window)
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    viewer = controller.show_viewer()
    (path,) = [p for p in viewer.model.problems]
    folder = path.rsplit("/", 1)[0]
    top = path.split("/")[0]
    tops = {e.name: viewer.model.index(r) for r, e in enumerate(entries(viewer))}
    assert "1 photo here needs attention" in tops[top].data(ROLE_PROBLEM)
    other = next(name for name in tops if name != top)
    assert tops[other].data(ROLE_PROBLEM) is None
    viewer.show_folder(folder)
    rows = {e.record.path: viewer.model.index(r) for r, e in enumerate(entries(viewer)) if e.record}
    assert rows[path].data(ROLE_PROBLEM).startswith("Missing on Disk 1")
    assert sum(1 for i in rows.values() if i.data(ROLE_PROBLEM)) == 1
    assert viewer._items[folder].toolTip(0)
    controller.shutdown()
