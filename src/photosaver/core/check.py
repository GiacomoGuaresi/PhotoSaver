"""Checking the disks against the index.

- **Quick check**: lists every disk and compares size and modification date with the
  index; only files that look different are read and hashed. Takes seconds.
- **Full check**: reads every file on every disk and compares its hash with the index,
  so it finds silent corruption (bit rot) too. Takes hours on big archives, can be
  interrupted and resumed.

Both produce a list of :class:`Difference`, one per file and disk. Checks never change
files; deciding and fixing is up to the resolution actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from . import hashing, scanner
from .archive import Archive
from .disk import Disk
from .index import FileRecord

# Difference kinds, per file and disk
MISSING = "missing"  # in the index, not on the disk
UNTRACKED = "untracked"  # on the disk, not in the index: added outside the app
CORRUPT = "corrupt"  # different content, same date: damaged without anyone touching it
MODIFIED = "modified"  # different content and date: edited outside the app

# exFAT keeps dates to 10 ms, FAT to 2 s: closer dates are the same date
MTIME_TOLERANCE_NS = 2_000_000_000


@dataclass(frozen=True)
class Difference:
    kind: str
    disk_id: str
    path: str
    size: int | None = None  # on the disk, when the file is there
    mtime_ns: int | None = None
    hash: str | None = None  # of the file on the disk, when read


@dataclass
class Report:
    differences: list[Difference] = field(default_factory=list)
    disks: list[str] = field(default_factory=list)  # ids of the checked disks
    files: int = 0  # files in the index
    errors: list[tuple[str, str, str]] = field(default_factory=list)  # (disk id, path, reason)

    def of_kind(self, kind: str) -> list[Difference]:
        return [d for d in self.differences if d.kind == kind]

    @property
    def clean(self) -> bool:
        return not self.differences and not self.errors


def same_date(a: int, b: int) -> bool:
    return abs(a - b) <= MTIME_TOLERANCE_NS


def quick_check(
    archive: Archive,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Report:
    """Compare every connected disk with the index by size and date.

    Files that differ, and files added outside the app, are hashed: the first to tell
    corruption from editing, the second to recognize moves. ``on_progress(done, total)``
    counts disks.
    """
    records = {record.path: record for record in archive.index.files()}
    report = Report(disks=[d.id for d in archive.disks], files=len(records))
    for n, disk in enumerate(archive.disks):
        _check_disk(archive, disk, records, report, should_stop)
        if on_progress:
            on_progress(n + 1, len(archive.disks))
    return report


def _check_disk(
    archive: Archive,
    disk: Disk,
    records: dict[str, FileRecord],
    report: Report,
    should_stop: Callable[[], bool] | None,
) -> None:
    scan = scanner.scan(disk.archive) if disk.archive.is_dir() else scanner.ScanResult()
    if not disk.archive.is_dir():
        report.errors.append((disk.id, "", "archive folder not found"))
    for path, reason in scan.errors:
        report.errors.append((disk.id, path, reason))
    unreadable = {path for path, _ in scan.errors}

    found = {entry.path: entry for entry in scan.media}
    for path, record in records.items():
        entry = found.get(path)
        if entry is None:
            if not any(path == u or path.startswith(u + "/") for u in unreadable):
                report.differences.append(Difference(MISSING, disk.id, path))
            continue
        if entry.size == record.size and same_date(entry.mtime_ns, record.mtime_ns):
            continue
        digest = _hash(archive, disk, path, report, should_stop)
        if digest is None or digest == record.hash:
            continue  # only the date changed: the photo is fine
        kind = CORRUPT if same_date(entry.mtime_ns, record.mtime_ns) else MODIFIED
        report.differences.append(
            Difference(kind, disk.id, path, entry.size, entry.mtime_ns, digest)
        )

    for path, entry in found.items():
        if path not in records:
            digest = _hash(archive, disk, path, report, should_stop)
            report.differences.append(
                Difference(UNTRACKED, disk.id, path, entry.size, entry.mtime_ns, digest)
            )


def _hash(archive, disk, path, report, should_stop) -> str | None:
    try:
        return hashing.hash_file(archive.path_on(disk, path), should_stop=should_stop)
    except OSError as error:
        report.errors.append((disk.id, path, error.strerror or str(error)))
        return None
