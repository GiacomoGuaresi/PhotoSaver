"""Simulated disks for development (see doc/sviluppo.md).

::

    dev-disks/
    ├── .dev-disks      marker: only folders with it can be reset
    ├── disk-a/         simulated disk 1 (empty: the app initializes it)
    ├── disk-b/         simulated disk 2
    └── desktop/        folders to upload: new events and an old archive to reload
"""

from __future__ import annotations

import os
import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .fake_media import Gps, make_file, make_photo, make_video

MARKER = ".dev-disks"
DISKS = ("disk-a", "disk-b")
DESKTOP = "desktop"

SAMSUNG = ("samsung", "Galaxy S99")
PIXEL = ("Google", "Pixel 99")
REFLEX = ("NIKON CORPORATION", "NIKON D0000")

# Generic places, far from anyone's home
SEA = Gps(39.2238, 9.1217)
LAKE = Gps(45.9850, 9.2600)
SNOW = Gps(46.5000, 11.3500)


class NotDevDisks(Exception):
    """The folder exists but was not created by this module: never deleted."""


def reset(root: Path) -> None:
    """Delete the simulated disks under ``root``, only if they carry the marker."""
    if not root.exists():
        return
    if not (root / MARKER).is_file():
        raise NotDevDisks(f"{root} has no {MARKER} marker: not deleting it")
    shutil.rmtree(root)


def create(root: Path, *, seed: int = 0, scale: int = 1) -> dict[str, int]:
    """Create fresh simulated disks under ``root`` and return how many files of each kind.

    ``scale`` multiplies the number of photos, to try bigger archives.
    """
    reset(root)
    root.mkdir(parents=True)
    (root / MARKER).write_text("Simulated disks for PhotoSaver development.\n")
    for disk in DISKS:
        (root / disk).mkdir()

    gen = _Generator(root / DESKTOP, random.Random(seed), scale)
    gen.new_events()
    gen.old_archive()
    return gen.counts


class _Generator:
    def __init__(self, desktop: Path, rng: random.Random, scale: int) -> None:
        self.desktop = desktop
        self.rng = rng
        self.scale = scale
        self.counts = {"photos": 0, "videos": 0, "ignored": 0}

    def _seed(self) -> int:
        return self.rng.randrange(2**32)

    def _moments(self, start: datetime, count: int, hours: int = 8) -> list[datetime]:
        seconds = hours * 3600
        offsets = sorted(self.rng.sample(range(seconds), count))  # distinct: names are unique
        return [start + timedelta(seconds=s) for s in offsets]

    def _near(self, place: Gps) -> Gps:
        return Gps(
            place.lat + self.rng.uniform(-0.01, 0.01), place.lon + self.rng.uniform(-0.01, 0.01)
        )

    # File kinds, named as the devices name them

    def samsung(self, folder: Path, start: datetime, count: int, place: Gps | None) -> None:
        for taken in self._moments(start, count * self.scale):
            # About 60% of phone photos carry a position, as in the real archive
            gps = self._near(place) if place and self.rng.random() < 0.6 else None
            name = taken.strftime("%Y%m%d_%H%M%S") + ".jpg"
            make_photo(folder / name, taken=taken, camera=SAMSUNG, gps=gps, seed=self._seed())
            self.counts["photos"] += 1

    def pixel(self, folder: Path, start: datetime, count: int) -> None:
        for taken in self._moments(start, count * self.scale):
            name = taken.strftime("IMG_%Y%m%d_%H%M%S") + ".jpg"
            make_photo(folder / name, taken=taken, camera=PIXEL, seed=self._seed())
            self.counts["photos"] += 1

    def whatsapp(self, folder: Path, start: datetime, count: int) -> None:
        """No EXIF: the date is only in the name; the file date is when it was saved."""
        for n, taken in enumerate(self._moments(start, count * self.scale), start=1):
            name = taken.strftime("IMG-%Y%m%d-WA") + f"{n:04d}.jpg"
            saved = taken + timedelta(days=self.rng.randrange(1, 30))
            make_photo(folder / name, seed=self._seed(), mtime=saved)
            self.counts["photos"] += 1

    def reflex(self, folder: Path, start: datetime, count: int) -> None:
        first = self.rng.randrange(1000, 9000)
        for n, taken in enumerate(self._moments(start, count * self.scale)):
            name = f"DSC_{first + n:04d}.JPG"
            make_photo(folder / name, taken=taken, camera=REFLEX, seed=self._seed())
            self.counts["photos"] += 1

    def videos(self, folder: Path, start: datetime, count: int) -> None:
        for taken in self._moments(start, count):
            name = taken.strftime("%Y%m%d_%H%M%S") + ".mp4"
            make_video(folder / name, seed=self._seed(), mtime=taken)
            self.counts["videos"] += 1

    def ignored(self, folder: Path, names: list[str]) -> None:
        for name in names:
            make_file(folder / name, self.rng.randbytes(self.rng.randrange(100, 2000)))
            self.counts["ignored"] += 1

    # Layout

    def new_events(self) -> None:
        """Folders just organized on the desktop, ready for upload."""
        sea = self.desktop / "MARE 2026"
        self.samsung(sea, datetime(2026, 8, 10, 9), 20, SEA)
        self.samsung(sea / "Spiaggia", datetime(2026, 8, 11, 10), 8, SEA)
        self.videos(sea, datetime(2026, 8, 10, 9), 2)
        self.whatsapp(sea, datetime(2026, 8, 12, 12), 3)

        lake = self.desktop / "LAGO 2026"
        self.pixel(lake, datetime(2026, 9, 20, 10), 10)
        self.whatsapp(lake, datetime(2026, 9, 20, 10), 6)
        self.ignored(lake, ["note.txt", "biglietti.pdf", "canzone.mp3"])

    def old_archive(self) -> None:
        """An existing Year → Event archive, to reload as a whole tree."""
        archive = self.desktop / "vecchio-archivio" / "FOTO FAMIGLIA"
        y2024 = archive / "FOTO 2024"
        self.samsung(y2024, datetime(2024, 3, 2, 9), 6, None)
        self.samsung(y2024 / "NEVE 2024", datetime(2024, 1, 20, 9), 10, SNOW)
        self.samsung(y2024 / "GITA 2024" / "Spiaggia", datetime(2024, 6, 1, 9), 5, SEA)
        self.reflex(y2024 / "GITA 2024", datetime(2024, 6, 2, 9), 5)

        y2025 = archive / "FOTO 2025"
        self.samsung(y2025 / "LAGO 2025", datetime(2025, 5, 4, 9), 10, LAKE)
        self.whatsapp(y2025 / "LAGO 2025", datetime(2025, 5, 4, 9), 4)
        self.videos(y2025 / "LAGO 2025", datetime(2025, 5, 4, 9), 1)

        self.ignored(archive / "MUSICA", ["brano 1.mp3", "brano 2.m4a"])
        self.ignored(y2025, ["Thumbs.db", "desktop.ini"])


# A ready archive and ways to break it


def setup(root: Path, *, seed: int = 0) -> None:
    """Fresh simulated disks with an archive on A and B, holding the old archive."""
    from photosaver.core import archive, upload  # the app's own code, as a user would use it

    create(root, seed=seed)
    a = archive.create_archive(root / "disk-a", label="A", archive_dir="Foto")
    b = archive.join_archive(a, root / "disk-b", label="B")
    with archive.Archive.open([a, b]) as arch:
        plan = upload.analyze([root / DESKTOP / "vecchio-archivio" / "FOTO FAMIGLIA"])
        plan.folders[0].destination = ""
        upload.resolve(plan, arch)
        upload.apply(plan, arch)


def _photos(root: Path, disk: str) -> list[Path]:
    return sorted((root / disk / "Foto").rglob("*.jpg"))


def _pick(root: Path, disk: str, rng: random.Random) -> Path:
    return rng.choice(_photos(root, disk))


def _keep_date(path: Path, change) -> None:
    stat = path.stat()
    change(path)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def break_corrupt(root: Path, rng: random.Random) -> str:
    """Silent corruption: a byte changes on disk B, size and date do not."""
    path = _pick(root, "disk-b", rng)

    def flip(p: Path) -> None:
        data = bytearray(p.read_bytes())
        data[len(data) // 2] ^= 0xFF
        p.write_bytes(bytes(data))

    _keep_date(path, flip)
    return f"corrupted {path.relative_to(root)}"


def break_truncate(root: Path, rng: random.Random) -> str:
    """A copy cut to 0 bytes on disk A, date unchanged."""
    path = _pick(root, "disk-a", rng)
    _keep_date(path, lambda p: p.write_bytes(b""))
    return f"emptied {path.relative_to(root)}"


def break_delete(root: Path, rng: random.Random) -> str:
    """A photo deleted by hand from disk A."""
    path = _pick(root, "disk-a", rng)
    path.unlink()
    return f"deleted {path.relative_to(root)}"


def break_move(root: Path, rng: random.Random) -> str:
    """An event folder renamed by hand on disk B."""
    folders = sorted({p.parent for p in _photos(root, "disk-b")} - {root / "disk-b" / "Foto"})
    folder = rng.choice(folders)
    target = folder.with_name(folder.name + " (rinominata)")
    folder.rename(target)
    return f"renamed {folder.relative_to(root)} → {target.name}"


def break_edit(root: Path, rng: random.Random) -> str:
    """A photo edited with another program on disk A: new content, new date."""
    path = _pick(root, "disk-a", rng)
    make_photo(path, seed=rng.randrange(2**32), mtime=datetime.now())
    return f"edited {path.relative_to(root)}"


def break_add(root: Path, rng: random.Random) -> str:
    """A photo copied by hand onto disk A only."""
    path = root / "disk-a" / "Foto" / "FOTO 2025" / "aggiunta a mano.jpg"
    make_photo(path, taken=datetime(2025, 12, 25, 12), seed=rng.randrange(2**32))
    return f"added {path.relative_to(root)}"


def break_partial(root: Path, rng: random.Random) -> str:
    """An interrupted copy: a half-written partial file left on disk B."""
    path = _pick(root, "disk-b", rng)
    partial = path.with_name(f".{path.name}.photosaver-partial")
    partial.write_bytes(path.read_bytes()[: path.stat().st_size // 2])
    return f"left {partial.relative_to(root)}"


def break_desktop(root: Path, rng: random.Random) -> str:
    """Odd files among the photos to upload: a 0-byte photo and Windows shortcuts."""
    folder = root / DESKTOP / "LAGO 2026"
    make_file(folder / "20260920_180000.jpg", b"")
    for n in range(3):
        make_file(folder / f"IMG_{n:04d}.jpg.lnk", b"L\x00\x00\x00" + rng.randbytes(60))
    return "added a 0-byte photo and 3 .lnk shortcuts to desktop/LAGO 2026"


SCENARIOS = {
    "corrupt": break_corrupt,
    "truncate": break_truncate,
    "delete": break_delete,
    "move": break_move,
    "edit": break_edit,
    "add": break_add,
    "partial": break_partial,
    "desktop": break_desktop,
}


def break_disks(root: Path, names: list[str], *, seed: int = 0) -> list[str]:
    """Apply failure scenarios to set-up simulated disks; returns what was done."""
    if not (root / MARKER).is_file():
        raise NotDevDisks(f"{root} has no {MARKER} marker: not touching it")
    rng = random.Random(seed)
    return [SCENARIOS[name](root, rng) for name in names]
