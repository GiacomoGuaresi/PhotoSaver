import dataclasses
from datetime import UTC, datetime, timedelta

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import status, trash
from photosaver.core.disk import open_disk
from photosaver.core.index import Event
from photosaver.devtools import dev_disks
from photosaver.ui import app as app_mod
from photosaver.ui.controller import HOME
from photosaver.ui.history_trash import (
    HistoryScreen,
    TrashScreen,
    days_left,
    history_lines,
)


def event(kind, **detail):
    return Event("2026-10-15T10:00:00+00:00", kind, None, None, detail)


def test_history_lines_group_and_hide_details():
    events = [
        event("repaired"),
        event("repaired"),
        event("trashed"),
        event("upload_done", copied=3),
        event("upload"),
        event("upload_done", copied=2),
    ]
    lines = history_lines(events)
    assert [(line.kind, line.count) for line in lines] == [
        ("repaired", 2),
        ("upload_done", 1),
        ("upload_done", 1),
    ]


def test_days_left():
    now = datetime(2026, 10, 15, tzinfo=UTC)
    assert days_left((now - timedelta(days=10)).isoformat(), 30, now) == 20
    assert days_left((now - timedelta(days=40)).isoformat(), 30, now) == 0


def test_startup_empties_old_trash(arch):
    put(arch, "a.jpg", b"a")
    put(arch, "b.jpg", b"b")
    old = trash.move_to_trash(arch, arch.disks[0], "a.jpg")
    trash.move_to_trash(arch, arch.disks[0], "b.jpg")
    with arch.index.transaction():
        arch.index.remove_trash(old.id)
        long_ago = (datetime.now(UTC) - timedelta(days=31)).isoformat(timespec="seconds")
        arch.index.add_trash(dataclasses.replace(old, id=None, trashed_at=long_ago))
    arch.sync_indexes()
    result = status.startup_check(list(arch.disks))
    assert result.emptied == 1
    assert [e.path for e in arch.index.trash()] == ["b.jpg"]


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
    yield window, controller
    controller.shutdown()


def test_menu_disabled_until_home(qtbot, ui):
    window, controller = ui
    assert not controller.history_action.isEnabled()
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    assert controller.history_action.isEnabled() and controller.trash_action.isEnabled()


def test_history(qtbot, ui):
    window, controller = ui
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    controller.history_action.trigger()
    screen = window.current
    assert isinstance(screen, HistoryScreen)
    texts = [screen.tree.topLevelItem(i).text(1) for i in range(screen.tree.topLevelItemCount())]
    assert texts == ["Added 41 photos", "You prepared Disk 2", "You prepared Disk 1"]
    screen.back_button.click()
    assert controller.mode == HOME


def test_trash_restore_and_empty(qtbot, ui, dev, monkeypatch):
    window, controller = ui
    disks = [open_disk(dev / n) for n in ("disk-a", "disk-b")]
    with archive_mod.Archive.open(disks) as arch:
        path = next(r.path for r in arch.index.files())
        for disk in arch.disks:
            trash.move_to_trash(arch, disk, path)
        other = next(r.path for r in arch.index.files() if r.path != path)
        trash.move_to_trash(arch, arch.disks[0], other)
        arch.sync_indexes()
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)

    controller.trash_action.trigger()
    screen = window.current
    assert isinstance(screen, TrashScreen) and screen.tree.topLevelItemCount() == 2
    assert not screen.restore.isEnabled()
    item = next(
        screen.tree.topLevelItem(i)
        for i in range(2)
        if screen.tree.topLevelItem(i).data(0, 0x0100) == path
    )
    item.setSelected(True)
    screen.restore.click()
    screen = window.current
    assert screen.tree.topLevelItemCount() == 1
    for disk in disks:
        assert (disk.archive / path).exists()

    monkeypatch.setattr(TrashScreen, "confirm_empty", lambda self: True)
    screen.empty_button.click()
    assert window.current.tree.topLevelItemCount() == 0
    assert not window.current.empty_button.isEnabled()
