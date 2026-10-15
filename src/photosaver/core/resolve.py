"""From check differences to fixes.

:func:`build_issues` groups the differences of a check by file: one :class:`Issue` per
file, with the possible actions and, when the right one is obvious, a proposed action
(the interface shows it already selected). Nothing changes until :func:`apply` runs the
chosen actions. Files that are replaced or deleted go to the app's trash.

Obvious cases (proposed): repair a damaged copy from a good one, copy a file to a disk
that never had it, repeat on the other disks a move made on one, add to the archive a
file added by hand. Ambiguous cases (nothing proposed): a file missing from a disk that
had it (deleted on purpose, or lost?), a file edited outside the app.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from . import hashing, safecopy, trash
from .archive import Archive, ArchiveError
from .check import CORRUPT, MISSING, MODIFIED, MOVED, Difference, Report, mark_known
from .disk import Disk
from .index import OK, FileRecord, now

# Issue kinds
I_CORRUPT = "corrupt"  # damaged on some disks
I_MISSING = "missing"  # missing on some disks, good on others
I_LOST = "lost"  # missing on every disk
I_MODIFIED = "modified"  # edited outside the app
I_MOVED = "moved"  # moved or renamed outside the app
I_UNTRACKED = "untracked"  # added outside the app
I_COMPLEX = "complex"  # different problems on different disks

# Actions
REPAIR = "repair"  # replace bad copies (damaged, missing, edited) with a good one
COPY = "copy"  # copy to the disks where it is missing
DELETE_ALL = "delete_all"  # delete it from every disk (to the trash) and from the archive
FORGET = "forget"  # remove from the archive a file no disk has
REVERT = "revert"  # put back the original over edited copies
PROPAGATE = "propagate"  # keep the version of ``disk_id`` everywhere
ACCEPT = "accept"  # record in the archive what every disk has (edit, move, new file)
REPEAT_MOVE = "repeat_move"  # make the same move on the other disks
UNDO_MOVE = "undo_move"  # move it back where the archive expects it
ADD = "add"  # add a new file to the archive, copying it to the disks without it
DELETE = "delete"  # delete a new file (to the trash)
KNOWN = "known"  # mark as known: not reported anymore


@dataclass(frozen=True)
class Option:
    action: str
    disk_id: str | None = None  # whose version, for PROPAGATE


@dataclass
class Issue:
    kind: str
    path: str
    diffs: list[Difference]
    options: list[Option]
    proposed: Option | None = None
    choice: Option | None = None

    @property
    def chosen(self) -> Option | None:
        return self.choice or self.proposed

    @property
    def target(self) -> str | None:
        """New path, for moves."""
        targets = {d.target for d in self.diffs if d.target}
        return targets.pop() if len(targets) == 1 else None


@dataclass
class Outcome:
    done: list[Issue] = field(default_factory=list)
    failed: list[tuple[Issue, str]] = field(default_factory=list)


def build_issues(report: Report, archive: Archive) -> list[Issue]:
    by_path: dict[str, list[Difference]] = {}
    for diff in report.differences:
        by_path.setdefault(diff.path, []).append(diff)
    issues = []
    for path, diffs in sorted(by_path.items()):
        record = archive.index.get_file(path)
        if record is None:
            issues.append(_untracked_issue(path, diffs, archive))
        else:
            issues.append(_indexed_issue(path, diffs, archive))
    return issues


def _indexed_issue(path: str, diffs: list[Difference], archive: Archive) -> Issue:
    bad = {d.disk_id for d in diffs}
    good = [disk for disk in archive.disks if disk.id not in bad]
    kinds = {d.kind for d in diffs}
    known = Option(KNOWN)

    if kinds == {CORRUPT}:
        if good:
            return Issue(I_CORRUPT, path, diffs, [Option(REPAIR), known], Option(REPAIR))
        return Issue(I_CORRUPT, path, diffs, [known])

    if kinds == {MISSING}:
        if not good:
            return Issue(I_LOST, path, diffs, [Option(FORGET), known])
        copies = archive.index.copies(path)
        never_there = all(d.disk_id not in copies for d in diffs)
        options = [Option(COPY), Option(DELETE_ALL), known]
        return Issue(I_MISSING, path, diffs, options, Option(COPY) if never_there else None)

    if kinds == {MODIFIED}:
        versions = [Option(PROPAGATE, d.disk_id) for d in diffs]
        if good:
            return Issue(I_MODIFIED, path, diffs, [Option(REVERT), *versions, known])
        if len({d.hash for d in diffs}) == 1:
            return Issue(I_MODIFIED, path, diffs, [Option(ACCEPT), known], Option(ACCEPT))
        return Issue(I_MODIFIED, path, diffs, [*versions, known])

    if kinds == {MOVED}:
        same_target = len({d.target for d in diffs}) == 1
        if not good:
            if same_target:
                return Issue(
                    I_MOVED, path, diffs, [Option(ACCEPT), Option(UNDO_MOVE), known], Option(ACCEPT)
                )
            return Issue(I_MOVED, path, diffs, [Option(UNDO_MOVE), known])
        if same_target and _free_on(archive, good, diffs[0].target):
            options = [Option(REPEAT_MOVE), Option(UNDO_MOVE), known]
            return Issue(I_MOVED, path, diffs, options, Option(REPEAT_MOVE))
        return Issue(I_MOVED, path, diffs, [Option(UNDO_MOVE), known])

    if good:
        return Issue(I_COMPLEX, path, diffs, [Option(REPAIR), known])
    return Issue(I_COMPLEX, path, diffs, [Option(FORGET), known])


def _untracked_issue(path: str, diffs: list[Difference], archive: Archive) -> Issue:
    known = Option(KNOWN)
    hashes = {d.hash for d in diffs}
    if None in hashes:
        return Issue(I_UNTRACKED, path, diffs, [known])
    if len(hashes) > 1:
        return Issue(I_UNTRACKED, path, diffs, [Option(DELETE), known])
    options = [Option(ADD), Option(DELETE), known]
    return Issue(I_UNTRACKED, path, diffs, options, Option(ADD))


def _free_on(archive: Archive, disks: list[Disk], path: str | None) -> bool:
    return path is not None and not any(archive.path_on(d, path).exists() for d in disks)


# Applying


def apply(
    issues: list[Issue],
    archive: Archive,
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Outcome:
    """Run the chosen action of every issue (issues without one are left alone).

    ``on_progress(done, total)`` counts issues. A failing issue is reported and the others
    go on; an interruption (``should_stop``) raises :class:`hashing.Cancelled` after the
    current issue.
    """
    if not archive.complete:
        raise ArchiveError(f"connect all the disks first: {', '.join(archive.missing)}")
    todo = [issue for issue in issues if issue.chosen is not None]
    outcome = Outcome()
    try:
        for n, issue in enumerate(todo):
            if should_stop and should_stop():
                raise hashing.Cancelled("resolution interrupted")
            entry = archive.index.begin(JOURNAL_OPERATION, _to_journal(issue))
            _run(archive, issue, outcome)
            with archive.index.transaction():
                archive.index.end(entry)
            if on_progress:
                on_progress(n + 1, len(todo))
    finally:
        archive.sync_indexes()
    return outcome


def pending(archive: Archive) -> list[Issue]:
    """Actions interrupted before they finished (the app was closed, a disk unplugged…)."""
    return [
        _from_journal(entry.params)
        for entry in archive.index.journal()
        if entry.operation == JOURNAL_OPERATION
    ]


def recover(archive: Archive) -> Outcome:
    """Finish the interrupted actions. Every action can be run again safely: what was
    already done is recognized and skipped."""
    if not archive.complete:
        raise ArchiveError(f"connect all the disks first: {', '.join(archive.missing)}")
    outcome = Outcome()
    try:
        for entry in archive.index.journal():
            if entry.operation != JOURNAL_OPERATION:
                continue
            _run(archive, _from_journal(entry.params), outcome)
            with archive.index.transaction():
                archive.index.end(entry.id)
                archive.index.log("recovered", path=entry.params["issue"]["path"])
    finally:
        archive.sync_indexes()
    return outcome


JOURNAL_OPERATION = "resolve"


def _run(archive: Archive, issue: Issue, outcome: Outcome) -> None:
    try:
        _ACTIONS[issue.chosen.action](archive, issue, issue.chosen)
    except (OSError, safecopy.CopyError, KeyError) as error:
        outcome.failed.append((issue, str(error)))
    else:
        outcome.done.append(issue)


def _to_journal(issue: Issue) -> dict:
    return {
        "issue": {
            "kind": issue.kind,
            "path": issue.path,
            "diffs": [dataclasses.asdict(d) for d in issue.diffs],
        },
        "option": dataclasses.asdict(issue.chosen),
    }


def _from_journal(params: dict) -> Issue:
    issue = params["issue"]
    diffs = [Difference(**d) for d in issue["diffs"]]
    return Issue(issue["kind"], issue["path"], diffs, [], choice=Option(**params["option"]))


def _disk(archive: Archive, disk_id: str) -> Disk:
    return next(d for d in archive.disks if d.id == disk_id)


def _good(archive: Archive, issue: Issue) -> list[Disk]:
    bad = {d.disk_id for d in issue.diffs}
    return [disk for disk in archive.disks if disk.id not in bad]


def _bad(archive: Archive, issue: Issue) -> list[Disk]:
    return [_disk(archive, d.disk_id) for d in issue.diffs]


def _replace_from(
    archive: Archive, source: Disk, targets: list[Disk], path: str, expected: str
) -> None:
    """Put ``source``'s copy of ``path`` on ``targets``; what they had goes to the trash.
    Targets that already have the right content are left alone."""
    destinations = []
    for disk in targets:
        target = archive.path_on(disk, path)
        if target.exists():
            if hashing.hash_file(target) == expected:
                continue
            trash.move_to_trash(archive, disk, path, reason=trash.REPLACED)
        destinations.append(target)
    if destinations:
        safecopy.safe_copy(archive.path_on(source, path), destinations, expected_hash=expected)


def _mark_ok(archive: Archive, path: str, disks: list[Disk]) -> None:
    for disk in disks:
        archive.index.set_copy(path, disk.id, OK, verified_at=now())


def _repair(archive: Archive, issue: Issue, option: Option) -> None:
    record = archive.index.get_file(issue.path)
    bad = _bad(archive, issue)
    _replace_from(archive, _good(archive, issue)[0], bad, issue.path, record.hash)
    with archive.index.transaction():
        _mark_ok(archive, issue.path, bad)
        archive.index.log("repaired", path=issue.path, disks=[d.label for d in bad])


def _copy(archive: Archive, issue: Issue, option: Option) -> None:
    _repair(archive, issue, option)


def _revert(archive: Archive, issue: Issue, option: Option) -> None:
    _repair(archive, issue, option)


def _delete_all(archive: Archive, issue: Issue, option: Option) -> None:
    record = archive.index.get_file(issue.path)
    for disk in archive.disks:
        if archive.path_on(disk, issue.path).exists():
            trash.move_to_trash(archive, disk, issue.path, hash_=record.hash if record else None)
    with archive.index.transaction():
        archive.index.remove_file(issue.path)
        archive.index.log("deleted", path=issue.path)


def _forget(archive: Archive, issue: Issue, option: Option) -> None:
    with archive.index.transaction():
        archive.index.remove_file(issue.path)
        archive.index.log("forgotten", path=issue.path)


def _propagate(archive: Archive, issue: Issue, option: Option) -> None:
    source = _disk(archive, option.disk_id)
    version = next(d for d in issue.diffs if d.disk_id == source.id)
    others = [disk for disk in archive.disks if disk is not source]
    _replace_from(archive, source, others, issue.path, version.hash)
    with archive.index.transaction():
        archive.index.put_file(FileRecord(issue.path, version.size, version.mtime_ns, version.hash))
        _mark_ok(archive, issue.path, archive.disks)
        archive.index.log("updated", path=issue.path, source=source.label)


def _accept(archive: Archive, issue: Issue, option: Option) -> None:
    diff = issue.diffs[0]
    with archive.index.transaction():
        if issue.kind == I_MOVED:
            _index_move(archive, issue.path, diff.target)
            _mark_ok(archive, diff.target, archive.disks)
            archive.index.log("moved", path=diff.target, source=issue.path)
        else:  # edited, or added by hand, the same way on every disk
            archive.index.put_file(FileRecord(issue.path, diff.size, diff.mtime_ns, diff.hash))
            _mark_ok(archive, issue.path, archive.disks)
            archive.index.log("accepted", path=issue.path, issue=issue.kind)


def _repeat_move(archive: Archive, issue: Issue, option: Option) -> None:
    target = issue.target
    for disk in _good(archive, issue):
        _rename(archive.path_on(disk, issue.path), archive.path_on(disk, target))
    with archive.index.transaction():
        _index_move(archive, issue.path, target)
        _mark_ok(archive, target, archive.disks)
        archive.index.log("moved", path=target, source=issue.path)


def _undo_move(archive: Archive, issue: Issue, option: Option) -> None:
    for diff in issue.diffs:
        disk = _disk(archive, diff.disk_id)
        _rename(archive.path_on(disk, diff.target), archive.path_on(disk, issue.path))
    with archive.index.transaction():
        _mark_ok(archive, issue.path, archive.disks)
        archive.index.log("move_undone", path=issue.path)


def _add(archive: Archive, issue: Issue, option: Option) -> None:
    diff = issue.diffs[0]
    having = _bad(archive, issue)
    missing = [disk for disk in archive.disks if disk not in having]
    _replace_from(archive, having[0], missing, issue.path, diff.hash)
    with archive.index.transaction():
        archive.index.put_file(FileRecord(issue.path, diff.size, diff.mtime_ns, diff.hash))
        _mark_ok(archive, issue.path, archive.disks)
        archive.index.log("added", path=issue.path)


def _delete(archive: Archive, issue: Issue, option: Option) -> None:
    for diff in issue.diffs:
        disk = _disk(archive, diff.disk_id)
        if archive.path_on(disk, issue.path).exists():
            trash.move_to_trash(archive, disk, issue.path, hash_=diff.hash)


def _known(archive: Archive, issue: Issue, option: Option) -> None:
    for diff in issue.diffs:
        mark_known(archive, diff)


def _rename(source, target) -> None:
    """Move a file, unless it was already moved (an interrupted action run again)."""
    if target.exists():
        if not source.exists():
            return
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.rename(source, target)


def _index_move(archive: Archive, old: str, new: str) -> None:
    if archive.index.get_file(old) is None and archive.index.get_file(new) is not None:
        return  # already moved
    archive.index.move_file(old, new)


_ACTIONS = {
    REPAIR: _repair,
    COPY: _copy,
    REVERT: _revert,
    DELETE_ALL: _delete_all,
    FORGET: _forget,
    PROPAGATE: _propagate,
    ACCEPT: _accept,
    REPEAT_MOVE: _repeat_move,
    UNDO_MOVE: _undo_move,
    ADD: _add,
    DELETE: _delete,
    KNOWN: _known,
}
