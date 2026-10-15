"""When a photo or video was taken: EXIF first, then the date in the file name, then the
file's modification date (the least reliable: it changes when files are copied around).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

EXIF = "exif"
NAME = "name"
MTIME = "mtime"

_EXIF_IFD = 0x8769
_DATETIME_ORIGINAL = 0x9003
_DATETIME_DIGITIZED = 0x9004
_DATETIME = 0x0132

_FIRST_YEAR, _LAST_YEAR = 1990, 2100

# Date (and maybe time) in names from phones and apps:
#   20260810_093015.jpg        Samsung
#   IMG_20260810_093015.jpg    Android, Pixel (PXL_20260810_093015123.jpg)
#   IMG-20260810-WA0001.jpg    WhatsApp (VID-…, AUD-…)
#   Screenshot_20260810-093015.png
#   2026-08-10 09.30.15.jpg    Dropbox camera upload
_NAME_PATTERNS = [
    re.compile(
        r"(?<!\d)(?P<y>\d{4})-?(?P<m>\d{2})-?(?P<d>\d{2})[ _\-T](?P<H>\d{2})[.:\-]?(?P<M>\d{2})"
        r"[.:\-]?(?P<S>\d{2})(?!\d{3}\d)"
    ),
    re.compile(r"(?<!\d)(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})-WA\d+"),
    re.compile(r"(?<!\d)(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?!\d)"),
]


def date_from_exif(path: Path) -> datetime | None:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
    except (OSError, UnidentifiedImageError, ValueError):
        return None
    sub = exif.get_ifd(_EXIF_IFD)
    for value in (sub.get(_DATETIME_ORIGINAL), sub.get(_DATETIME_DIGITIZED), exif.get(_DATETIME)):
        parsed = _parse_exif(value)
        if parsed:
            return parsed
    return None


def date_from_name(name: str) -> datetime | None:
    for pattern in _NAME_PATTERNS:
        for match in pattern.finditer(name):
            parts = {k: int(v) for k, v in match.groupdict().items()}
            parsed = _build(
                parts["y"], parts["m"], parts["d"],
                parts.get("H", 0), parts.get("M", 0), parts.get("S", 0),
            )  # fmt: skip
            if parsed:
                return parsed
    return None


def taken(path: Path, mtime_ns: int) -> tuple[datetime, str]:
    """Best guess of when the file was taken, and where the date comes from."""
    from_exif = date_from_exif(path)
    if from_exif:
        return from_exif, EXIF
    from_name = date_from_name(path.name)
    if from_name:
        return from_name, NAME
    return datetime.fromtimestamp(mtime_ns / 1e9), MTIME


def _parse_exif(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"\s*(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", value)
    return _build(*map(int, match.groups())) if match else None


def _build(y: int, m: int, d: int, hh: int = 0, mm: int = 0, ss: int = 0) -> datetime | None:
    if not _FIRST_YEAR <= y <= _LAST_YEAR:
        return None
    try:
        return datetime(y, m, d, hh, mm, ss)
    except ValueError:
        return None
