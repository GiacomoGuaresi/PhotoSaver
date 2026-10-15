"""Uploading folders into the archive.

Two phases, so the interface can show a preview before anything is written:

1. :func:`analyze` reads the folders: finds photos and videos, hashes them, reads their
   dates. Slow (it reads every byte), done once.
2. :func:`resolve` decides, for the chosen destinations, what happens to each file: copy,
   skip because it is already there, warn about duplicates, rename on name conflicts.
   Fast, run again whenever a destination or a choice changes.

A file in the archive is never overwritten by an upload.
"""

from __future__ import annotations

import contextlib
import os
import re
import time
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import dates, hashing, safecopy, scanner
from .archive import Archive, ArchiveError
from .index import OK, FileRecord, now

# Item status
NEW = "new"  # will be copied
SAME = "same"  # already in the archive at that path, same content: nothing to do
DUPLICATE = "duplicate"  # same content already in the archive (or in this upload) elsewhere
CONFLICT = "conflict"  # another file with the same name is at the destination

# Item actions
COPY = "copy"
SKIP = "skip"
RENAME = "rename"  # copy with a free name: name_2.jpg

_YEAR = re.compile(r"(?<!\d)(19[89]\d|20\d\d|2100)(?!\d)")


@dataclass
class Item:
    source: Path
    relative: str  # inside the uploaded folder, with '/'
    size: int
    mtime_ns: int
    hash: str
    kind: str
    taken: datetime
    taken_from: str  # dates.EXIF, dates.NAME or dates.MTIME
    status: str = NEW
    target: str = ""  # archive path the file goes to (after renaming)
    duplicates: list[str] = field(default_factory=list)  # archive paths with the same content
    action: str = COPY
    choice: str | None = None  # the user's choice, kept across resolves when still valid

    @property
    def copied(self) -> bool:
        return self.action in (COPY, RENAME)


@dataclass
class Folder:
    source: Path
    items: list[Item]
    ignored: list[str]
    skipped: list[str]
    errors: list[tuple[str, str]]
    destination: str = ""  # archive folder, '' for the archive root

    @property
    def years(self) -> Counter[int]:
        return Counter(item.taken.year for item in self.items)


@dataclass
class Plan:
    folders: list[Folder]

    @property
    def items(self) -> list[Item]:
        return [item for folder in self.folders for item in folder.items]

    def to_copy(self) -> list[Item]:
        return [item for item in self.items if item.copied]

    def count(self, status: str) -> int:
        return sum(item.status == status for item in self.items)

    @property
    def copy_size(self) -> int:
        return sum(item.size for item in self.to_copy())


