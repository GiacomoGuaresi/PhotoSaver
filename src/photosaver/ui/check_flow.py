"""'Check the disks': quick or thorough check, what was found in plain words, fix it.

Steps: choose the check → checking → results, grouped, with the obvious action already
chosen → fixing → a new quick check, to show that everything is fine.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core import check, resolve
from ..core.archive import Archive
from ..core.disk import Disk
from . import format as fmt
from . import theme
from .connect import BusyScreen
from .issues import Group, Texts, group_issues
from .main_window import MainWindow
from .screen import Banner, Screen

READ_SPEED = 100_000_000  # bytes per second, a USB hard disk (disks are read in parallel)
SHOWN_FILES = 20


class ChooseCheckScreen(Screen):
    def __init__(self, archive_size: int, parent: QWidget | None = None):
        super().__init__(
            self.tr("Check the disks"),
            self.tr("Which check do you want to do?"),
            parent,
        )
        self.group = QButtonGroup(self)
        self.quick = self._choice(
            self.tr("Quick check"),
            self.tr("A few seconds. Finds photos that are missing, added or moved."),
        )
        self.full = self._choice(
            self.tr("Thorough check"),
            self.tr(
                "%1. Reads every photo again to find the ones that got damaged. "
                "You can stop it and go on another time."
            ).replace("%1", fmt.duration(archive_size / READ_SPEED).capitalize()),
        )
        self.quick.setChecked(True)
        self.body.addStretch(1)
        self.set_primary(self.tr("Start the check"))

    def _choice(self, title: str, text: str) -> QRadioButton:
        button = theme.set_role(QRadioButton(f"{title}\n{text}"), "choice")
        button.setIconSize(QSize(32, 32))
        self.group.addButton(button)
        self.body.addWidget(button)
        return button


class GroupRow(QFrame):
    """One group of problems: what happened, what to do, which photos."""

    changed = Signal()

    def __init__(self, group: Group, all_labels: list[str], parent: QWidget | None = None):
        super().__init__(parent, objectName="card")
        self.group = group
        texts = Texts(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        title = theme.set_role(QLabel(texts.title(group, all_labels)), "heading")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.choice = QComboBox()
        if group.proposed is None:
            self.choice.addItem(self.tr("Choose what to do…"), None)
        for option in group.options:
            self.choice.addItem(texts.option(group, option, all_labels), option)
        if group.proposed is not None:
            self.choice.setCurrentIndex(group.options.index(group.proposed))
        self.choice.currentIndexChanged.connect(self._chosen)
        layout.addWidget(self.choice)

        paths = [issue.path for issue in group.issues]
        self.files = theme.set_role(QLabel(self._list(paths)), "muted")
        self.files.setWordWrap(True)
        self.files.hide()
        self.toggle = theme.set_role(QPushButton(self.tr("Show the photos")), "link")
        self.toggle.clicked.connect(self._toggle)
        layout.addWidget(self.toggle)
        layout.addWidget(self.files)

    def _list(self, paths: list[str]) -> str:
        shown = [path.replace("/", " › ") for path in paths[:SHOWN_FILES]]
        if len(paths) > SHOWN_FILES:
            shown.append(self.tr("… and %n more", "", len(paths) - SHOWN_FILES))
        return "\n".join(shown)

    def _toggle(self) -> None:
        self.files.setVisible(self.files.isHidden())
        self.toggle.setText(
            self.tr("Hide the photos") if self.files.isVisible() else self.tr("Show the photos")
        )

    def _chosen(self) -> None:
        self.group.choice = self.choice.currentData()
        self.changed.emit()


class ResultsScreen(Screen):
    def __init__(
        self,
        groups: list[Group],
        all_labels: list[str],
        report: check.Report,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.groups = groups
        self.rows: list[GroupRow] = []
        if not groups:
            self.set_texts(self.tr("All good!"))
            self.body.addWidget(Banner(self.tr("Your photos are safe on both disks."), "safe"))
        else:
            self.set_texts(
                self.tr("I found something to sort out"),
                self.tr(
                    "For each line I've already chosen what to do when it's obvious. "
                    "Check, then press the button."
                ),
            )
            scroll = QScrollArea(widgetResizable=True)
            content = QWidget()
            rows = QVBoxLayout(content)
            rows.setContentsMargins(0, 0, 8, 0)
            rows.setSpacing(12)
            for group in groups:
                row = GroupRow(group, all_labels)
                row.changed.connect(self.refresh)
                rows.addWidget(row)
                self.rows.append(row)
            rows.addStretch(1)
            scroll.setWidget(content)
            self.body.addWidget(scroll, 1)
        if report.errors:
            self.body.addWidget(
                Banner(
                    self.tr(
                        "%n file(s) or folder(s) can't be read. If it happens again, the disk "
                        "may be failing: copy your photos to a new disk soon.",
                        "",
                        len(report.errors),
                    ),
                    "danger",
                )
            )
        if report.known:
            note = theme.set_role(
                QLabel(self.tr("%n known problem(s) not shown.", "", report.known)), "muted"
            )
            self.body.addWidget(note)
        self.undecided = theme.set_role(
            QLabel(self.tr("The lines without a choice stay as they are.")), "muted"
        )
        self.body.addWidget(self.undecided)
        if not groups:
            self.body.addStretch(1)
        self.set_primary("")
        self.refresh()

    def refresh(self) -> None:
        if not self.groups:
            self.primary.setText(self.tr("Back to the start"))
            self.undecided.hide()
            return
        chosen = sum(len(g.issues) for g in self.groups if g.choice is not None)
        self.primary.setText(self.tr("Sort out %n thing(s)", "", chosen))
        self.primary.setEnabled(chosen > 0)
        self.undecided.setVisible(any(g.choice is None for g in self.groups))


class CheckFlow(QObject):
    finished = Signal()

    def __init__(
        self,
        window: MainWindow,
        disks: list[Disk],
        run,
        archive_size: int = 0,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.window = window
        self.disks = disks
        self.run = run
        self.archive_size = archive_size
        self.worker = None
        self.labels = {disk.id: disk.label for disk in disks}
        self.all_labels = sorted(self.labels.values())

    def start(self, *, quick_now: bool = False) -> None:
        if quick_now:
            self._check(full=False, first=True)
            return
        choose = self.window.open(ChooseCheckScreen(self.archive_size))
        choose.back_requested.connect(self.finished)
        choose.primary.clicked.connect(lambda: self._check(full=choose.full.isChecked()))

    def _check(self, full: bool, first: bool = False) -> None:
        disks = self.disks
        if full:
            busy = BusyScreen(
                self.tr("I'm reading every photo…"),
                self.tr(
                    "You can wait calmly, or stop and go on another time: "
                    "I'll start again from here."
                ),
            )
        else:
            busy = BusyScreen(self.tr("I'm checking the disks…"))
        if first:
            self.window.open(busy)
        else:
            self.window.replace(busy)
        busy.set_back(False)
        eta = fmt.Eta(time.monotonic)
        if full:
            busy.add_secondary(self.tr("Stop"), lambda: self.worker and self.worker.cancel())

        def job(on_progress, should_stop):
            with Archive.open(disks) as archive:
                run = check.full_check if full else check.quick_check
                report = run(archive, on_progress=on_progress, should_stop=should_stop)
                return report, resolve.build_issues(report, archive)

        def progress(done, total):
            if not full:
                busy.set_progress(done, total)
                return
            detail = fmt.size(done) + " / " + fmt.size(total)
            left = eta.left(done, total)
            if left is not None:
                detail += "  ·  " + self.tr("%1 left").replace("%1", fmt.duration(left))
            busy.set_progress(done, total, detail)

        self.worker = self.run(job, self._results, progress, self._failed)
        self.worker.cancelled.connect(self._stopped)

    def _results(self, result) -> None:
        report, issues = result
        groups = group_issues(issues, self.labels)
        screen = ResultsScreen(groups, self.all_labels, report)
        self.window.replace(screen)
        screen.set_back(False)
        if groups:
            screen.add_secondary(self.tr("Not now"), self.finished.emit)
            screen.primary.clicked.connect(lambda: self._fix(groups))
        else:
            screen.primary.clicked.connect(self.finished.emit)

    def _fix(self, groups: list[Group]) -> None:
        for group in groups:
            group.apply_choice()
        issues = [issue for group in groups for issue in group.issues]
        disks = self.disks
        busy = BusyScreen(self.tr("I'm sorting things out…"))
        self.window.replace(busy)
        busy.set_back(False)

        def job(on_progress, should_stop):
            with Archive.open(disks) as archive:
                return resolve.apply(
                    issues, archive, on_progress=on_progress, should_stop=should_stop
                )

        self.worker = self.run(job, self._fixed, busy.set_progress, self._failed)

    def _fixed(self, outcome: resolve.Outcome) -> None:
        if outcome.failed:
            screen = Screen(
                self.tr("Almost done"),
                self.tr(
                    "%n thing(s) could not be sorted out. "
                    "Check that both disks are connected and try again.",
                    "",
                    len(outcome.failed),
                ),
            )
            self.window.replace(screen)
            screen.set_back(False)
            screen.set_primary(self.tr("Check again"), lambda: self._check(full=False))
            return
        self._check(full=False)

    def _stopped(self) -> None:
        screen = Screen(
            self.tr("Check stopped"),
            self.tr("Next time the thorough check starts again from where it stopped."),
        )
        self.window.replace(screen)
        screen.set_back(False)
        screen.set_primary(self.tr("OK"), self.finished.emit)

    def _failed(self, message: str) -> None:
        screen = Screen(
            self.tr("Something went wrong"),
            self.tr("%1\n\nCheck that both disks are connected, then try again.").replace(
                "%1", message
            ),
        )
        self.window.replace(screen)
        screen.set_back(False)
        screen.set_primary(self.tr("OK"), self.finished.emit)
