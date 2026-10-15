import dataclasses
import os
from datetime import UTC, datetime, timedelta

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import hashing, trash
from photosaver.core.index import OK, SCHEMA_VERSION


@pytest.fixture
def filled(arch):
    put(arch, "FOTO 2026/MARE/a.jpg", b"photo a")
    put(arch, "FOTO 2026/MARE/b.jpg", b"photo b")
    return arch


def test_schema_has_trash(filled):
    assert SCHEMA_VERSION == 2
    assert filled.index.trash() == []


def test_move_to_trash(filled):
    a = filled.disks[0]
    entry = trash.move_to_trash(
        filled, a, "FOTO 2026/MARE/a.jpg", hash_=hashing.hash_bytes(b"photo a")
    )

    assert not filled.path_on(a, "FOTO 2026/MARE/a.jpg").exists()
    stored = trash.trash_dir(a).joinpath(*entry.stored.split("/"))
    assert stored.read_bytes() == b"photo a"
    assert entry.stored.endswith("/FOTO 2026/MARE/a.jpg")
    assert filled.index.trash() == [entry]
    assert entry.id is not None and entry.size == 7 and entry.reason == trash.DELETED
    assert trash.size(filled, a) == 7
    assert filled.index.events()[0].kind == "trashed"
    # the folder stays, and the other disk is untouched
    assert filled.path_on(a, "FOTO 2026/MARE").is_dir()
    assert filled.path_on(filled.disks[1], "FOTO 2026/MARE/a.jpg").exists()


def test_restore_known_file(filled):
    a = filled.disks[0]
    entry = trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    trash.restore(filled, entry)
    assert filled.path_on(a, "FOTO 2026/MARE/a.jpg").read_bytes() == b"photo a"
    assert filled.index.trash() == []
    assert not any(trash.trash_dir(a).iterdir())


def test_restore_forgotten_file_lists_it_again(filled):
    a = filled.disks[0]
    entry = trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    with filled.index.transaction():
        filled.index.remove_file("FOTO 2026/MARE/a.jpg")
    trash.restore(filled, entry)
    record = filled.index.get_file("FOTO 2026/MARE/a.jpg")
    assert record.hash == hashing.hash_bytes(b"photo a")
    assert filled.index.copies(record.path)[a.id].state == OK


def test_restore_never_overwrites(filled):
    a = filled.disks[0]
    entry = trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    filled.path_on(a, "FOTO 2026/MARE/a.jpg").write_bytes(b"new")
    with pytest.raises(FileExistsError):
        trash.restore(filled, entry)
    assert filled.index.trash() == [entry]


def test_restore_needs_the_disk(filled, two_disks):
    entry = trash.move_to_trash(filled, filled.disks[1], "FOTO 2026/MARE/a.jpg")
    filled.sync_indexes()
    filled.close()
    only_a = archive_mod.Archive.open([two_disks[0]])
    with only_a, pytest.raises(FileNotFoundError, match="disk B is not connected"):
        trash.restore(only_a, entry)


def test_empty_all(filled):
    a, b = filled.disks
    trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    trash.move_to_trash(filled, b, "FOTO 2026/MARE/a.jpg")
    assert trash.empty(filled) == 2
    assert filled.index.trash() == []
    assert list(trash.trash_dir(a).iterdir()) == []
    assert filled.index.events()[0].kind == "trash_emptied"


def test_empty_old_only(filled):
    a = filled.disks[0]
    trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    old = trash.move_to_trash(filled, a, "FOTO 2026/MARE/b.jpg")
    with filled.index.transaction():
        filled.index.remove_trash(old.id)
        long_ago = (datetime.now(UTC) - timedelta(days=40)).isoformat(timespec="seconds")
        filled.index.add_trash(dataclasses.replace(old, id=None, trashed_at=long_ago))
    assert trash.empty(filled, older_than_days=30) == 1
    assert [e.path for e in filled.index.trash()] == ["FOTO 2026/MARE/a.jpg"]


def test_empty_skips_disconnected_disks(filled, two_disks):
    trash.move_to_trash(filled, filled.disks[1], "FOTO 2026/MARE/a.jpg")
    filled.sync_indexes()
    filled.close()
    with archive_mod.Archive.open([two_disks[0]]) as only_a:
        assert trash.empty(only_a) == 0
        assert len(only_a.index.trash()) == 1


def test_empty_tolerates_missing_files(filled):
    a = filled.disks[0]
    entry = trash.move_to_trash(filled, a, "FOTO 2026/MARE/a.jpg")
    os.remove(trash.trash_dir(a).joinpath(*entry.stored.split("/")))
    assert trash.empty(filled) == 1


def test_scanner_ignores_trash(filled):
    from photosaver.core import check

    trash.move_to_trash(filled, filled.disks[0], "FOTO 2026/MARE/a.jpg")
    report = check.quick_check(filled)
    assert [(d.kind, d.path) for d in report.differences] == [("missing", "FOTO 2026/MARE/a.jpg")]
