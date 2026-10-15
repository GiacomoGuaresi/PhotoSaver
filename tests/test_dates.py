from datetime import datetime

import pytest

from photosaver.core import dates
from photosaver.devtools.fake_media import make_file, make_photo


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("20260810_093015.jpg", datetime(2026, 8, 10, 9, 30, 15)),
        ("20260810_093015(1).jpg", datetime(2026, 8, 10, 9, 30, 15)),
        ("IMG_20260810_093015.jpg", datetime(2026, 8, 10, 9, 30, 15)),
        ("PXL_20260810_093015123.jpg", datetime(2026, 8, 10, 9, 30, 15)),
        ("IMG-20260810-WA0001.jpg", datetime(2026, 8, 10)),
        ("VID-20260810-WA0002.mp4", datetime(2026, 8, 10)),
        ("Screenshot_20260810-093015.png", datetime(2026, 8, 10, 9, 30, 15)),
        ("2026-08-10 09.30.15.jpg", datetime(2026, 8, 10, 9, 30, 15)),
        ("vacanza 2026-08-10.jpg", datetime(2026, 8, 10)),
        ("DSC_0001.JPG", None),
        ("IMG_1234.JPG", None),
        ("20261310_093015.jpg", None),  # month 13
        ("18000810_093015.jpg", None),  # too old
        ("1234567820260810_093015.jpg", None),  # part of a longer number
    ],
)
def test_date_from_name(name, expected):
    assert dates.date_from_name(name) == expected


def test_exif_first(tmp_path):
    path = make_photo(tmp_path / "20200101_000000.jpg", taken=datetime(2026, 8, 10, 9, 30), seed=1)
    assert dates.taken(path, 0) == (datetime(2026, 8, 10, 9, 30), dates.EXIF)


def test_name_without_exif(tmp_path):
    path = make_photo(tmp_path / "IMG-20250504-WA0001.jpg", mtime=datetime(2025, 6, 1))
    assert dates.taken(path, path.stat().st_mtime_ns) == (datetime(2025, 5, 4), dates.NAME)


def test_mtime_last(tmp_path):
    path = make_photo(tmp_path / "DSC_0001.jpg", mtime=datetime(2024, 1, 2, 3, 4, 5))
    assert dates.taken(path, path.stat().st_mtime_ns) == (
        datetime(2024, 1, 2, 3, 4, 5),
        dates.MTIME,
    )


def test_not_an_image(tmp_path):
    path = make_file(tmp_path / "VID_20240102_030405.mp4", b"\x00" * 100)
    assert dates.date_from_exif(path) is None
    assert dates.taken(path, 0)[1] == dates.NAME
