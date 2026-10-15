"""Fake photos and videos for development and tests: small, reproducible, no personal data.

Photos are real JPEGs with controlled EXIF (date, camera, GPS), so date and position
extraction can be tested; videos are placeholder bytes with an MP4 header.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

# EXIF tags
_MAKE = 0x010F
_MODEL = 0x0110
_DATETIME = 0x0132
_EXIF_IFD = 0x8769
_GPS_IFD = 0x8825
_DATETIME_ORIGINAL = 0x9003


@dataclass(frozen=True)
class Gps:
    lat: float
    lon: float


def _dms(value: float) -> tuple[float, float, float]:
    value = abs(value)
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = round(((value - degrees) * 60 - minutes) * 60, 2)
    return (float(degrees), float(minutes), seconds)


def make_photo(
    path: Path,
    *,
    taken: datetime | None = None,
    camera: tuple[str, str] | None = None,
    gps: Gps | None = None,
    seed: int = 0,
    size: tuple[int, int] = (320, 240),
    mtime: datetime | None = None,
) -> Path:
    """Write a JPEG with a random pattern and the given EXIF data.

    Without ``taken`` the photo has no EXIF at all, like those sent through WhatsApp.
    The file's modification time is ``mtime``, or ``taken`` when not given.
    """
    rng = random.Random(seed)
    image = Image.new("RGB", size, tuple(rng.randrange(256) for _ in range(3)))
    draw = ImageDraw.Draw(image)
    for _ in range(6):
        x0, y0 = rng.randrange(size[0]), rng.randrange(size[1])
        x1, y1 = x0 + rng.randrange(20, 160), y0 + rng.randrange(20, 120)
        draw.ellipse((x0, y0, x1, y1), fill=tuple(rng.randrange(256) for _ in range(3)))

    exif = Image.Exif()
    if taken is not None:
        stamp = taken.strftime("%Y:%m:%d %H:%M:%S")
        exif[_DATETIME] = stamp
        exif.get_ifd(_EXIF_IFD)[_DATETIME_ORIGINAL] = stamp
    if camera is not None:
        exif[_MAKE], exif[_MODEL] = camera
    if gps is not None:
        exif.get_ifd(_GPS_IFD).update(
            {
                1: "N" if gps.lat >= 0 else "S",
                2: _dms(gps.lat),
                3: "E" if gps.lon >= 0 else "W",
                4: _dms(gps.lon),
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=80, exif=exif)
    _set_mtime(path, mtime or taken)
    return path


def make_video(
    path: Path, *, seed: int = 0, size: int = 64 * 1024, mtime: datetime | None = None
) -> Path:
    """Write a placeholder MP4: a valid ``ftyp`` box followed by random bytes (not playable)."""
    rng = random.Random(seed)
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + rng.randbytes(max(0, size - len(header))))
    _set_mtime(path, mtime)
    return path


def make_file(path: Path, data: bytes = b"", *, mtime: datetime | None = None) -> Path:
    """Write any other file (documents, music, shortcuts…)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _set_mtime(path, mtime)
    return path


def _set_mtime(path: Path, when: datetime | None) -> None:
    if when is not None:
        stamp = when.timestamp()
        os.utime(path, (stamp, stamp))
