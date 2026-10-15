"""Checking the disks against the index.

- **Quick check**: lists every disk and compares size and modification date with the
  index; only files that look different are read and hashed. Takes seconds.
- **Full check**: reads every file on every disk (one thread per disk, in parallel) and
  compares its hash with the index, so it also finds silent corruption (bit rot). Takes
  hours on big archives; it records its progress in the index and resumes after an
  interruption.

Both produce a list of :class:`Difference`, one per file and disk. Checks never change
the files; deciding and fixing is up to the resolution actions.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import hashing, scanner
from .archive import Archive
from .disk import Disk
from .index import CORRUPT as STATE_CORRUPT
from .index import MISSING as STATE_MISSING
from .index import MODIFIED as STATE_MODIFIED
from .index import OK, FileRecord, now

# Difference kinds, per file and disk
MISSING = "missing"  # in the index, not on the disk
UNTRACKED = "untracked"  # on the disk, not in the index: added outside the app
CORRUPT = "corrupt"  # different content, same date: damaged without anyone touching it
MODIFIED = "modified"  # different content and date: edited outside the app
MOVED = "moved"  # missing at ``path``, found at ``target`` with the same content

# exFAT keeps dates to 10 ms, FAT to 2 s: closer dates are the same date
MTIME_TOLERANCE_NS = 2_000_000_000

FULL_CHECK_RUN = "full_check_run"  # meta key of a full check in progress
LAST_FULL_CHECK = "last_full_check:"  # meta key prefix, + disk id
WRITE_EVERY = 2.0  # seconds between index writes during a full check


@dataclass(frozen=True)
class Difference:
    kind: str
    disk_id: str
    path: str
    size: int | None = None  # on the disk, when the file is there
    mtime_ns: int | None = None
    hash: str | None = None  # of the file on the disk, when read
    target: str | None = None  # new path of a moved file


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


# What a disk scan emits, to the report directly (quick) or through a queue (full)
_DIFF, _OK, _ERROR, _BYTES = "diff", "ok", "error", "bytes"
Emit = Callable[[str, object], None]


def _scan_disk(
    archive: Archive,
    disk: Disk,
    records: dict[str, FileRecord],
    emit: Emit,
    should_stop: Callable[[], bool] | None,
    *,
    full: bool,
    skip: frozenset[str] = frozenset(),
) -> None:
    """Compare one disk with the index. ``full`` reads every file; ``skip`` lists paths
    already verified (by an interrupted full check)."""
    if disk.archive.is_dir():
        scan = scanner.scan(disk.archive)
    else:
        scan = scanner.ScanResult()
        emit(_ERROR, (disk.id, "", "archive folder not found"))
    for path, reason in scan.errors:
        emit(_ERROR, (disk.id, path, reason))
    unreadable = [path for path, _ in scan.errors]

    def read(path: str) -> str | None:
        try:
            return hashing.hash_file(
                archive.path_on(disk, path),
                should_stop=should_stop,
                on_progress=lambda n: emit(_BYTES, n),
            )
        except OSError as error:
            emit(_ERROR, (disk.id, path, error.strerror or str(error)))
            return None

    found = {entry.path: entry for entry in scan.media}
    for path, record in records.items():
        if path in skip:
            continue
        entry = found.get(path)
        if entry is None:
            if not any(path == u or path.startswith(u + "/") for u in unreadable):
                emit(_DIFF, Difference(MISSING, disk.id, path))
            continue
        looks_same = entry.size == record.size and same_date(entry.mtime_ns, record.mtime_ns)
        if looks_same and not full:
            continue
        digest = read(path)
        if digest is None:
            continue
        if digest == record.hash:
            emit(_OK, (disk.id, path))  # only the date may have changed: the photo is fine
            continue
        kind = CORRUPT if same_date(entry.mtime_ns, record.mtime_ns) else MODIFIED
        emit(_DIFF, Difference(kind, disk.id, path, entry.size, entry.mtime_ns, digest))

    for path, entry in found.items():
        if path not in records:
            emit(
                _DIFF, Difference(UNTRACKED, disk.id, path, entry.size, entry.mtime_ns, read(path))
            )


def quick_check(
    archive: Archive,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Report:
    """Compare every connected disk with the index by size and date.

    Files that differ, and files added outside the app, are hashed: the first to tell
    corruption from editing, the second to recognize moves. ``on_progress(done, total)``
    counts disks. Read-only: the index is not changed.
    """
    records = {record.path: record for record in archive.index.files()}
    report = Report(disks=[d.id for d in archive.disks], files=len(records))

    def emit(kind: str, value) -> None:
        if kind == _DIFF:
            report.differences.append(value)
        elif kind == _ERROR:
            report.errors.append(value)

    for n, disk in enumerate(archive.disks):
        _scan_disk(archive, disk, records, emit, should_stop, full=False)
        if on_progress:
            on_progress(n + 1, len(archive.disks))
    detect_moves(report, records)
    return report


def full_check(
    archive: Archive,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Report:
    """Read every file on every connected disk and compare it with the index.

    The state of each copy (ok, missing, corrupt, modified) and the time it was verified
    are recorded in the index as the check goes. If interrupted (``should_stop``), it
    raises :class:`hashing.Cancelled`; the next full check resumes, skipping the files
    already verified. ``on_progress(done, total)`` counts bytes.
    """
    index = archive.index
    records = {record.path: record for record in index.files()}
    started = _start_run(archive)
    report = Report(disks=[d.id for d in archive.disks], files=len(records))

    skips: dict[str, frozenset[str]] = {}
    for disk in archive.disks:
        copies = index.copies_on(disk.id)
        done = {p for p, c in copies.items() if c.verified_at and c.verified_at >= started}
        skips[disk.id] = frozenset(done & records.keys())
        for path in skips[disk.id]:  # problems found before the interruption
            state = copies[path].state
            if state in _KIND_OF_STATE:
                report.differences.append(Difference(_KIND_OF_STATE[state], disk.id, path))

    total = sum(
        records[path].size for disk in archive.disks for path in records.keys() - skips[disk.id]
    )
    events: queue.Queue = queue.Queue()
    stop = threading.Event()
    cancelled = threading.Event()

    def worker(disk: Disk) -> None:
        try:
            _scan_disk(
                archive,
                disk,
                records,
                lambda kind, value: events.put((kind, value)),
                stop.is_set,
                full=True,
                skip=skips[disk.id],
            )
        except hashing.Cancelled:
            cancelled.set()
        except BaseException as error:  # reported by the main thread
            events.put(("crash", error))
        finally:
            events.put(("done", disk.id))

    threads = [threading.Thread(target=worker, args=(d,), daemon=True) for d in archive.disks]
    for thread in threads:
        thread.start()

    pending: list[tuple[str, str, str]] = []  # (path, disk id, state) to write
    running, done_bytes, last_write, crash = len(threads), 0, time.monotonic(), None
    while running:
        if should_stop and should_stop():
            stop.set()
        try:
            kind, value = events.get(timeout=0.1)
        except queue.Empty:
            continue
        if kind == "done":
            running -= 1
        elif kind == "crash":
            crash = value
            stop.set()
        elif kind == _BYTES:
            done_bytes += value
            if on_progress:  # files added outside the app are read too: not in the total
                on_progress(min(done_bytes, total), total)
        elif kind == _ERROR:
            report.errors.append(value)
        elif kind == _OK:
            pending.append((value[1], value[0], OK))
        elif kind == _DIFF:
            report.differences.append(value)
            if value.kind in _STATE_OF_KIND:
                pending.append((value.path, value.disk_id, _STATE_OF_KIND[value.kind]))
        if time.monotonic() - last_write > WRITE_EVERY:
            _write_states(archive, pending)
            last_write = time.monotonic()
    for thread in threads:
        thread.join()

    _write_states(archive, pending)
    if crash is not None:
        archive.sync_indexes()
        raise crash
    if cancelled.is_set():  # a stop asked after the workers finished changes nothing
        archive.sync_indexes()
        raise hashing.Cancelled("full check interrupted")
    _finish_run(archive, report)
    detect_moves(report, records)
    return report


def detect_moves(report: Report, records: dict[str, FileRecord]) -> None:
    """Pair, on each disk, a missing file with a new file of the same content: it was moved
    or renamed. Among several candidates, the one with the same file name wins."""
    by_disk: dict[str, list[Difference]] = {}
    for diff in report.differences:
        if diff.kind == UNTRACKED and diff.hash:
            by_disk.setdefault(diff.disk_id, []).append(diff)

    moved: list[Difference] = []
    paired: set[int] = set()
    for diff in report.differences:
        if diff.kind != MISSING or diff.path not in records:
            continue
        expected = records[diff.path].hash
        name = diff.path.rsplit("/", 1)[-1]
        candidates = [
            u for u in by_disk.get(diff.disk_id, []) if u.hash == expected and id(u) not in paired
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda u: (u.path.rsplit("/", 1)[-1] != name, u.path))
        paired.update((id(best), id(diff)))
        moved.append(
            Difference(
                MOVED, diff.disk_id, diff.path, best.size, best.mtime_ns, best.hash, best.path
            )
        )
    report.differences = [d for d in report.differences if id(d) not in paired] + moved


_STATE_OF_KIND = {MISSING: STATE_MISSING, CORRUPT: STATE_CORRUPT, MODIFIED: STATE_MODIFIED}
_KIND_OF_STATE = {state: kind for kind, state in _STATE_OF_KIND.items()}


def _start_run(archive: Archive) -> str:
    """Start a full check, or resume the interrupted one on the same disks."""
    disks = sorted(d.id for d in archive.disks)
    raw = archive.index.get_meta(FULL_CHECK_RUN)
    if raw:
        run = json.loads(raw)
        if run.get("disks") == disks:
            return run["started"]
    started = now()
    with archive.index.transaction():
        archive.index.set_meta(FULL_CHECK_RUN, json.dumps({"started": started, "disks": disks}))
        archive.index.log("full_check_started", disks=disks)
    return started


def _write_states(archive: Archive, pending: list[tuple[str, str, str]]) -> None:
    if not pending:
        return
    verified = now()
    with archive.index.transaction():
        for path, disk_id, state in pending:
            archive.index.set_copy(path, disk_id, state, verified_at=verified)
    pending.clear()


def _finish_run(archive: Archive, report: Report) -> None:
    finished = now()
    with archive.index.transaction():
        archive.index.delete_meta(FULL_CHECK_RUN)
        for disk in archive.disks:
            archive.index.set_meta(LAST_FULL_CHECK + disk.id, finished)
        archive.index.log(
            "full_check_done",
            disks=report.disks,
            files=report.files,
            differences=len(report.differences),
            errors=len(report.errors),
        )
    archive.sync_indexes()


def last_full_check(archive: Archive, disk: Disk) -> str | None:
    return archive.index.get_meta(LAST_FULL_CHECK + disk.id)
