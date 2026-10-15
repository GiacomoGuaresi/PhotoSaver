"""Pillow setup shared by the modules that open photos: HEIC/HEIF support (iPhones and
recent Android phones) when pillow-heif is installed."""

from __future__ import annotations

from functools import cache


@cache
def setup() -> bool:
    try:
        import pillow_heif
    except ImportError:
        return False
    pillow_heif.register_heif_opener()
    return True
