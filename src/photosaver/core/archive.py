"""Archive-level operations on disks and their indexes."""

from __future__ import annotations

from pathlib import Path

from .disk import Disk, init_disk, open_disk  # noqa: F401 (re-exported)
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


class ArchiveError(Exception):
    """Base class for archive errors."""


class MixedArchives(ArchiveError):
    """The disks belong to different archives."""


class Archive:
    """The connected disks of one archive, with its working index.

    The working index is the one with the highest revision: the others may be behind
    after an interruption. Operations write to it and call :meth:`sync_indexes` to copy it
    to every other connected disk. With a single disk connected the archive is read-only
    in practice: operations that write require :attr:`complete`.
    """

    def __init__(self, disks: list[Disk], indexes: list[Index], primary: int) -> None:
        self.disks = disks
        self._indexes = indexes
        self.primary = disks[primary]
        self.index = indexes[primary]
        self.stale = [
            disk
            for disk, index in zip(disks, indexes, strict=True)
            if index.revision < self.index.revision
        ]
        for i, index in enumerate(indexes):
            if i != primary:
                index.close()

    @classmethod
    def open(cls, disks: list[Disk]) -> Archive:
        if not disks:
            raise ValueError("no disk")
        archive_ids = {disk.info.archive_id for disk in disks}
        if len(archive_ids) > 1:
            raise MixedArchives("the disks belong to different archives")
        disks = sorted(disks, key=lambda d: d.label)
        indexes: list[Index] = []
        try:
            for disk in disks:
                indexes.append(open_index(disk))
        except BaseException:
            for index in indexes:
                index.close()
            raise
        revisions = [index.revision for index in indexes]
        return cls(disks, indexes, revisions.index(max(revisions)))

    def close(self) -> None:
        self.index.close()

    def __enter__(self) -> Archive:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def missing(self) -> list[str]:
        """Labels of the archive's disks that are not connected."""
        connected = {disk.id for disk in self.disks}
        return [d.label for d in self.index.disks() if d.id not in connected]

    @property
    def complete(self) -> bool:
        """All the archive's disks are connected: writing operations are allowed."""
        return not self.missing

    def path_on(self, disk: Disk, path: str) -> Path:
        """Where an archive path (``FOTO 2026/a.jpg``) lives on a disk."""
        return disk.archive.joinpath(*path.split("/"))

    def sync_indexes(self) -> None:
        """Copy the working index to every other connected disk."""
        for disk in self.disks:
            if disk is not self.primary:
                self.index.copy_to(index_path(disk))
        self.stale = []
