"""Content hashes, read in streaming so files of any size use little memory.

SHA-256: fast enough (hardware-accelerated on recent CPUs, far above the speed of a USB
disk) and checkable without the app (``sha256sum``, ``certutil -hashfile``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

ALGORITHM = "sha256"
CHUNK = 1 << 20  # 1 MiB


class Cancelled(Exception):
    """Hashing was stopped by the caller."""


def new_hasher():
    return hashlib.sha256()


def hash_file(
    path: Path,
    *,
    on_progress: Callable[[int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> str:
    """Hex digest of the file content.

    ``on_progress`` receives the number of bytes read for each chunk; ``should_stop`` is
    polled between chunks and raises :class:`Cancelled` when it returns True.
    """
    hasher = new_hasher()
    buffer = bytearray(CHUNK)
    view = memoryview(buffer)
    with path.open("rb", buffering=0) as file:
        while read := file.readinto(buffer):
            hasher.update(view[:read])
            if on_progress:
                on_progress(read)
            if should_stop and should_stop():
                raise Cancelled(str(path))
    return hasher.hexdigest()


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
