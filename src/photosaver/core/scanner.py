"""Find photos and videos in a folder tree.

Only photos, videos and camera RAW files belong to the archive. Everything else is
*ignored* but listed, so nothing is left behind unknowingly; hidden and system files
(``.photosaver/``, macOS ``._*`` files, ``Thumbs.db``…) are *skipped* silently.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

PHOTO = "photo"
VIDEO = "video"
RAW = "raw"

EXTENSIONS: dict[str, str] = {
    **dict.fromkeys(
        ["jpg", "jpeg", "jpe", "heic", "heif", "avif", "png", "webp", "gif", "bmp", "tif", "tiff"],
        PHOTO,
    ),
    **dict.fromkeys(
        ["mp4", "mov", "m4v", "3gp", "avi", "mkv", "mts", "m2ts", "wmv", "mpg", "mpeg", "webm"],
        VIDEO,
    ),
    **dict.fromkeys(
        ["dng", "nef", "nrw", "cr2", "cr3", "crw", "arw", "srf", "sr2", "raf", "orf", "rw2",
         "pef", "srw", "x3f", "rwl", "3fr", "erf", "kdc", "dcr", "mrw", "iiq"],
        RAW,
    ),
}  # fmt: skip

SYSTEM_NAMES = {"thumbs.db", "desktop.ini", "$recycle.bin", "system volume information"}


@dataclass(frozen=True)
class Entry:
    path: str  # relative to the scanned folder, with '/'
    size: int
    mtime_ns: int
    kind: str


@dataclass
class ScanResult:
    media: list[Entry] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)  # not photos or videos
    skipped: list[str] = field(default_factory=list)  # hidden and system files
    errors: list[tuple[str, str]] = field(default_factory=list)  # unreadable: (path, reason)

    @property
    def size(self) -> int:
        return sum(entry.size for entry in self.media)


def kind_of(name: str) -> str | None:
    """``photo``, ``video``, ``raw`` or None, from the file extension."""
    _, dot, extension = name.rpartition(".")
    return EXTENSIONS.get(extension.lower()) if dot else None


def is_hidden(name: str) -> bool:
    return name.startswith(".") or name.lower() in SYSTEM_NAMES


def scan(root: Path, *, on_file: Callable[[int], None] | None = None) -> ScanResult:
    """Walk ``root`` and classify every file. Symbolic links are never followed.

    ``on_file`` is called with the number of files seen so far, for progress.
    """
    result = ScanResult()
    seen = 0

    def walk(folder: Path, relative: PurePosixPath) -> None:
        nonlocal seen
        try:
            with os.scandir(folder) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as error:
            result.errors.append((relative.as_posix(), error.strerror or str(error)))
            return

        for entry in entries:
            path = (relative / entry.name).as_posix()
            if is_hidden(entry.name):
                result.skipped.append(path)
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    walk(Path(entry.path), relative / entry.name)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    result.ignored.append(path)  # symbolic links and special files
                    continue
                kind = kind_of(entry.name)
                if kind is None:
                    result.ignored.append(path)
                    continue
                stat = entry.stat(follow_symlinks=False)
            except OSError as error:
                result.errors.append((path, error.strerror or str(error)))
                continue
            result.media.append(Entry(path, stat.st_size, stat.st_mtime_ns, kind))
            seen += 1
            if on_file:
                on_file(seen)

    walk(root, PurePosixPath())
    return result
