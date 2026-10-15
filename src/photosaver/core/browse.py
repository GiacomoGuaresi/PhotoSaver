"""The archive as folders, for the viewer: built from the index, so one disk is enough.

Empty folders are not in the index (it lists files): they are added from a disk, so a
folder just created in the app shows up.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .index import OK, FileRecord
from .scanner import is_hidden


@dataclass
class Folder:
    name: str
    path: str  # relative to the archive folder, '' for the root
    folders: dict[str, Folder] = field(default_factory=dict)
    files: list[FileRecord] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Files here and in every subfolder."""
        return len(self.files) + sum(child.count for child in self.folders.values())

    def children(self) -> list[Folder]:
        return sorted(self.folders.values(), key=lambda f: f.name.casefold())

    def find(self, path: str) -> Folder | None:
        node = self
        for part in [p for p in path.split("/") if p]:
            node = node.folders.get(part)
            if node is None:
                return None
        return node

    def walk(self) -> Iterable[Folder]:
        yield self
        for child in self.children():
            yield from child.walk()


def build_tree(records: Iterable[FileRecord], folders: Iterable[str] = ()) -> Folder:
    """The folder tree of ``records``, plus the (possibly empty) ``folders``."""
    root = Folder("", "")

    def node_for(parts: list[str]) -> Folder:
        node = root
        for i, part in enumerate(parts):
            if part not in node.folders:
                node.folders[part] = Folder(part, "/".join(parts[: i + 1]))
            node = node.folders[part]
        return node

    for folder in folders:
        node_for([p for p in folder.split("/") if p])
    for record in records:
        *parts, _ = record.path.split("/")
        node_for(parts).files.append(record)
    for node in root.walk():
        node.files.sort(key=lambda r: r.path.rsplit("/", 1)[-1].casefold())
    return root


def disk_folders(archive_dir: Path) -> list[str]:
    """Every folder under the archive folder of a disk (folders only: quick)."""
    found = []

    def walk(folder: Path, relative: str) -> None:
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if is_hidden(entry.name) or not entry.is_dir(follow_symlinks=False):
                        continue
                    path = f"{relative}/{entry.name}" if relative else entry.name
                    found.append(path)
                    walk(Path(entry.path), path)
        except OSError:
            return

    walk(archive_dir, "")
    return found


def copy_problems(index, disk_ids: list[str], issues=()) -> dict[str, dict[str, str]]:
    """Files with a problem on some disk: path → {disk id: kind}.

    Kinds are those of the last thorough check recorded in the index (missing, corrupt,
    modified), updated with the ``issues`` of a more recent check. Copies never
    verified are not problems.
    """
    problems: dict[str, dict[str, str]] = {}
    for disk_id in disk_ids:
        for path, copy in index.copies_on(disk_id).items():
            if copy.state != OK:
                problems.setdefault(path, {})[disk_id] = copy.state
    for issue in issues:
        if index.get_file(issue.path) is None:
            continue  # files added outside the app are not in the viewer
        for diff in issue.diffs:
            kind = diff.kind if diff.kind != "moved" else "missing"
            problems.setdefault(issue.path, {})[diff.disk_id] = kind
    return problems


def folder_problems(problems: dict[str, dict[str, str]]) -> dict[str, int]:
    """How many files with problems in each folder, subfolders included ('' = all)."""
    counts: dict[str, int] = {}
    for path in problems:
        parts = path.split("/")[:-1]
        for depth in range(len(parts) + 1):
            folder = "/".join(parts[:depth])
            counts[folder] = counts.get(folder, 0) + 1
    return counts
