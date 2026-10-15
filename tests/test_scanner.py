import os
import sys

import pytest

from photosaver.core import scanner
from photosaver.devtools import dev_disks


def touch(path, data=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("20260810_093015.jpg", "photo"),
        ("IMG.JPEG", "photo"),
        ("a.HEIC", "photo"),
        ("clip.MOV", "video"),
        ("v.3gp", "video"),
        ("DSC_0001.NEF", "raw"),
        ("x.dng", "raw"),
        ("note.txt", None),
        ("shortcut.lnk", None),
        ("jpg", None),
        ("archive.jpg.zip", None),
    ],
)
def test_kind_of(name, kind):
    assert scanner.kind_of(name) == kind


def test_scan_classifies(tmp_path):
    touch(tmp_path / "FOTO 2026" / "MARE 2026" / "a.jpg", b"12345")
    touch(tmp_path / "FOTO 2026" / "MARE 2026" / "b.mp4")
    touch(tmp_path / "FOTO 2026" / "c.NEF")
    touch(tmp_path / "FOTO 2026" / "doc.pdf")
    touch(tmp_path / "FOTO 2026" / "photo.lnk")
    touch(tmp_path / "FOTO 2026" / "Thumbs.db")
    touch(tmp_path / "FOTO 2026" / "._a.jpg")
    touch(tmp_path / ".photosaver" / "index.sqlite")
    touch(tmp_path / "FOTO 2026" / ".a.jpg.photosaver-partial")

    result = scanner.scan(tmp_path)

    assert [(e.path, e.kind) for e in result.media] == [
        ("FOTO 2026/MARE 2026/a.jpg", "photo"),
        ("FOTO 2026/MARE 2026/b.mp4", "video"),
        ("FOTO 2026/c.NEF", "raw"),
    ]
    assert result.media[0].size == 5
    assert result.size == 7
    assert result.ignored == ["FOTO 2026/doc.pdf", "FOTO 2026/photo.lnk"]
    assert sorted(result.skipped) == [
        ".photosaver",
        "FOTO 2026/._a.jpg",
        "FOTO 2026/.a.jpg.photosaver-partial",
        "FOTO 2026/Thumbs.db",
    ]
    assert result.errors == []


def test_scan_keeps_mtime(tmp_path):
    path = touch(tmp_path / "a.jpg")
    os.utime(path, ns=(1_600_000_000_123_456_789, 1_600_000_000_123_456_789))
    (entry,) = scanner.scan(tmp_path).media
    assert entry.mtime_ns == path.stat().st_mtime_ns


def test_scan_empty_and_zero_bytes(tmp_path):
    (tmp_path / "empty").mkdir()
    touch(tmp_path / "zero.jpg", b"")
    result = scanner.scan(tmp_path)
    assert [(e.path, e.size) for e in result.media] == [("zero.jpg", 0)]


def test_scan_progress(tmp_path):
    for n in range(3):
        touch(tmp_path / f"{n}.jpg")
    seen = []
    scanner.scan(tmp_path, on_file=seen.append)
    assert seen == [1, 2, 3]


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_symlinks_are_not_followed(tmp_path):
    outside = tmp_path / "outside"
    touch(outside / "secret.jpg")
    root = tmp_path / "root"
    root.mkdir()
    (root / "link-dir").symlink_to(outside)
    (root / "link.jpg").symlink_to(outside / "secret.jpg")
    result = scanner.scan(root)
    assert result.media == []
    assert sorted(result.ignored) == ["link-dir", "link.jpg"]


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions as non-root"
)
def test_unreadable_folder_is_reported(tmp_path):
    touch(tmp_path / "ok.jpg")
    locked = tmp_path / "locked"
    touch(locked / "a.jpg")
    locked.chmod(0)
    try:
        result = scanner.scan(tmp_path)
    finally:
        locked.chmod(0o755)
    assert [e.path for e in result.media] == ["ok.jpg"]
    assert [path for path, _ in result.errors] == ["locked"]


def test_scan_simulated_desktop(tmp_path):
    counts = dev_disks.create(tmp_path / "dev", seed=1)
    result = scanner.scan(tmp_path / "dev" / "desktop")
    kinds = [e.kind for e in result.media]
    assert kinds.count("photo") == counts["photos"]
    assert kinds.count("video") == counts["videos"]
    assert len(result.ignored) + len(result.skipped) == counts["ignored"]