def analyze(
    folders: list[Path],
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Plan:
    """Scan, hash and date every photo and video in ``folders``.

    ``on_progress(done, total)`` reports bytes hashed out of the total.
    """
    scans = [(folder, scanner.scan(folder)) for folder in folders]
    total = sum(result.size for _, result in scans)
    done = 0

    def advance(read: int) -> None:
        nonlocal done
        done += read
        if on_progress:
            on_progress(done, total)

    plan = Plan([])
    for folder, result in scans:
        items = []
        for entry in result.media:
            path = folder.joinpath(*entry.path.split("/"))
            digest = hashing.hash_file(path, on_progress=advance, should_stop=should_stop)
            when, source = dates.taken(path, entry.mtime_ns)
            items.append(
                Item(path, entry.path, entry.size, entry.mtime_ns, digest, entry.kind, when, source)
            )
        plan.folders.append(Folder(folder, items, result.ignored, result.skipped, result.errors))
    return plan


def top_level_folders(archive: Archive) -> list[str]:
    """Folders at the root of the archive: from the index and from the disks."""
    names = {r.path.split("/")[0] for r in archive.index.files() if "/" in r.path}
    for disk in archive.disks:
        if disk.archive.is_dir():
            names.update(
                p.name
                for p in disk.archive.iterdir()
                if p.is_dir() and not scanner.is_hidden(p.name)
            )
    return sorted(names)


def propose_destination(folder: Folder, top_level: list[str]) -> str:
    """Where to put an uploaded folder, from the dates of its photos.

    - A whole archive tree (every file inside a year folder) goes to the archive root,
      keeping its structure.
    - An event folder goes into the year folder of most of its photos: an existing one
      (``FOTO 2026``), or a new one named like the others, or just the year.
    """
    name = folder.source.name
    if not folder.items:
        return name
    firsts = [item.relative.split("/") for item in folder.items]
    if all(len(parts) > 1 and _YEAR.search(parts[0]) for parts in firsts):
        return ""

    year = folder.years.most_common(1)[0][0]
    return f"{_year_folder(year, top_level)}/{name}"


def _year_folder(year: int, top_level: list[str]) -> str:
    matching = [n for n in top_level if any(int(y) == year for y in _YEAR.findall(n))]
    if matching:
        return min(matching, key=len)
    patterns = Counter(
        (n[: m.start()], n[m.end() :]) for n in top_level if (m := _YEAR.search(n)) is not None
    )
    if patterns:
        (prefix, suffix), _ = patterns.most_common(1)[0]
        return f"{prefix}{year}{suffix}"
    return str(year)


def resolve(plan: Plan, archive: Archive) -> None:
    """Decide status, target and action of every item, for the current destinations."""
    indexed = {_key(record.path): record for record in archive.index.files()}
    hashes: dict[str, list[str]] = {}
    for record in indexed.values():
        hashes.setdefault(record.hash, []).append(record.path)
    planned: dict[str, Item] = {}  # targets taken by this upload
    planned_hashes: dict[str, Item] = {}

    for folder in plan.folders:
        for item in folder.items:
            target = _join(folder.destination, item.relative)
            item.target, item.duplicates = target, []
            key = _key(target)
            existing = indexed.get(key)
            if existing is not None:
                item.status = SAME if existing.hash == item.hash else CONFLICT
            elif key in planned:
                item.status = DUPLICATE if planned[key].hash == item.hash else CONFLICT
            elif (on_disk := _hash_on_disks(archive, target)) is not None:
                # Put there outside the app: the same file is adopted, a different one kept
                item.status = NEW if on_disk == item.hash else CONFLICT
            else:
                item.status = NEW

            if item.status == NEW:
                others = [p for p in hashes.get(item.hash, []) if _key(p) != key]
                if item.hash in planned_hashes:
                    others.append(planned_hashes[item.hash].target)
                if others:
                    item.status, item.duplicates = DUPLICATE, others

            item.action = _action(item)
            if item.action == RENAME:
                item.target = _free_name(target, indexed, planned, archive)
            if item.copied:
                planned[_key(item.target)] = item
                planned_hashes.setdefault(item.hash, item)


def _action(item: Item) -> str:
    allowed = {
        NEW: (COPY,),
        SAME: (SKIP,),
        DUPLICATE: (SKIP, COPY),  # skipped unless asked: the photo is already safe
        CONFLICT: (RENAME, SKIP),  # renamed unless asked: nothing is lost
    }[item.status]
    return item.choice if item.choice in allowed else allowed[0]


def _free_name(target: str, indexed: dict, planned: dict, archive: Archive) -> str:
    path = PurePosixPath(target)
    for n in range(2, 10_000):
        candidate = str(path.with_name(f"{path.stem}_{n}{path.suffix}"))
        key = _key(candidate)
        if (
            key not in indexed
            and key not in planned
            and not any(archive.path_on(d, candidate).exists() for d in archive.disks)
        ):
            return candidate
    raise RuntimeError(f"no free name for {target}")


def _hash_on_disks(archive: Archive, target: str) -> str | None:
    for disk in archive.disks:
        path = archive.path_on(disk, target)
        if path.is_file():
            return hashing.hash_file(path)
    return None


def _join(destination: str, relative: str) -> str:
    return f"{destination.strip('/')}/{relative}" if destination.strip("/") else relative


def _key(path: str) -> str:
    """Comparison key for archive paths: exFAT ignores letter case."""
    return path.casefold()


# Applying the plan

SYNC_EVERY = 30.0  # seconds between copies of the index to the other disks


@dataclass
class Result:
    copied: list[Item] = field(default_factory=list)
    failed: list[tuple[Item, str]] = field(default_factory=list)


def apply(
    plan: Plan,
    archive: Archive,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Result:
    """Copy the plan's files to every disk, verified, and record them in the index.

    Can be interrupted at any point: analyzing and resolving again, then applying, resumes
    the upload (files already copied are found in the index, or adopted from the disks).
    Files that fail (changed since the analysis, unreadable…) are reported and skipped;
    an error on a disk stops the upload.
    """
    if not archive.complete:
        raise ArchiveError(f"connect all the disks first: {', '.join(archive.missing)}")
    items = plan.to_copy()
    total = sum(item.size for item in items)
    done = 0
    result = Result()
    operation = uuid.uuid4().hex[:12]
    last_sync = time.monotonic()

    def advance(read: int) -> None:
        nonlocal done
        done += read
        if on_progress:
            on_progress(done, total)

    try:
        for item in items:
            before = done
            try:
                _copy_item(item, archive, advance, should_stop)
            except (safecopy.SourceChanged, safecopy.VerifyFailed, FileExistsError) as error:
                result.failed.append((item, str(error)))
            except OSError as error:
                if not item.source.exists() or error.filename == str(item.source):
                    result.failed.append((item, error.strerror or str(error)))
                else:
                    raise
            else:
                with archive.index.transaction():
                    archive.index.put_file(
                        FileRecord(item.target, item.size, item.mtime_ns, item.hash)
                    )
                    for disk in archive.disks:
                        archive.index.set_copy(item.target, disk.id, OK, verified_at=now())
                    archive.index.log(
                        "upload", path=item.target, op=operation, source=str(item.source)
                    )
                result.copied.append(item)
            # Failed or partial items still count, so the progress always reaches the end
            advance(item.size - (done - before))
            if time.monotonic() - last_sync > SYNC_EVERY:
                archive.sync_indexes()
                last_sync = time.monotonic()
    finally:
        with archive.index.transaction():
            archive.index.log(
                "upload_done",
                op=operation,
                folders=[str(f.source) for f in plan.folders],
                copied=len(result.copied),
                failed=len(result.failed),
                size=sum(item.size for item in result.copied),
                complete=len(result.copied) + len(result.failed) == len(items),
            )
        archive.sync_indexes()
    return result


def _copy_item(item: Item, archive: Archive, advance, should_stop) -> None:
    pending = []
    for disk in archive.disks:
        destination = archive.path_on(disk, item.target)
        if not destination.exists():
            pending.append(destination)
        elif hashing.hash_file(destination, should_stop=should_stop) == item.hash:
            # Already there (an interrupted upload, or copied by hand): adopt it
            os.utime(destination, ns=(destination.stat().st_atime_ns, item.mtime_ns))
        else:
            raise FileExistsError(f"{destination} exists with a different content")
    if pending:
        safecopy.safe_copy(
            item.source,
            pending,
            expected_hash=item.hash,
            on_progress=advance,
            should_stop=should_stop,
        )


# Deleting the originals


@dataclass
class Cleanup:
    deleted: list[Path] = field(default_factory=list)
    kept: list[tuple[Path, str]] = field(default_factory=list)


def delete_sources(plan: Plan, archive: Archive) -> Cleanup:
    """Delete the uploaded originals whose content is safe on every disk of the archive.

    A file is deleted only if the index has a file with its hash, recorded as good on
    all the archive's disks, and it has not changed since the analysis. Everything else
    (files skipped for a name conflict, failed copies, ignored files) stays, and so do the
    folders that are not empty.
    """
    disk_ids = {d.id for d in archive.index.disks()}
    cleanup = Cleanup()
    for item in plan.items:
        reason = _unsafe_to_delete(item, archive, disk_ids)
        if reason:
            cleanup.kept.append((item.source, reason))
            continue
        try:
            item.source.unlink()
        except OSError as error:
            cleanup.kept.append((item.source, error.strerror or str(error)))
        else:
            cleanup.deleted.append(item.source)
    for folder in plan.folders:
        _remove_empty_folders(folder.source)
    return cleanup


def _unsafe_to_delete(item: Item, archive: Archive, disk_ids: set[str]) -> str | None:
    try:
        stat = item.source.stat()
    except OSError:
        return "not found"
    if (stat.st_size, stat.st_mtime_ns) != (item.size, item.mtime_ns):
        return "changed since the upload"
    for record in archive.index.files_with_hash(item.hash):
        copies = archive.index.copies(record.path)
        if all(copies.get(d) is not None and copies[d].state == OK for d in disk_ids):
            return None
    return "not in the archive"


def _remove_empty_folders(root: Path) -> None:
    for folder, _, _ in sorted(os.walk(root), key=lambda w: -len(w[0])):
        with contextlib.suppress(OSError):
            os.rmdir(folder)  # fails, as wanted, when not empty
