"""Archive-level operations on disks and their indexes."""

from __future__ import annotations

from pathlib import Path

from .disk import Disk, init_disk
from .index import INDEX_FILE, Index


def index_path(disk: Disk) -> Path:
    return disk.data_dir / INDEX_FILE


def open_index(disk: Disk) -> Index:
    return Index.open(index_path(disk))


def create_archive(root: Path, *, label: str, archive_dir: str) -> Disk:
    """Initialize ``root`` as the first disk of a new, empty archive."""
    disk = init_disk(root, label=label, archive_dir=archive_dir)
    index = Index.create(index_path(disk), archive_id=disk.info.archive_id)
    with index, index.transaction():
        index.add_disk(disk.id, label)
        index.log("archive_created", disk_id=disk.id, label=label, archive_dir=archive_dir)
    return disk


def join_archive(member: Disk, root: Path, *, label: str) -> Disk:
    """Initialize ``root`` as a new disk of ``member``'s archive.

    The new disk is registered in ``member``'s index, which is then copied to it, so the
    two indexes are identical. Copying the files is a separate step.
    """
    disk = init_disk(
        root, label=label, archive_dir=member.info.archive_dir, archive_id=member.info.archive_id
    )
    with open_index(member) as index:
        with index.transaction():
            index.add_disk(disk.id, label)
            index.log("disk_added", disk_id=disk.id, label=label)
        index.copy_to(index_path(disk))
    return disk
