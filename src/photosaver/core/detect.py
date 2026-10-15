"""Which disks are connected, and what that means for the archive.

The app looks at a list of candidate folders (the roots of the connected volumes; during
development, the simulated disks) and sorts them out: PhotoSaver disks, new empty disks,
anything else. Reading only: nothing is ever written here.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .archive import open_index
from .disk import Disk, DiskError, is_disk, open_disk

ENV_DISKS = "PHOTOSAVER_DISKS"  # development: candidate folders, separated by os.pathsep

# Situations
WAITING = "waiting"  # no disk of an archive
MIXED = "mixed"  # disks of different archives
PARTIAL = "partial"  # some disks of the archive, not all
COMPLETE = "complete"  # every disk of the archive


@dataclass
class Found:
    disks: list[Disk] = field(default_factory=list)
    empty: list[Path] = field(default_factory=list)  # new disks, ready to be prepared
    other: list[Path] = field(default_factory=list)  # not disks of an archive, not empty
    unreadable: list[Path] = field(default_factory=list)  # broken .photosaver/disk.json


@dataclass
class Assessment:
    situation: str
    disks: list[Disk] = field(default_factory=list)  # connected disks of the archive
    missing: list[str] = field(default_factory=list)  # labels of the disks not connected
    all_labels: list[str] = field(default_factory=list)


def configured_roots(env: dict[str, str] | None = None) -> list[Path]:
    value = (env if env is not None else os.environ).get(ENV_DISKS, "")
    return [Path(part) for part in value.split(os.pathsep) if part]


def scan_roots(roots: Iterable[Path]) -> Found:
    found = Found()
    for root in roots:
        try:
            if not root.is_dir():
                continue
            if is_disk(root):
                try:
                    found.disks.append(open_disk(root))
                except DiskError:
                    found.unreadable.append(root)
            elif _is_empty(root):
                found.empty.append(root)
            else:
                found.other.append(root)
        except OSError:
            found.unreadable.append(root)
    return found


def assess(found: Found) -> Assessment:
    """The situation for the user, from the PhotoSaver disks found."""
    if not found.disks:
        return Assessment(WAITING)
    if len({disk.info.archive_id for disk in found.disks}) > 1:
        return Assessment(MIXED, found.disks)
    disks = sorted(found.disks, key=lambda d: d.label)
    labels = _archive_labels(disks)
    connected = {disk.label for disk in disks}
    missing = [label for label in labels if label not in connected]
    situation = PARTIAL if missing else COMPLETE
    return Assessment(situation, disks, missing, sorted(set(labels) | connected))


def free_space(root: Path) -> int | None:
    try:
        return shutil.disk_usage(root).free
    except OSError:
        return None


def _archive_labels(disks: list[Disk]) -> list[str]:
    """Every disk of the archive, from the most recent index among the connected disks."""
    best: tuple[int, list[str]] = (-1, [])
    for disk in disks:
        try:
            with open_index(disk) as index:
                revision = index.revision
                if revision > best[0]:
                    best = (revision, [d.label for d in index.disks()])
        except Exception:  # an unreadable index: the other disks still tell
            continue
    return best[1] or [disk.label for disk in disks]


def _is_empty(root: Path) -> bool:
    """Nothing but system leftovers (lost+found, recycle bin, Spotlight…)."""
    ignored = {"lost+found", "$recycle.bin", "system volume information", ".trashes",
               ".spotlight-v100", ".fseventsd", ".ds_store"}  # fmt: skip
    return all(entry.name.lower() in ignored for entry in os.scandir(root))
