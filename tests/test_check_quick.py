import os
import shutil
import sys

import pytest
from conftest import put

from photosaver.core import check, hashing


@pytest.fixture
def filled(arch):
    put(arch, "FOTO 2026/MARE 2026/a.jpg", b"photo a" * 100)
    put(arch, "FOTO 2026/MARE 2026/b.jpg", b"photo b" * 100)
    put(arch, "FOTO 2025/c.mp4", b"video c" * 100)
    return arch


def on(arch, label, path):
    disk = next(d for d in arch.disks if d.label == label)
    return disk, arch.path_on(disk, path)


def kinds(arch, report):
    labels = {d.id: d.label for d in arch.disks}
    return sorted((d.kind, labels[d.disk_id], d.path) for d in report.differences)


def test_clean(filled):
    report = check.quick_check(filled)
    assert report.clean
    assert report.files == 3 and len(report.disks) == 2


def test_missing(filled):
    _, path = on(filled, "B", "FOTO 2025/c.mp4")
    path.unlink()
    assert kinds(filled, check.quick_check(filled)) == [("missing", "B", "FOTO 2025/c.mp4")]


def test_untracked_is_hashed(filled):
    disk, path = on(filled, "A", "FOTO 2026/new.jpg")
    path.write_bytes(b"added by hand")
    report = check.quick_check(filled)
    assert kinds(filled, report) == [("untracked", "A", "FOTO 2026/new.jpg")]
    assert report.differences[0].hash == hashing.hash_bytes(b"added by hand")


def test_corrupt_same_date(filled):
    _, path = on(filled, "A", "FOTO 2026/MARE 2026/a.jpg")
    stat = path.stat()
    path.write_bytes(b"")  # truncated, date untouched
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert kinds(filled, check.quick_check(filled)) == [
        ("corrupt", "A", "FOTO 2026/MARE 2026/a.jpg")
    ]


def test_modified(filled):
    _, path = on(filled, "B", "FOTO 2026/MARE 2026/b.jpg")
    stat = path.stat()
    path.write_bytes(b"edited")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 60 * 10**9))
    report = check.quick_check(filled)
    assert kinds(filled, report) == [("modified", "B", "FOTO 2026/MARE 2026/b.jpg")]
    assert report.differences[0].size == len(b"edited")


def test_date_only_change_is_fine(filled):
    _, path = on(filled, "A", "FOTO 2025/c.mp4")
    os.utime(path, ns=(0, path.stat().st_mtime_ns + 3600 * 10**9))
    assert check.quick_check(filled).clean


def test_same_size_and_date_is_not_read(filled, monkeypatch):
    monkeypatch.setattr(hashing, "hash_file", lambda *a, **k: pytest.fail("read"))
    assert check.quick_check(filled).clean


def test_small_date_differences_are_tolerated(filled):
    _, path = on(filled, "B", "FOTO 2025/c.mp4")
    os.utime(path, ns=(0, path.stat().st_mtime_ns + 1_500_000_000))
    assert check.quick_check(filled).clean


def test_missing_archive_folder(filled):
    disk, _ = on(filled, "B", "x")
    shutil.rmtree(disk.archive)
    report = check.quick_check(filled)
    assert sorted(d.path for d in report.of_kind(check.MISSING)) == [
        "FOTO 2025/c.mp4",
        "FOTO 2026/MARE 2026/a.jpg",
        "FOTO 2026/MARE 2026/b.jpg",
    ]
    assert report.errors == [(disk.id, "", "archive folder not found")]


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions as non-root"
)
def test_unreadable_folder_is_an_error_not_missing(filled):
    disk, path = on(filled, "A", "FOTO 2026/MARE 2026/a.jpg")
    path.parent.chmod(0)
    try:
        report = check.quick_check(filled)
    finally:
        path.parent.chmod(0o755)
    assert report.differences == []
    assert report.errors == [(disk.id, "FOTO 2026/MARE 2026", "Permission denied")]
