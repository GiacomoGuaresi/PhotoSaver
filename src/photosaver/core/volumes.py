"""Connected volumes: where to look for PhotoSaver disks, and how to unplug them safely.

Only reads the system's list of mounted volumes; never writes to a disk.
"""

from __future__ import annotations

import os
import string
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

# Linux: where desktops mount removable disks
LINUX_MEDIA = ("/run/media/", "/media/", "/mnt/")


def _unescape(field: str) -> str:
    """/proc/mounts writes spaces and a few other characters as octal escapes."""
    out, i = [], 0
    while i < len(field):
        if field[i] == "\\" and field[i + 1 : i + 4].isdigit():
            out.append(chr(int(field[i + 1 : i + 4], 8)))
            i += 4
        else:
            out.append(field[i])
            i += 1
    return "".join(out)


def linux_roots(mounts_text: str) -> list[Path]:
    roots = []
    for line in mounts_text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount_point = _unescape(parts[1])
        if mount_point.startswith(LINUX_MEDIA):
            roots.append(Path(mount_point))
    return roots


def mac_roots(volumes: Path = Path("/Volumes")) -> list[Path]:
    try:
        entries = sorted(volumes.iterdir())
    except OSError:
        return []
    # The system disk appears in /Volumes as a link to /
    return [entry for entry in entries if not entry.is_symlink() and entry.is_dir()]


def windows_roots(env: Mapping[str, str] | None = None) -> list[Path]:
    env = os.environ if env is None else env
    system = env.get("SYSTEMDRIVE", "C:").upper().rstrip("\\")
    if hasattr(os, "listdrives"):
        drives = os.listdrives()
    else:  # Python < 3.12
        drives = [
            f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")
        ]
    return [Path(drive) for drive in drives if drive.upper().rstrip("\\") != system]


def mounted_roots() -> list[Path]:
    """Roots of the volumes that may be PhotoSaver disks, on this computer."""
    if sys.platform.startswith("linux"):
        try:
            return linux_roots(Path("/proc/self/mounts").read_text(encoding="utf-8"))
        except OSError:
            return []
    if sys.platform == "darwin":
        return mac_roots()
    if sys.platform == "win32":
        return windows_roots()
    return []


def eject_command(root: Path, platform: str = sys.platform) -> list[str] | None:
    """The system command that unmounts ``root`` so it can be unplugged safely."""
    if platform.startswith("linux"):
        return ["gio", "mount", "--unmount", str(root)]
    if platform == "darwin":
        return ["diskutil", "eject", str(root)]
    if platform == "win32":
        drive = str(root).rstrip("\\")
        script = (
            "(New-Object -ComObject Shell.Application).Namespace(17)"
            f".ParseName('{drive}').InvokeVerb('Eject')"
        )
        return ["powershell", "-NoProfile", "-Command", script]
    return None


def eject(root: Path) -> bool:
    """Unmount a volume; False if the system refused (a file still open…)."""
    command = eject_command(root)
    if command is None:
        return False
    try:
        result = subprocess.run(command, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
