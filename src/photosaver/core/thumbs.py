"""Thumbnails: small JPEGs of photos, made with Pillow (no Qt, they are made in threads).

Thumbnails are named after the content hash of the photo, so a moved or renamed photo
keeps its thumbnail and copies of the same photo share one.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from . import imaging
from .scanner import PHOTO, RAW, VIDEO, kind_of

imaging.setup()

SIZE = 320  # pixels, the longest side
QUALITY = 80


class NoThumbnail(Exception):
    """The file can't be read as an image (a video, a damaged photo…)."""


def make_thumbnail(path: Path, size: int = SIZE) -> bytes:
    """A JPEG of at most ``size`` pixels, turned the right way up (EXIF orientation)."""
    kind = kind_of(path.name)
    if kind == VIDEO:
        raise NoThumbnail(f"{path.name} is a video")
    try:
        image = _open(path) if kind == RAW else Image.open(path)
        with image:
            image.draft("RGB", (size, size))  # JPEG: decode at a smaller scale, much faster
            image = ImageOps.exif_transpose(image)
            image.thumbnail((size, size))
            if image.mode != "RGB":
                image = image.convert("RGB")
            out = io.BytesIO()
            image.save(out, "JPEG", quality=QUALITY)
            return out.getvalue()
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError) as error:
        raise NoThumbnail(f"{path.name}: {error}") from error


def _open(path: Path) -> Image.Image:
    """A RAW file: its embedded preview if any, else Pillow's own reading."""
    try:
        import rawpy
    except ImportError:
        return Image.open(path)
    try:
        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
    except (rawpy.LibRawError, OSError):
        return Image.open(path)
    if thumb.format == rawpy.ThumbFormat.JPEG:
        return Image.open(io.BytesIO(thumb.data))
    return Image.fromarray(thumb.data)


def can_have_thumbnail(name: str) -> bool:
    return kind_of(name) in (PHOTO, RAW)


# Thumbnails kept on the disks: ready on any computer

CACHE_DIR = "miniature"


def cache_path(data_dir: Path, hash_: str) -> Path:
    """``.photosaver/miniature/ab/abcdef….jpg``: a folder per first two characters."""
    return data_dir / CACHE_DIR / hash_[:2] / f"{hash_}.jpg"


def read_cached(data_dirs: list[Path], hash_: str) -> bytes | None:
    for data_dir in data_dirs:
        try:
            return cache_path(data_dir, hash_).read_bytes()
        except OSError:
            continue
    return None


def store(data_dirs: list[Path], hash_: str, data: bytes) -> None:
    """Save a thumbnail on every disk; a disk that can't be written is just skipped."""
    for data_dir in data_dirs:
        path = cache_path(data_dir, hash_)
        if path.exists():
            continue
        tmp = path.with_name(path.name + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError:
            with contextlib.suppress(OSError):
                tmp.unlink()


def thumbnail(data_dirs: list[Path], sources: list[Path], hash_: str) -> bytes | None:
    """From the disks if already made, else made from the first readable copy and saved."""
    cached = read_cached(data_dirs, hash_)
    if cached is not None:
        return cached
    for source in sources:
        try:
            data = make_thumbnail(source)
        except NoThumbnail:
            continue
        store(data_dirs, hash_, data)
        return data
    return None


def missing(data_dirs: list[Path], records) -> list:
    """Records of photos without a thumbnail on every disk."""
    return [
        record
        for record in records
        if can_have_thumbnail(record.path)
        and not all(cache_path(d, record.hash).exists() for d in data_dirs)
    ]


def fill(
    data_dirs: list[Path],
    archives: list[Path],
    records,
    *,
    on_progress=None,
    should_stop=None,
) -> int:
    """Make the missing thumbnails; returns how many were made or copied."""
    todo = missing(data_dirs, records)
    for n, record in enumerate(todo):
        if should_stop and should_stop():
            break
        sources = [archive.joinpath(*record.path.split("/")) for archive in archives]
        thumbnail(data_dirs, sources, record.hash)
        if on_progress:
            on_progress(n + 1, len(todo))
    return len(todo)
