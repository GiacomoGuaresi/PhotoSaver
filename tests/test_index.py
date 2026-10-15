import sqlite3

import pytest

from photosaver.core import index as idx
from photosaver.core.index import FileRecord, Index


@pytest.fixture
def index(tmp_path):
    with Index.create(tmp_path / "index.sqlite", archive_id="arch") as index:
        yield index


def rec(path, hash_="h1", size=10):
    return FileRecord(path=path, size=size, mtime_ns=1_000, hash=hash_)


def test_create_sets_meta(index):
    assert index.archive_id == "arch"
    assert index.schema_version == idx.SCHEMA_VERSION
    assert index.revision == 1


def test_create_refuses_existing_file(tmp_path, index):
    with pytest.raises(FileExistsError):
        Index.create(index.path, archive_id="other")


def test_open_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        Index.open(tmp_path / "nope.sqlite")
    assert not (tmp_path / "nope.sqlite").exists()


def test_reopen_keeps_data(tmp_path, index):
    with index.transaction():
        index.put_file(rec("FOTO 2026/a.jpg"))
    index.close()
    with Index.open(tmp_path / "index.sqlite") as again:
        assert again.get_file("FOTO 2026/a.jpg").hash == "h1"
        assert again.revision == 2


def test_writes_need_a_transaction(index):
    with pytest.raises(idx.NotInTransaction):
        index.put_file(rec("a.jpg"))


def test_transaction_is_all_or_nothing(index):
    with pytest.raises(RuntimeError), index.transaction():
        index.put_file(rec("a.jpg"))
        raise RuntimeError
    assert index.get_file("a.jpg") is None
    assert index.revision == 1


def test_nested_transaction_bumps_once(index):
    with index.transaction():
        index.put_file(rec("a.jpg"))
        with index.transaction():
            index.put_file(rec("b.jpg"))
    assert index.revision == 2
    assert index.count_files() == (2, 20)


def test_files(index):
    with index.transaction():
        index.put_file(rec("b.jpg", "h2"))
        index.put_file(rec("a.jpg", "h1"))
        index.put_file(rec("x/a.jpg", "h1"))
    assert [f.path for f in index.files()] == ["a.jpg", "b.jpg", "x/a.jpg"]
    assert [f.path for f in index.files_with_hash("h1")] == ["a.jpg", "x/a.jpg"]
    assert index.get_file("a.jpg").added_at


def test_put_file_updates_in_place(index):
    with index.transaction():
        index.add_disk("d1", "A")
        index.put_file(rec("a.jpg", "h1"))
        index.set_copy("a.jpg", "d1", idx.OK)
        index.put_file(rec("a.jpg", "h2", size=20))
    assert index.get_file("a.jpg").hash == "h2"
    assert index.count_files() == (1, 20)
    assert index.copies("a.jpg")["d1"].state == idx.OK


def test_move_and_remove(index):
    with index.transaction():
        index.add_disk("d1", "A")
        index.put_file(rec("a.jpg"))
        index.set_copy("a.jpg", "d1", idx.OK)
        index.move_file("a.jpg", "x/a.jpg")
    assert index.get_file("a.jpg") is None
    assert index.copies("x/a.jpg")["d1"].state == idx.OK
    with index.transaction():
        index.remove_file("x/a.jpg")
    assert index.count_files() == (0, 0)
    with pytest.raises(KeyError), index.transaction():
        index.move_file("missing.jpg", "b.jpg")


def test_copies_per_disk(index):
    with index.transaction():
        index.add_disk("d1", "A")
        index.add_disk("d2", "B")
        index.add_disk("d3", "C")
        index.put_file(rec("a.jpg"))
        index.set_copy("a.jpg", "d1", idx.OK, verified_at="2026-10-15T10:00:00+00:00")
        index.set_copy("a.jpg", "d2", idx.CORRUPT)
    with index.transaction():
        index.set_copy("a.jpg", "d1", idx.MISSING)
    copies = index.copies("a.jpg")
    assert copies["d1"] == idx.Copy(idx.MISSING, "2026-10-15T10:00:00+00:00")
    assert copies["d2"] == idx.Copy(idx.CORRUPT, None)
    assert "d3" not in copies
    assert [d.label for d in index.disks()] == ["A", "B", "C"]


def test_set_copy_unknown(index):
    with pytest.raises(KeyError), index.transaction():
        index.set_copy("nope.jpg", "d1", idx.OK)
    with pytest.raises(sqlite3.IntegrityError), index.transaction():
        index.put_file(rec("a.jpg"))
        index.set_copy("a.jpg", "unknown-disk", idx.OK)


def test_events(index):
    with index.transaction():
        index.log("upload", path="a.jpg", disk_id="d1", size=10)
        index.log("check")
    events = index.events()
    assert [e.kind for e in events] == ["check", "upload"]
    assert events[1].detail == {"size": 10}
    assert events[0].detail == {}
    assert len(index.events(limit=1)) == 1


def test_copy_to(tmp_path, index):
    with index.transaction():
        index.put_file(rec("a.jpg"))
    target = tmp_path / "b" / "index.sqlite"
    target.parent.mkdir()
    target.write_bytes(b"old content")
    index.copy_to(target)
    with Index.open(target) as copy:
        assert copy.get_file("a.jpg") == index.get_file("a.jpg")
        assert copy.revision == index.revision
    assert sorted(p.name for p in target.parent.iterdir()) == ["index.sqlite"]


def test_newer_schema_is_refused(tmp_path, index):
    index.close()
    db = sqlite3.connect(tmp_path / "index.sqlite")
    db.execute(f"PRAGMA user_version = {idx.SCHEMA_VERSION + 1}")
    db.close()
    with pytest.raises(idx.UnsupportedSchema):
        Index.open(tmp_path / "index.sqlite")


def test_migrations_upgrade_old_index(tmp_path, monkeypatch):
    path = tmp_path / "index.sqlite"
    Index.create(path, archive_id="arch").close()
    monkeypatch.setattr(idx, "MIGRATIONS", [*idx.MIGRATIONS, "CREATE TABLE extra (x INTEGER);"])
    monkeypatch.setattr(idx, "SCHEMA_VERSION", idx.SCHEMA_VERSION + 1)
    with Index.open(path) as index:
        assert index.schema_version == idx.SCHEMA_VERSION
        assert index.archive_id == "arch"


def test_meta_and_copies_on(index):
    with index.transaction():
        index.set_meta("x", "1")
        index.add_disk("d1", "A")
        index.put_file(rec("a.jpg"))
        index.put_file(rec("b.jpg"))
        index.set_copy("a.jpg", "d1", idx.OK)
    assert index.get_meta("x") == "1"
    assert index.copies_on("d1") == {"a.jpg": idx.Copy(idx.OK, None)}
    with index.transaction():
        index.delete_meta("x")
    assert index.get_meta("x") is None
