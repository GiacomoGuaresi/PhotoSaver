"""The app's trash: files deleted or replaced by the app are moved here, not destroyed.

Every disk has its own trash, ``.photosaver/cestino/``, so moving a file there is just
a rename on the same disk. The index lists every trashed file (on every disk), with its
original path, so it can be restored. The trash is emptied by hand or, for files older
than a number of days, automatically.

::

    .photosaver/cestino/20261015T190000-1a2b3c/FOTO 2026/MARE 2026/a.jpg
                        └ when and which batch ┘└ original path in the archive ┘
"""

from __future__ import annotations

import contextlib
import dataclasses
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import hashing
from .archive import Archive
from .disk import Disk
from .index import OK, FileRecord, TrashEntry, now

TRASH_DIR = "cestino"
DEFAULT_DAYS = 30

# Reasons
DELETED = "deleted"
REPLACED = "replaced"  # a damaged or edited copy, replaced by a good one


def trash_dir(disk: Disk) -> Path:
    return disk.data_dir / TRASH_DIR


def move_to_trash(
    archive: Archive, disk: Disk, path: str, *, reason: str = DELETED, hash_: str | None = None
) -> TrashEntry:
    """Move an archive file of ``disk`` to its trash and record it in the index."""
    source = archive.path_on(disk, path)
    stat = source.stat()
    batch = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    stored = f"{batch}/{path}"
    target = trash_dir(disk).joinpath(*stored.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    os.rename(source, target)
    entry = TrashEntry(
        None, disk.id, path, stored, stat.st_size, stat.st_mtime_ns, hash_, now(), reason
    )
    with archive.index.transaction():
        entry_id = archive.index.add_trash(entry)
        archive.index.log("trashed", path=path, disk_id=disk.id, reason=reason)
    return dataclasses.replace(entry, id=entry_id)


def restore(archive: Archive, entry: TrashEntry) -> None:
    """Put a trashed file back where it was, on its disk.

    If the archive no longer lists the file, it is listed again; the other disks get it
    back with the next check ("missing on B: copy from A").
    """
    disk = _connected(archive, entry.disk_id)
    target = archive.path_on(disk, entry.path)
    if target.exists():
        raise FileExistsError(f"{entry.path} already exists on disk {disk.label}")
    stored = trash_dir(disk).joinpath(*entry.stored.split("/"))
    digest = entry.hash or hashing.hash_file(stored)
    target.parent.mkdir(parents=True, exist_ok=True)
    os.rename(stored, target)
    _remove_empty_parents(stored.parent, trash_dir(disk))
    with archive.index.transaction():
        archive.index.remove_trash(entry.id)
        record = archive.index.get_file(entry.path)
        if record is None:
            archive.index.put_file(FileRecord(entry.path, entry.size, entry.mtime_ns, digest))
            record = archive.index.get_file(entry.path)
        if record.hash == digest:
            archive.index.set_copy(entry.path, disk.id, OK)
        archive.index.log("restored", path=entry.path, disk_id=disk.id)


def empty(archive: Archive, *, older_than_days: int | None = None) -> int:
    """Delete for good the trashed files on the connected disks (all, or the old ones).

    Returns how many files were deleted. Files on disks that are not connected stay.
    """
    limit = (
        datetime.now(UTC) - timedelta(days=older_than_days) if older_than_days is not None else None
    )
    deleted = 0
    for disk in archive.disks:
        for entry in archive.index.trash(disk.id):
            if limit is not None and datetime.fromisoformat(entry.trashed_at) > limit:
                continue
            stored = trash_dir(disk).joinpath(*entry.stored.split("/"))
            with contextlib.suppress(FileNotFoundError):
                stored.unlink()
            _remove_empty_parents(stored.parent, trash_dir(disk))
            with archive.index.transaction():
                archive.index.remove_trash(entry.id)
            deleted += 1
    if deleted:
        with archive.index.transaction():
            archive.index.log("trash_emptied", files=deleted, older_than_days=older_than_days)
    return deleted


def size(archive: Archive, disk: Disk) -> int:
    return sum(entry.size for entry in archive.index.trash(disk.id))


def _connected(archive: Archive, disk_id: str) -> Disk:
    for disk in archive.disks:
        if disk.id == disk_id:
            return disk
    label = next((d.label for d in archive.index.disks() if d.id == disk_id), disk_id)
    raise FileNotFoundError(f"disk {label} is not connected")


def _remove_empty_parents(folder: Path, stop: Path) -> None:
    """Remove ``folder`` and its parents while they are empty, up to ``stop`` (excluded)."""
    stop = stop.resolve()
    folder = folder.resolve()
    while folder != stop and stop in folder.parents:
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent
