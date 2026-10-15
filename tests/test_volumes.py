import sys
from pathlib import Path

import pytest

from photosaver.core import volumes

MOUNTS = """\
/dev/nvme0n1p2 / ext4 rw,relatime 0 0
proc /proc proc rw 0 0
/dev/sdb1 /run/media/user/TOSHIBA\\040EXT fuseblk rw 0 0
/dev/sdc1 /media/user/DISCO1 exfat rw 0 0
/dev/sdd1 /mnt/backup ext4 rw 0 0
tmpfs /run/user/1000 tmpfs rw 0 0
"""


def test_linux_roots():
    assert volumes.linux_roots(MOUNTS) == [
        Path("/run/media/user/TOSHIBA EXT"),
        Path("/media/user/DISCO1"),
        Path("/mnt/backup"),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_mac_roots(tmp_path):
    (tmp_path / "DISCO1").mkdir()
    (tmp_path / "Macintosh HD").symlink_to("/")
    assert volumes.mac_roots(tmp_path) == [tmp_path / "DISCO1"]
    assert volumes.mac_roots(tmp_path / "missing") == []


def test_eject_commands():
    root = Path("/media/user/DISCO1")
    assert volumes.eject_command(root, "linux") == ["gio", "mount", "--unmount", str(root)]
    assert volumes.eject_command(root, "darwin")[:2] == ["diskutil", "eject"]
    assert "Eject" in volumes.eject_command(Path("E:\\"), "win32")[-1]
    assert volumes.eject_command(root, "plan9") is None


def test_mounted_roots_runs():
    assert isinstance(volumes.mounted_roots(), list)
