"""Changes made from the viewer, applied to every disk and to the index.

Rename, move, delete (to the trash) and new folder. Each multi-step change is written in
the journal first and every step can run again safely, so an interruption is finished by
:func:`recover`, like the resolution actions.
"""

from __future__ import annotations

import contextlib
import os
import re
import uuid
from pathlib import PurePosixPath

from . import trash
from .archive import Archive, ArchiveError

JOURNAL_OPERATION = "edit"
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')  # not allowed in exFAT/Windows names


class EditError(Exception):
    """The change is not possible (bad name, already exists…): nothing was changed."""


def check_name(name: str) -> str:
    name = name.strip()
    if not name or name in (".", "..") or name.startswith(".") or name.endswith("."):
        raise EditError("invalid name")
    if _FORBIDDEN.search(name):
        raise EditError("invalid characters")
    return name


def _require(archive: Archive) -> None:
    if not archive.complete:
        raise ArchiveError(f"connect all the disks first: {', '.join(archive.missing)}")


def _records_under(archive: Archive, path: str) -> list[str]:
    """The archive files at ``path`` (a file) or under it (a folder)."""
    if archive.index.get_file(path) is not None:
        return [path]
    prefix = path + "/"
    return [r.path for r in archive.index.files() if r.path.startswith(prefix)]


def _exists(archive: Archive, path: str) -> bool:
    key = path.casefold()
    if any(r.path.casefold() == key or r.path.casefold().startswith(key + "/")
           for r in archive.index.files()):  # fmt: skip
        return True
    return any(_exists_on_disk(archive.path_on(disk, path)) for disk in archive.disks)


def _exists_on_disk(path) -> bool:
    """Like exFAT: names that differ only in letter case are the same name."""
    try:
        return any(entry.casefold() == path.name.casefold() for entry in os.listdir(path.parent))
    except OSError:
        return False


# New folder


def new_folder(archive: Archive, parent: str, name: str) -> str:
    _require(archive)
    path = f"{parent}/{check_name(name)}" if parent else check_name(name)
    if _exists(archive, path):
        raise EditError("already exists")
    for disk in archive.disks:
        archive.path_on(disk, path).mkdir(parents=True, exist_ok=True)
    with archive.index.transaction():
        archive.index.log("folder_created", path=path)
    return path


# Rename and move


def rename(archive: Archive, path: str, new_name: str) -> str:
    """Rename a file or a folder in its folder; returns the new path."""
    parent = str(PurePosixPath(path).parent)
    parent = "" if parent == "." else parent
    new_name = check_name(new_name)
    new = f"{parent}/{new_name}" if parent else new_name
    return _move(archive, path, new)


def move(archive: Archive, path: str, folder: str) -> str:
    """Move a file or a folder into ``folder`` ('' = the main folder); returns the new path."""
    name = PurePosixPath(path).name
    new = f"{folder}/{name}" if folder else name
    if folder == path or folder.startswith(path + "/"):
        raise EditError("a folder can't go inside itself")
    return _move(archive, path, new)


def _move(archive: Archive, old: str, new: str) -> str:
    _require(archive)
    if old == new:
        return new
    only_case = old.casefold() == new.casefold()  # exFAT: "mare" → "Mare" is the same name
    if not only_case and _exists(archive, new):
        raise EditError("already exists")
    if not any(archive.path_on(disk, old).exists() for disk in archive.disks):
        raise EditError("not found")
    params = {"op": "move", "old": old, "new": new}
    entry = archive.index.begin(JOURNAL_OPERATION, params)
    _run(archive, params)
    with archive.index.transaction():
        archive.index.end(entry)
    archive.sync_indexes()
    return new


def _do_move(archive: Archive, old: str, new: str) -> None:
    for disk in archive.disks:
        source, target = archive.path_on(disk, old), archive.path_on(disk, new)
        if old.casefold() == new.casefold():
            if source.exists() and source.name != target.name:
                # two steps, so a case-insensitive disk really changes the name
                step = source.with_name(f".{source.name}.{uuid.uuid4().hex[:6]}")
                os.rename(source, step)
                os.rename(step, target)
            continue
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.rename(source, target)
    with archive.index.transaction():
        for path in _records_under(archive, old):
            archive.index.move_file(path, new + path[len(old) :])
        archive.index.log("renamed", path=new, source=old)


# Delete


def delete(archive: Archive, paths: list[str]) -> int:
    """Move files and folders to the trash of every disk; returns how many files."""
    _require(archive)
    files = sorted({f for path in paths for f in _records_under(archive, path)})
    params = {"op": "delete", "paths": list(paths), "files": files}
    entry = archive.index.begin(JOURNAL_OPERATION, params)
    _run(archive, params)
    with archive.index.transaction():
        archive.index.end(entry)
    archive.sync_indexes()
    return len(files)


def _do_delete(archive: Archive, paths: list[str], files: list[str]) -> None:
    for path in files:
        record = archive.index.get_file(path)
        for disk in archive.disks:
            if archive.path_on(disk, path).exists():
                trash.move_to_trash(archive, disk, path, hash_=record.hash if record else None)
        with archive.index.transaction():
            archive.index.remove_file(path)
    # Folders asked to be deleted go away if nothing else is left in them
    for path in paths:
        for disk in archive.disks:
            folder = archive.path_on(disk, path)
            if folder.is_dir():
                for sub, _, _ in sorted(os.walk(folder), key=lambda w: -len(w[0])):
                    with contextlib.suppress(OSError):
                        os.rmdir(sub)
    with archive.index.transaction():
        archive.index.log("deleted", files=len(files), paths=paths)


# Journal


def _run(archive: Archive, params: dict) -> None:
    if params["op"] == "move":
        _do_move(archive, params["old"], params["new"])
    elif params["op"] == "delete":
        _do_delete(archive, params["paths"], params["files"])


def pending(archive: Archive) -> int:
    return sum(1 for e in archive.index.journal() if e.operation == JOURNAL_OPERATION)


def recover(archive: Archive) -> int:
    """Finish the changes interrupted last time; returns how many."""
    _require(archive)
    done = 0
    for entry in archive.index.journal():
        if entry.operation != JOURNAL_OPERATION:
            continue
        _run(archive, entry.params)
        with archive.index.transaction():
            archive.index.end(entry.id)
            archive.index.log("recovered", operation=entry.params["op"])
        done += 1
    archive.sync_indexes()
    return done
