"""Two small exFAT disks for testing, as image files mounted in loop (Linux, no root).

    uv run python scripts/exfat_loop.py up      # create and mount; prints the variable to set
    uv run python scripts/exfat_loop.py down    # unmount and delete

Needs mkfs.exfat (exfatprogs) and udisksctl (udisks2). Then set the printed
PHOTOSAVER_EXFAT variable and run ``uv run pytest tests/test_exfat.py``.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

STATE = Path(tempfile.gettempdir()) / "photosaver-exfat.json"
LABELS = ("PSTEST1", "PSTEST2")
SIZE = "128M"


def run(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def mount_point(device: str) -> str:
    for _ in range(20):
        try:
            return run("findmnt", "-n", "-o", "TARGET", device).strip()
        except subprocess.CalledProcessError:
            time.sleep(0.5)
    out = run("udisksctl", "mount", "-b", device, "--no-user-interaction")
    return out.strip().split(" at ", 1)[1].rstrip(".")


def up() -> None:
    folder = Path(tempfile.mkdtemp(prefix="photosaver-exfat-"))
    disks = []
    for label in LABELS:
        image = folder / f"{label}.img"
        run("truncate", "-s", SIZE, str(image))
        run("mkfs.exfat", "-L", label, str(image))
        out = run("udisksctl", "loop-setup", "-f", str(image), "--no-user-interaction")
        device = re.search(r"/dev/loop\d+", out).group(0)
        disks.append({"image": str(image), "device": device, "mount": mount_point(device)})
    STATE.write_text(json.dumps({"folder": str(folder), "disks": disks}))
    print("export PHOTOSAVER_EXFAT=" + ":".join(d["mount"] for d in disks))


def down() -> None:
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text())
    for disk in state["disks"]:
        subprocess.run(["udisksctl", "unmount", "-b", disk["device"], "--no-user-interaction"],
                       capture_output=True)  # fmt: skip
        subprocess.run(["udisksctl", "loop-delete", "-b", disk["device"], "--no-user-interaction"],
                       capture_output=True)  # fmt: skip
        Path(disk["image"]).unlink(missing_ok=True)
    Path(state["folder"]).rmdir()
    STATE.unlink()
    print("Removed the test disks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["up", "down"])
    command = parser.parse_args().command
    sys.exit(up() if command == "up" else down())
