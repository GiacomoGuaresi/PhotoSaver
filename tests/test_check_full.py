import os

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import check, hashing
from photosaver.core.index import CORRUPT, MISSING, MODIFIED, OK


@pytest.fixture
def filled(arch):
    for n in range(6):
        put(arch, f"FOTO 2026/{n}.jpg", bytes([n]) * 5000)
    return arch


def disk(arch, label):
    return next(d for d in arch.disks if d.label == label)


def flip_byte_keep_date(path):
    """Silent corruption: one byte changes, size and date do not."""
    stat = path.stat()
    data = bytearray(path.read_bytes())
    data[100] ^= 0xFF
    path.write_bytes(bytes(data))
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def test_clean_and_recorded(filled):
    seen = []
    report = check.full_check(filled, on_progress=lambda d, t: seen.append((d, t)))
    assert report.clean
    assert seen[-1] == (2 * 6 * 5000, 2 * 6 * 5000)
    for d in filled.disks:
        assert {c.state for c in filled.index.copies_on(d.id).values()} == {OK}
        assert all(c.verified_at for c in filled.index.copies_on(d.id).values())
        assert check.last_full_check(filled, d)
    assert filled.index.get_meta(check.FULL_CHECK_RUN) is None
    assert filled.index.events()[0].kind == "full_check_done"


def test_finds_bit_rot_the_quick_check_misses(filled):
    path = filled.path_on(disk(filled, "B"), "FOTO 2026/3.jpg")
    flip_byte_keep_date(path)
    assert check.quick_check(filled).clean

    report = check.full_check(filled)
    (diff,) = report.differences
    assert (diff.kind, diff.disk_id, diff.path) == (
        check.CORRUPT,
        disk(filled, "B").id,
        "FOTO 2026/3.jpg",
    )
    assert diff.hash == hashing.hash_file(path)
    copies = filled.index.copies("FOTO 2026/3.jpg")
    assert copies[disk(filled, "B").id].state == CORRUPT
    assert copies[disk(filled, "A").id].state == OK


def test_missing_and_modified_are_recorded(filled):
    filled.path_on(disk(filled, "A"), "FOTO 2026/0.jpg").unlink()
    path = filled.path_on(disk(filled, "A"), "FOTO 2026/1.jpg")
    path.write_bytes(b"edited")
    os.utime(path, ns=(0, path.stat().st_mtime_ns + 10**12))
    report = check.full_check(filled)
    assert sorted((d.kind, d.path) for d in report.differences) == [
        (check.MISSING, "FOTO 2026/0.jpg"),
        (check.MODIFIED, "FOTO 2026/1.jpg"),
    ]
    a = filled.index.copies_on(disk(filled, "A").id)
    assert (a["FOTO 2026/0.jpg"].state, a["FOTO 2026/1.jpg"].state) == (MISSING, MODIFIED)


def test_resume_after_interruption(filled, monkeypatch):
    flip_byte_keep_date(filled.path_on(disk(filled, "A"), "FOTO 2026/0.jpg"))
    monkeypatch.setattr(check, "WRITE_EVERY", 0)
    read = []
    limit = [5]
    real = hashing.hash_file

    def interrupted_after_limit(path, **kwargs):
        if len(read) >= limit[0]:
            raise hashing.Cancelled(str(path))
        read.append(path)
        return real(path, **kwargs)

    monkeypatch.setattr(hashing, "hash_file", interrupted_after_limit)
    with pytest.raises(hashing.Cancelled):
        check.full_check(filled)
    assert filled.index.get_meta(check.FULL_CHECK_RUN)
    verified = sum(
        1 for d in filled.disks for c in filled.index.copies_on(d.id).values() if c.verified_at
    )
    assert verified == 5

    read.clear()
    limit[0] = 100
    report = check.full_check(filled)
    assert len(read) == 12 - 5
    assert [(d.kind, d.path) for d in report.differences] == [(check.CORRUPT, "FOTO 2026/0.jpg")]
    assert filled.index.get_meta(check.FULL_CHECK_RUN) is None


def test_stop_request_cancels(filled):
    with pytest.raises(hashing.Cancelled):
        check.full_check(filled, should_stop=lambda: True)


def test_untracked_files_are_reported(filled):
    put(filled, "FOTO 2026/new.jpg", b"by hand", disks=filled.disks[:1], index=False)
    (diff,) = check.full_check(filled).differences
    assert (diff.kind, diff.path) == (check.UNTRACKED, "FOTO 2026/new.jpg")


def test_one_disk_only(filled, two_disks):
    filled.close()
    with archive_mod.Archive.open([two_disks[1]]) as only_b:
        report = check.full_check(only_b)
        assert report.clean and report.disks == [two_disks[1].id]
        assert check.last_full_check(only_b, two_disks[1])
        assert not only_b.index.copies_on(two_disks[0].id)["FOTO 2026/0.jpg"].verified_at


def test_worker_crash_is_raised(filled, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(check.scanner, "scan", boom)
    with pytest.raises(RuntimeError, match="boom"):
        check.full_check(filled)
