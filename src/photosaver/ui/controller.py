"""The conductor: from what is connected to what the user sees.

- No disk, new disks, wrong disks → "Connect the disks".
- Every disk of the archive → quick check → home, safe or with what to fix.
- Only some disks, and the user said so → home, read-only.
- A disk unplugged → back to "Connect the disks".
"""

from __future__ import annotations

from PySide6.QtCore import QLocale, QObject

from ..core import browse, detect, status, trash
from ..core.archive import Archive
from . import theme
from .add_photos import AddPhotosFlow
from .check_flow import CheckFlow
from .connect import BusyScreen, ConnectScreen, DoneScreen
from .history_trash import HistoryScreen, TrashScreen
from .home import HomeScreen
from .main_window import MainWindow
from .prepare import PrepareFlow
from .screen import Banner
from .session import Session, disk_name
from .viewer import ViewerScreen
from .workers import Worker

# Modes
CONNECT = "connect"
CHECKING = "checking"
HOME = "home"
READ_ONLY = "read_only"
DONE = "done"
PREPARE = "prepare"
ADD = "add"
CHECK = "check"


class Controller(QObject):
    def __init__(self, window: MainWindow, session: Session, parent: QObject | None = None):
        super().__init__(parent)
        self.window = window
        self.session = session
        self.mode = ""
        self.startup: status.Startup | None = None
        self._busy = False
        self._workers: set[Worker] = set()
        session.changed.connect(self.on_changed)
        window.disk_bar.done_requested.connect(self.finish)
        menu = window.disk_bar.menu
        self.history_action = menu.addAction(
            theme.icon("history"), self.tr("History"), self.show_history
        )
        self.trash_action = menu.addAction(theme.icon("trash-2"), self.tr("Trash"), self.show_trash)
        self._update_menu()

    @property
    def busy(self) -> bool:
        """An operation is running: screens are not switched under it."""
        return self._busy

    @busy.setter
    def busy(self, value: bool) -> None:
        self._busy = value
        self._update_menu()

    def _update_menu(self) -> None:
        available = bool(self.session.assessment.disks) and not self._busy
        available &= self.session.assessment.situation in (detect.COMPLETE, detect.PARTIAL)
        available &= self.mode in (HOME, READ_ONLY)
        self.history_action.setEnabled(available)
        self.trash_action.setEnabled(available)

    @property
    def disks(self):
        return self.session.assessment.disks

    def start(self) -> None:
        self.session.start()

    # Reacting to the disks

    def on_changed(self) -> None:
        found, assessment = self.session.found, self.session.assessment
        self._update_disk_bar()
        self._update_menu()
        if self.mode == DONE or self.busy:
            return
        situation = assessment.situation
        if situation == detect.COMPLETE:
            if self.mode not in (CHECKING, HOME):
                self.run_startup_check()
        elif situation == detect.PARTIAL and self.mode == READ_ONLY:
            self._show_read_only()
        else:
            self._show_connect(found, assessment)

    def _show_connect(self, found, assessment) -> None:
        screen = self.window.current
        if self.mode != CONNECT or not isinstance(screen, ConnectScreen):
            self.mode = CONNECT
            screen = self.window.reset(ConnectScreen())
            screen.one_disk_requested.connect(self.open_read_only)
            screen.prepare_requested.connect(self.prepare)
        screen.update_state(found, assessment)

    def _update_disk_bar(self) -> None:
        assessment = self.session.assessment
        connected = {d.label: d for d in assessment.disks}
        chips = []
        for label in assessment.all_labels or ["A", "B"]:
            name = self.tr("Disk %1").replace("%1", disk_name(label))
            disk = connected.get(label)
            if disk is None:
                chips.append((name, False, self.tr("not connected")))
                continue
            free = detect.free_space(disk.root)
            detail = self.tr("connected")
            if free is not None:
                size = QLocale().formattedDataSize(free, 1, QLocale.DataSizeFormat.DataSizeSIFormat)
                detail = self.tr("connected · %1 free").replace("%1", size)
            chips.append((name, True, detail))
        self.window.disk_bar.set_disks(chips)

    # Startup check

    def run_startup_check(self) -> None:
        self.mode = CHECKING
        screen = BusyScreen(
            self.tr("Perfect, both disks are here"),
            self.tr("I'm checking that all the photos are fine… it takes a few seconds."),
        )
        self.window.reset(screen)
        disks = list(self.disks)
        self.run(
            lambda **kw: status.startup_check(disks, **kw),
            self._on_startup_checked,
            screen.set_progress,
        )

    def _on_startup_checked(self, result: status.Startup) -> None:
        self.startup = result
        self.mode = HOME
        home = self._home()
        home.set_read_only(False)
        if result.interrupted:
            home.status.set(
                self.tr("Last time something was interrupted. Your photos are safe: I'll fix it."),
                "warning",
                self.tr("Fix"),
                self.recover,
            )
        elif result.issues:
            home.status.set(
                self.tr("I found %n thing(s) to sort out on the disks.", "", len(result.issues)),
                "warning",
                self.tr("Let's look together"),
                lambda: self.check_disks(quick_now=True),
            )
        elif result.errors:
            home.status.set(
                self.tr("Some files can't be read. Run a check of the disks."),
                "warning",
                self.tr("Check"),
                lambda: self.check_disks(quick_now=True),
            )
        else:
            home.status.set(self.tr("Your photos are safe on both disks."), "safe")
        # Disks may have changed while checking
        self.on_changed()

    def recover(self) -> None:
        disks = list(self.disks)
        self.window.reset(BusyScreen(self.tr("I'm finishing what was interrupted…")))
        self.mode = CHECKING
        self.run(lambda **kw: status.recover(disks, **kw), lambda _: self.run_startup_check())

    # Preparing new disks

    def prepare(self) -> None:
        self.busy = True
        self.mode = PREPARE
        flow = PrepareFlow(self.window, self.session, self)
        flow.finished.connect(self._prepared)
        flow.start()

    def _prepared(self, done: bool) -> None:
        self.busy = False
        self.mode = ""
        self.on_changed()

    # Adding photos

    def add_photos(self) -> None:
        self.busy = True
        self.mode = ADD
        flow = AddPhotosFlow(self.window, list(self.disks), self.run, self)
        flow.finished.connect(self._flow_finished)
        flow.start()

    def _flow_finished(self) -> None:
        """Back from a flow that may have changed the disks: check again, then home."""
        self.busy = False
        self.mode = ""
        self.on_changed()

    # Checking the disks

    def check_disks(self, quick_now: bool = False) -> None:
        self.busy = True
        self.mode = CHECK
        size = self.startup.size if self.startup else 0
        flow = CheckFlow(self.window, list(self.disks), self.run, size, self)
        flow.finished.connect(self._flow_finished)
        flow.start(quick_now=quick_now)

    # Viewer

    def show_viewer(self) -> ViewerScreen:
        disks = list(self.disks)
        with Archive.open(disks) as archive:
            records = list(archive.index.files())
        folders = {f for disk in disks for f in browse.disk_folders(disk.archive)}
        root = browse.build_tree(records, sorted(folders))
        self._home()
        return self.window.open(ViewerScreen(root, [disk.archive for disk in disks]))

    # History and trash

    def show_history(self) -> None:
        with Archive.open(list(self.disks)) as archive:
            events = archive.index.events()
            labels = {d.id: d.label for d in archive.index.disks()}
        self._home()
        self.window.open(HistoryScreen(events, labels))
        self._update_menu()

    def show_trash(self, replace: bool = False) -> None:
        with Archive.open(list(self.disks)) as archive:
            entries = archive.index.trash()
        screen = TrashScreen(entries, self.session.assessment.situation == detect.COMPLETE)
        screen.restore_requested.connect(self._restore)
        screen.empty_requested.connect(self._empty_trash)
        if replace:
            self.window.replace(screen)
        else:
            self._home()
            self.window.open(screen)

    def _restore(self, files) -> None:
        problems = []
        with Archive.open(list(self.disks)) as archive:
            for file in files:
                for entry in file.entries:
                    try:
                        trash.restore(archive, entry)
                    except OSError as error:
                        problems.append(f"{file.path}: {error.strerror or error}")
            archive.sync_indexes()
        self.show_trash(replace=True)
        if problems:
            self.window.current.body.insertWidget(
                0,
                Banner(
                    self.tr(
                        "Some photos could not be restored: "
                        "a photo with the same name is already there."
                    ),
                    "warning",
                ),
            )

    def _empty_trash(self) -> None:
        with Archive.open(list(self.disks)) as archive:
            trash.empty(archive)
            archive.sync_indexes()
        self.show_trash(replace=True)

    # Read-only

    def open_read_only(self) -> None:
        self.mode = READ_ONLY
        self._show_read_only()

    def _show_read_only(self) -> None:
        home = self._home()
        home.set_read_only(True)
        assessment = self.session.assessment
        here = ", ".join(disk_name(d.label) for d in assessment.disks)
        missing = ", ".join(disk_name(label) for label in assessment.missing)
        home.status.set(
            self.tr("You are looking at Disk %1 only. To add photos, connect Disk %2 too.")
            .replace("%1", here)
            .replace("%2", missing),
            "warning",
        )

    def _home(self) -> HomeScreen:
        screen = self.window.current
        if not isinstance(screen, HomeScreen) or self.window.stack.count() != 1:
            screen = self.window.reset(HomeScreen())
            screen.add_requested.connect(self.add_photos)
            screen.browse_requested.connect(self.show_viewer)
            screen.check_requested.connect(self.check_disks)
        return screen

    # Finishing

    def finish(self) -> None:
        for worker in list(self._workers):
            worker.cancel()
            worker.wait(5000)
        self.session.stop()
        self.mode = DONE
        self.window.reset(DoneScreen())

    # Background work

    def run(self, job, on_success, on_progress=None, on_failure=None) -> Worker:
        worker = Worker(job, self)
        self._workers.add(worker)
        if on_progress is not None:
            worker.progress.connect(on_progress)
        worker.succeeded.connect(on_success)
        worker.failed.connect(on_failure or self._show_failure)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()
        return worker

    def _show_failure(self, message: str) -> None:
        self.mode = HOME
        home = self._home()
        home.status.set(
            self.tr("Something went wrong, your photos were not touched: %1").replace(
                "%1", message
            ),
            "danger",
        )
