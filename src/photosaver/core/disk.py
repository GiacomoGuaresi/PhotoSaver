"""Disk identity: the ``.photosaver/disk.json`` file that makes a folder a PhotoSaver disk.

A disk is just a root folder (a real drive or a simulated one): nothing here depends on
mount points, volume labels or filesystems.

::

    <root>/
    ├── .photosaver/
    │   └── disk.json    which disk this is, and of which archive
    └── <archive_dir>/   the photos, readable without the app
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = ".photosaver"
DISK_FILE = "disk.json"
FORMAT = 1


class DiskError(Exception):
    """Base class for disk identity errors."""


class NotADisk(DiskError):
    """The folder has no (readable) ``.photosaver/disk.json``."""


class AlreadyADisk(DiskError):
    """The folder is already a PhotoSaver disk: initializing it again would lose its identity."""


class UnsupportedFormat(DiskError):
    """The disk was written by a newer version of the app."""


@dataclass(frozen=True)
class DiskInfo:
    disk_id: str
    archive_id: str
    label: str
    archive_dir: str
    created: str
    format: int = FORMAT


@dataclass(frozen=True)
class Disk:
    root: Path
    info: DiskInfo

    @property
    def data_dir(self) -> Path:
        return self.root / DATA_DIR

    @property
    def archive(self) -> Path:
        return self.root / self.info.archive_dir

    @property
    def id(self) -> str:
        return self.info.disk_id

    @property
    def label(self) -> str:
        return self.info.label


def new_id() -> str:
    return uuid.uuid4().hex


def is_disk(root: Path) -> bool:
    return (root / DATA_DIR / DISK_FILE).is_file()


def init_disk(root: Path, *, label: str, archive_dir: str, archive_id: str | None = None) -> Disk:
    """Make ``root`` a disk of the archive ``archive_id`` (a new archive when not given).

    Creates ``.photosaver/`` and the archive folder; files already in ``root`` are left alone.
    """
    _check_archive_dir(archive_dir)
    if (root / DATA_DIR).exists():
        raise AlreadyADisk(f"{root} is already a PhotoSaver disk")
    if not root.is_dir():
        raise NotADisk(f"{root} is not a folder")

    info = DiskInfo(
        disk_id=new_id(),
        archive_id=archive_id or new_id(),
        label=label,
        archive_dir=archive_dir,
        created=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    (root / DATA_DIR).mkdir()
    (root / archive_dir).mkdir(exist_ok=True)
    write_json(root / DATA_DIR / DISK_FILE, asdict(info))
    return Disk(root, info)


def open_disk(root: Path) -> Disk:
    path = root / DATA_DIR / DISK_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise NotADisk(f"{root} is not a PhotoSaver disk") from None
    except (OSError, ValueError) as error:
        raise NotADisk(f"{path} is unreadable: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("format"), int):
        raise NotADisk(f"{path} is not a disk file")
    if data["format"] > FORMAT:
        raise UnsupportedFormat(f"{root} was written by a newer PhotoSaver: please update")
    try:
        info = DiskInfo(**{field: data[field] for field in DiskInfo.__dataclass_fields__})
    except KeyError as error:
        raise NotADisk(f"{path} misses {error}") from None
    return Disk(root, info)


def write_json(path: Path, data: dict) -> None:
    """Write ``path`` atomically: a crash leaves either the old file or the new one."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)


def _check_archive_dir(name: str) -> None:
    if not name or name.startswith(".") or "/" in name or "\\" in name or name in ("..",):
        raise ValueError(f"invalid archive folder name: {name!r}")
