"""Take a screenshot of every screen of the app, on simulated disks (doc/sviluppo.md).

uv run python scripts/screenshots.py [--out screenshots/now]

Runs offscreen in a temporary folder: real disks are never looked at. Used to review the
interface: compare two folders of screenshots, before and after a change.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

from PySide6.QtCore import QLocale  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from photosaver.core import edit  # noqa: E402
from photosaver.core.archive import Archive  # noqa: E402
from photosaver.devtools import dev_disks  # noqa: E402
from photosaver.ui import app as app_mod  # noqa: E402
from photosaver.ui.add_photos import (  # noqa: E402
    AddPhotosFlow,
    ChooseFoldersScreen,
    PreviewScreen,
    SummaryScreen,
)
from photosaver.ui.check_flow import ChooseCheckScreen, ResultsScreen  # noqa: E402
from photosaver.ui.connect import BusyScreen, ConnectScreen  # noqa: E402
from photosaver.ui.controller import HOME  # noqa: E402
from photosaver.ui.home import HomeScreen  # noqa: E402
from photosaver.ui.prepare import ChooseDiskScreen, ConfirmScreen, IntroScreen  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "screenshots" / "now"
SIZE = (1100, 760)
SETTLE = 0.6  # seconds: animations end, thumbnails arrive


class Shooter:
    def __init__(self, out: Path):
        self.out = out
        self.count = 0
        self.failed: list[str] = []

    def wait(self, condition: Callable[[], bool], timeout: float = 30) -> None:
        end = time.monotonic() + timeout
        while not condition():
            if time.monotonic() > end:
                raise TimeoutError("the app did not get there")
            QApplication.processEvents()
            time.sleep(0.01)

    def settle(self, seconds: float = SETTLE) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            QApplication.processEvents()
            time.sleep(0.01)

    def shot(self, window, name: str) -> None:
        self.settle()
        self.count += 1
        path = self.out / f"{self.count:02d}-{name}.png"
        window.grab().save(str(path))
        print(f"  {path.name}")

    def scene(self, name: str, run: Callable[[], None]) -> None:
        print(name)
        try:
            run()
        except Exception:
            self.failed.append(name)
            traceback.print_exc()


def make_window(roots: list[Path]):
    window, controller = app_mod.build(roots)
    window.resize(*SIZE)
    window.show()
    return window, controller


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--lang", default="it", help="it or en")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("*.png"):
        old.unlink()

    app = app_mod.create_application(sys.argv[:1])
    if args.lang != "en":
        app_mod.install_translations(app, QLocale(args.lang))
    s = Shooter(args.out)
    work = Path(tempfile.mkdtemp(prefix="photosaver-shots-"))
    dev = work / "dev-disks"
    dev_disks.setup(dev)
    disk_a, disk_b = dev / "disk-a", dev / "disk-b"
    desktop = dev / "desktop"

    roots: list[Path] = []
    window, controller = make_window(roots)

    def connect() -> None:
        controller.start()
        s.wait(lambda: isinstance(window.current, ConnectScreen))
        s.shot(window, "connect-waiting")
        roots.append(disk_a)
        controller.session.refresh()
        s.shot(window, "connect-one-disk")
        roots.append(disk_b)
        controller.session.refresh()
        s.wait(lambda: isinstance(window.current, BusyScreen))
        s.shot(window, "startup-check")
        s.wait(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))
        s.shot(window, "home-safe")

    def browse() -> None:
        viewer = controller.show_viewer()
        s.shot(window, "viewer-root")
        viewer.show_folder("FOTO 2024/NEVE 2024")
        s.settle(2)
        s.shot(window, "viewer-photos")
        viewer.grid.selectionModel().select(
            viewer.model.index(1), viewer.grid.selectionModel().SelectionFlag.Select
        )
        s.shot(window, "viewer-selected")
        viewer._open(viewer.model.index(0))
        s.settle(1.5)
        s.shot(window, "preview-photo")
        window.back()
        window.back()

    def add_photos() -> None:
        controller.add_photos()
        choose = window.current
        assert isinstance(choose, ChooseFoldersScreen)
        s.shot(window, "add-choose-empty")
        choose.add_folder(desktop / "MARE 2026")
        choose.add_folder(desktop / "LAGO 2026")
        s.shot(window, "add-choose-folders")
        choose.primary.click()
        s.shot(window, "add-analysing")
        s.wait(lambda: isinstance(window.current, PreviewScreen))
        s.shot(window, "add-preview")
        window.current.primary.click()
        s.wait(lambda: isinstance(window.current, BusyScreen))
        window.current.set_progress(42, 100, "1,2 GB / 3,0 GB  ·  circa 2 minuti")
        s.shot(window, "add-copying")
        s.wait(lambda: isinstance(window.current, SummaryScreen))
        s.shot(window, "add-summary")
        window.current.keep_requested.emit()
        s.wait(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))

    def check_choose() -> None:
        controller.check_disks()
        assert isinstance(window.current, ChooseCheckScreen)
        s.shot(window, "check-choose")
        window.current.back_requested.emit()
        s.wait(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))

    def history() -> None:
        controller.show_history()
        s.shot(window, "history")

    def trash_empty() -> None:
        controller.show_trash()
        s.shot(window, "trash-empty")
        window.back()

    def broken() -> None:
        dev_disks.break_disks(dev, list(dev_disks.SCENARIOS), seed=1)
        controller.mode = ""
        controller.on_changed()
        s.wait(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))
        s.shot(window, "home-warning")
        controller.show_viewer()
        s.shot(window, "viewer-problems")
        window.back()
        window.current.status.action.click()
        s.wait(lambda: isinstance(window.current, ResultsScreen), timeout=60)
        s.shot(window, "check-results")
        results = window.current
        for row in results.rows:
            if row.group.choice is None:
                row.choice.setCurrentIndex(1)
        results.primary.click()
        s.wait(
            lambda: isinstance(window.current, ResultsScreen) and not window.current.groups,
            timeout=60,
        )
        s.shot(window, "check-all-good")
        window.current.primary.click()
        s.wait(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))

    def trash_full() -> None:
        with Archive.open(list(controller.disks)) as archive:
            photos = [r.path for r in archive.index.files() if "NEVE" in r.path][:6]
            edit.delete(archive, photos)
        controller.show_trash()
        s.shot(window, "trash-full")
        window.back()

    def done() -> None:
        controller.finish()
        s.shot(window, "done")

    for name, scene in (
        ("connect", connect),
        ("browse", browse),
        ("add photos", add_photos),
        ("check choose", check_choose),
        ("history", history),
        ("trash empty", trash_empty),
        ("broken disks", broken),
        ("trash full", trash_full),
        ("done", done),
    ):
        s.scene(name, scene)
    controller.shutdown()
    window.close()

    # One disk only: read-only home
    def read_only() -> None:
        w, c = make_window([disk_a])
        c.start()
        s.wait(lambda: isinstance(w.current, ConnectScreen))
        w.current.one_disk.click()
        s.shot(w, "home-read-only")
        c.shutdown()
        w.close()

    # New disks: prepare them
    def prepare() -> None:
        new = [work / "new-1", work / "new-2"]
        for root in new:
            root.mkdir()
        w, c = make_window(new)
        c.start()
        s.wait(lambda: isinstance(w.current, ConnectScreen))
        s.shot(w, "connect-new-disk")
        w.current.message.action.click()
        assert isinstance(w.current, IntroScreen)
        s.shot(w, "prepare-intro")
        w.current.primary.click()
        assert isinstance(w.current, ChooseDiskScreen)
        next(iter(w.current._choices)).setChecked(True)
        s.shot(w, "prepare-choose")
        w.current.primary.click()
        assert isinstance(w.current, ConfirmScreen)
        s.shot(w, "prepare-confirm")
        w.current.agree.setChecked(True)
        w.current.primary.click()
        s.wait(lambda: hasattr(w.current, "primary") and not isinstance(w.current, ConfirmScreen))
        s.shot(w, "prepare-ready")
        c.shutdown()
        w.close()

    def failure() -> None:
        w, c = make_window([disk_a, disk_b])
        c.start()
        s.wait(lambda: c.mode == HOME)
        w.open(BusyScreen("…"))
        AddPhotosFlow(w, list(c.disks), c.run, c)._failed("[Errno 5] Input/output error")
        s.shot(w, "add-failed")
        c.shutdown()
        w.close()

    s.scene("read only", read_only)
    s.scene("prepare", prepare)
    s.scene("failure", failure)

    print(f"\n{s.count} screenshots in {args.out}")
    if s.failed:
        print("Failed scenes: " + ", ".join(s.failed))
    return 1 if s.failed else 0


if __name__ == "__main__":
    sys.exit(main())
