from datetime import datetime

import pytest
from PIL import Image

from photosaver.devtools import dev_disks
from photosaver.devtools.fake_media import Gps, make_photo


def _exif(path):
    with Image.open(path) as image:
        exif = image.getexif()
        return exif, exif.get_ifd(0x8769), exif.get_ifd(0x8825)


def test_photo_carries_date_camera_and_gps(tmp_path):
    taken = datetime(2026, 8, 10, 9, 30, 15)
    path = make_photo(
        tmp_path / "a.jpg", taken=taken, camera=("Make", "Model"), gps=Gps(45.5, -9.25)
    )

    exif, sub, gps = _exif(path)
    assert sub[0x9003] == "2026:08:10 09:30:15"
    assert (exif[0x010F], exif[0x0110]) == ("Make", "Model")
    assert gps[1] == "N" and gps[3] == "W"
    assert [float(v) for v in gps[2]] == [45.0, 30.0, 0.0]
    assert path.stat().st_mtime == taken.timestamp()


def test_photo_without_date_has_no_exif(tmp_path):
    exif, sub, gps = _exif(make_photo(tmp_path / "a.jpg"))
    assert not exif and not sub and not gps


def test_create_is_reproducible(tmp_path):
    def listing(root):
        return sorted(
            (p.relative_to(root).as_posix(), p.read_bytes()) for p in root.rglob("*") if p.is_file()
        )

    counts = dev_disks.create(tmp_path / "one", seed=7)
    dev_disks.create(tmp_path / "two", seed=7)
    assert listing(tmp_path / "one") == listing(tmp_path / "two")
    assert counts["photos"] > 50 and counts["videos"] > 0 and counts["ignored"] > 0


def test_create_layout(tmp_path):
    root = tmp_path / "dev-disks"
    dev_disks.create(root)
    assert sorted(p.name for p in root.iterdir()) == [".dev-disks", "desktop", "disk-a", "disk-b"]
    assert not any((root / "disk-a").iterdir())
    whatsapp = next((root / "desktop" / "LAGO 2026").glob("IMG-*-WA*.jpg"))
    assert not _exif(whatsapp)[0]


def test_reset_refuses_folders_without_marker(tmp_path):
    (tmp_path / "photos").mkdir()
    (tmp_path / "photos" / "keep.jpg").write_bytes(b"x")
    with pytest.raises(dev_disks.NotDevDisks):
        dev_disks.reset(tmp_path / "photos")
    assert (tmp_path / "photos" / "keep.jpg").exists()


def test_reset_removes_dev_disks(tmp_path):
    root = tmp_path / "dev-disks"
    dev_disks.create(root)
    dev_disks.reset(root)
    assert not root.exists()
