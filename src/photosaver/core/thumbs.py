"""Thumbnails: small JPEGs of photos, made with Pillow (no Qt, they are made in threads).

Thumbnails are named after the content hash of the photo, so a moved or renamed photo
keeps its thumbnail and copies of the same photo share one.
"""

from __future__ import annotations

import io
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
