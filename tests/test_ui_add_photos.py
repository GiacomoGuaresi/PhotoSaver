import time

import pytest

from photosaver.core import archive as archive_mod
from photosaver.core import upload
from photosaver.core.disk import open_disk
from photosaver.devtools import dev_disks
from photosaver.ui import app as app_mod
from photosaver.ui.add_photos import ChooseFoldersScreen, PreviewScreen, SummaryScreen
from photosaver.ui.controller import HOME
from photosaver.ui.home import HomeScreen


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
    for worker in list(controller._workers):
        worker.wait(10000)


def archive_files(dev):
    disks = [open_disk(dev / "disk-a"), open_disk(dev / "disk-b")]
    with archive_mod.Archive.open(disks) as arch:
        return {r.path for r in arch.index.files()}


def to_preview(qtbot, window, *folders):
    window.current.add.click()
    choose = window.current
    assert isinstance(choose, ChooseFoldersScreen) and not choose.primary.isEnabled()
    for folder in folders:
        choose.add_folder(folder)
    choose.primary.click()
    qtbot.waitUntil(lambda: isinstance(window.current, PreviewScreen), timeout=10000)
    return window.current


def test_add_photos_and_delete_originals(qtbot, ui, dev):
    window, controller = ui
    sea = dev / "desktop" / "MARE 2026"
    preview = to_preview(qtbot, window, sea)
    (card,) = preview.cards
    assert "FOTO 2026 › MARE 2026" in card.destination.text()
    assert preview.primary.isEnabled() and "33" in preview.primary.text()

    preview.primary.click()
    qtbot.waitUntil(lambda: isinstance(window.current, SummaryScreen), timeout=20000)
    summary = window.current
    assert "33" in summary.subtitle.text()
    summary.delete_requested.emit()
    qtbot.waitUntil(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))
    assert window.current.status.role == "safe"
    assert not sea.exists()
    assert "FOTO 2026/MARE 2026/Spiaggia" in {p.rsplit("/", 1)[0] for p in archive_files(dev)}


def test_keep_originals_and_ignored_files_are_told(qtbot, ui, dev):
    window, controller = ui
    lake = dev / "desktop" / "LAGO 2026"
    preview = to_preview(qtbot, window, lake)
    assert "3" in preview.cards[0].notes.text()  # three files that are not photos
    preview.primary.click()
    qtbot.waitUntil(lambda: isinstance(window.current, SummaryScreen), timeout=20000)
    window.current.keep_requested.emit()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    assert lake.exists()


def test_already_there(qtbot, ui, dev):
    window, _ = ui
    preview = to_preview(qtbot, window, dev / "desktop" / "vecchio-archivio" / "FOTO FAMIGLIA")
    assert not preview.primary.isEnabled() and not preview.nothing.isHidden()


def test_change_destination(qtbot, ui, dev):
    window, controller = ui
    preview = to_preview(qtbot, window, dev / "desktop" / "MARE 2026")
    flow = next(c for c in controller.children() if hasattr(c, "plan"))
    flow.plan.folders[0].destination = "VIAGGI/Mare"
    flow._resolve()
    assert "VIAGGI › Mare" in preview.cards[0].destination.text()


def test_duplicates_toggle(qtbot, ui, dev, tmp_path):
    window, controller = ui
    copy = tmp_path / "copia"
    copy.mkdir()
    some = next((dev / "disk-a" / "Foto" / "FOTO 2024").glob("*.jpg"))
    (copy / "stessa foto.jpg").write_bytes(some.read_bytes())
    preview = to_preview(qtbot, window, copy)
    assert not preview.duplicates.isHidden() and not preview.primary.isEnabled()
    preview.duplicates.setChecked(True)
    assert preview.primary.isEnabled()


def test_folders_on_the_disks_are_refused(qtbot, ui, dev):
    window, _ = ui
    window.current.add.click()
    choose = window.current
    choose.add_folder(dev / "disk-a" / "Foto" / "FOTO 2024")
    assert choose.list.count() == 0 and not choose.warning.isHidden()


def test_stop_copy(qtbot, ui, dev, monkeypatch):
    window, controller = ui
    preview = to_preview(qtbot, window, dev / "desktop" / "MARE 2026")
    real = upload.apply

    def slow_apply(plan, archive, *, on_progress=None, should_stop=None):
        deadline = time.monotonic() + 5
        while not should_stop() and time.monotonic() < deadline:  # in the worker thread
            time.sleep(0.01)
        return real(plan, archive, on_progress=on_progress, should_stop=should_stop)

    monkeypatch.setattr(upload, "apply", slow_apply)
    preview.primary.click()
    busy = window.current
    busy.footer.findChildren(type(busy.back_button))[-1].click()  # "Stop"
    qtbot.waitUntil(lambda: window.current.title.text() == "Copy stopped", timeout=10000)
    window.current.primary.click()
    qtbot.waitUntil(lambda: controller.mode == HOME)
