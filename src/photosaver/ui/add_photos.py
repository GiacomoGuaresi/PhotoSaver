"""'Add photos': folders from the computer, copied and verified on both disks.

Steps: choose the folders → looking at the photos (analysis) → what will happen (where
they go, what is already there) → copying → done, and maybe delete the originals.
"""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core import scanner, upload
from ..core.archive import Archive
from ..core.disk import Disk
from . import format as fmt
from . import theme
from .connect import BusyScreen
from .main_window import MainWindow
from .screen import Banner, Screen


class ChooseFoldersScreen(Screen):
    """Pick one or more folders, with a button or by dropping them on the window."""

    def __init__(self, forbidden: list[Path] = (), parent: QWidget | None = None):
        super().__init__(
            self.tr("Add photos"),
            self.tr("Choose the folders with the photos to add. You can also drag them here."),
            parent,
        )
        self.setAcceptDrops(True)
        self._forbidden = [p.resolve() for p in forbidden]
        self.pick = QPushButton(theme.icon("folder-plus"), self.tr("Choose a folder…"))
        self.pick.setIconSize(QSize(28, 28))
        self.pick.setMinimumHeight(64)
        self.pick.clicked.connect(self._choose)
        self.body.addWidget(self.pick)
        self.list = QListWidget()
        self.list.setIconSize(QSize(24, 24))
        self.body.addWidget(self.list, 1)
        self.warning = Banner(
            self.tr("This folder is already on the photo disks: choose one on the computer."),
            "warning",
        )
        self.warning.hide()
        self.body.addWidget(self.warning)
        self.remove = QPushButton(theme.icon("x"), self.tr("Remove from the list"))
        self.remove.clicked.connect(self._remove_selected)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.remove)
        self.body.addLayout(row)
        self.set_primary(self.tr("Next"))
        self._update()

    @property
    def folders(self) -> list[Path]:
        return [
            Path(self.list.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.list.count())
        ]

    def add_folder(self, folder: Path) -> None:
        if not folder.is_dir() or folder in self.folders:
            return
        resolved = folder.resolve()
        if any(
            resolved == f or f in resolved.parents or resolved in f.parents for f in self._forbidden
        ):
            self.warning.show()
            return
        self.warning.hide()
        item = QListWidgetItem(theme.icon("folder-open"), folder.name)
        item.setToolTip(str(folder))
        item.setData(Qt.ItemDataRole.UserRole, str(folder))
        self.list.addItem(item)
        self._update()

    def _choose(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder of photos"))
        if folder:
            self.add_folder(Path(folder))

    def _remove_selected(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self._update()

    def _update(self) -> None:
        self.primary.setEnabled(self.list.count() > 0)
        self.remove.setVisible(self.list.count() > 0)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.add_folder(Path(url.toLocalFile()))


class DestinationDialog(QDialog):
    """Where a folder goes: the year folder (existing or new) and the folder name."""

    def __init__(self, destination: str, top_level: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Where do you want to put these photos?"))
        self.setMinimumWidth(520)
        year, _, name = destination.rpartition("/")
        form = QFormLayout(self)
        self.year = QComboBox(editable=True)
        self.year.addItems(top_level)
        self.year.setCurrentText(year)
        self.name = QLineEdit(name)
        form.addRow(self.tr("In the folder:"), self.year)
        form.addRow(self.tr("With the name:"), self.name)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @property
    def destination(self) -> str:
        parts = [self.year.currentText().strip(" /"), self.name.text().strip(" /")]
        return "/".join(part for part in parts if part)


class FolderCard(QFrame):
    """What will happen to one uploaded folder."""

    change_requested = Signal(object)  # the upload.Folder

    def __init__(self, folder: upload.Folder, parent: QWidget | None = None):
        super().__init__(parent, objectName="card")
        self.folder = folder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        kinds = Counter(item.kind for item in folder.items)
        photos = kinds[scanner.PHOTO] + kinds[scanner.RAW]
        title = theme.set_role(QLabel(folder.source.name), "heading")
        counts = theme.set_role(
            QLabel(
                " · ".join(
                    [
                        self.tr("%n photo(s)", "", photos),
                        *(
                            [self.tr("%n video(s)", "", kinds[scanner.VIDEO])]
                            if kinds[scanner.VIDEO]
                            else []
                        ),
                        fmt.size(sum(item.size for item in folder.items)),
                    ]
                )
            ),
            "muted",
        )
        head = QHBoxLayout()
        head.addWidget(title)
        head.addWidget(counts, 1)
        layout.addLayout(head)

        where = QHBoxLayout()
        self.destination = QLabel()
        self.destination.setWordWrap(True)
        where.addWidget(self.destination, 1)
        change = QPushButton(self.tr("Change"))
        change.clicked.connect(lambda: self.change_requested.emit(self.folder))
        where.addWidget(change)
        layout.addLayout(where)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        theme.set_role(self.notes, "muted")
        layout.addWidget(self.notes)
        self.refresh()

    def refresh(self) -> None:
        folder = self.folder
        place = folder.destination.replace("/", " › ") if folder.destination else ""
        self.destination.setText(
            self.tr("They will go in: <b>%1</b>").replace("%1", place)
            if place
            else self.tr("They will go in your photos as they are, with their folders.")
        )
        statuses = Counter(item.status for item in folder.items)
        copied_duplicates = sum(
            1 for i in folder.items if i.status == upload.DUPLICATE and i.copied
        )
        notes = []
        if statuses[upload.SAME]:
            notes.append(
                self.tr(
                    "%n photo(s) are already on the disks: I won't copy them again.",
                    "",
                    statuses[upload.SAME],
                )
            )
        if statuses[upload.DUPLICATE] - copied_duplicates:
            notes.append(
                self.tr(
                    "%n photo(s) are already in your photos in another folder: I'll skip them.",
                    "",
                    statuses[upload.DUPLICATE] - copied_duplicates,
                )
            )
        renamed = sum(1 for i in folder.items if i.action == upload.RENAME)
        if renamed:
            notes.append(
                self.tr(
                    "%n photo(s) have the same name as different photos already there: "
                    "I'll save them with a new name.",
                    "",
                    renamed,
                )
            )
        if folder.ignored:
            notes.append(
                self.tr(
                    "%n file(s) are not photos or videos: they stay where they are.",
                    "",
                    len(folder.ignored),
                )
            )
        if folder.errors:
            notes.append(self.tr("%n file(s) can't be read.", "", len(folder.errors)))
        self.notes.setText("\n".join("• " + note for note in notes))
        self.notes.setVisible(bool(notes))


class PreviewScreen(Screen):
    change_requested = Signal(object)
    duplicates_toggled = Signal(bool)

    def __init__(self, plan: upload.Plan, parent: QWidget | None = None):
        super().__init__(self.tr("Here's what I'll do"), parent=parent)
        self.plan = plan
        scroll = QScrollArea(widgetResizable=True)
        content = QWidget()
        self._cards = QVBoxLayout(content)
        self._cards.setContentsMargins(0, 0, 8, 0)
        self._cards.setSpacing(12)
        self.cards = []
        for folder in plan.folders:
            card = FolderCard(folder)
            card.change_requested.connect(self.change_requested)
            self._cards.addWidget(card)
            self.cards.append(card)
        self._cards.addStretch(1)
        scroll.setWidget(content)
        self.body.addWidget(scroll, 1)
        self.duplicates = QCheckBox(
            self.tr("Copy also the photos that are already in another folder")
        )
        self.duplicates.toggled.connect(self.duplicates_toggled)
        self.body.addWidget(self.duplicates)
        self.nothing = Banner(
            self.tr("There is nothing new to copy: these photos are already safe."), "safe"
        )
        self.body.addWidget(self.nothing)
        self.set_primary("")
        self.refresh()

    def refresh(self) -> None:
        for card in self.cards:
            card.refresh()
        count, size = len(self.plan.to_copy()), self.plan.copy_size
        self.duplicates.setVisible(self.plan.count(upload.DUPLICATE) > 0)
        self.nothing.setVisible(count == 0)
        self.primary.setText(
            self.tr("Copy %n photo(s) to both disks", "", count) + f"  ·  {fmt.size(size)}"
        )
        self.primary.setEnabled(count > 0)


class SummaryScreen(Screen):
    delete_requested = Signal()
    keep_requested = Signal()

    def __init__(self, result: upload.Result, can_delete: bool, parent: QWidget | None = None):
        copied = len(result.copied)
        super().__init__(
            self.tr("Done!") if not result.failed else self.tr("Almost done"),
            self.tr("%n photo(s) are now safe on both disks.", "", copied),
            parent,
        )
        if result.failed:
            failed = Banner(
                self.tr(
                    "%n file(s) could not be copied: they were changed or can't be read. "
                    "They stay on the computer.",
                    "",
                    len(result.failed),
                ),
                "warning",
            )
            self.body.addWidget(failed)
            names = QLabel("\n".join(item.relative for item, _ in result.failed[:10]))
            theme.set_role(names, "muted")
            self.body.addWidget(names)
        if can_delete:
            self.body.addWidget(
                Banner(
                    self.tr(
                        "Do you want to delete the original folders from the computer? "
                        "The photos are already safe on the two disks."
                    ),
                    "safe",
                )
            )
            self.add_secondary(self.tr("Keep them"), self.keep_requested.emit)
            theme.set_role(
                self.set_primary(self.tr("Delete the originals"), self.delete_requested.emit),
                "danger",
            )
        else:
            self.set_primary(self.tr("Done"), self.keep_requested.emit)
        self.body.addStretch(1)


class AddPhotosFlow(QObject):
    """Drives the steps. ``run(job, on_success, on_progress, on_failure)`` runs a job in the
    background (the controller's); ``finished`` when the user is back home."""

    finished = Signal()

    def __init__(self, window: MainWindow, disks: list[Disk], run, parent: QObject | None = None):
        super().__init__(parent)
        self.window = window
        self.disks = disks
        self.run = run
        self.plan: upload.Plan | None = None
        self.worker = None
        self.choose: ChooseFoldersScreen | None = None

    def start(self) -> None:
        self.choose = self.window.open(ChooseFoldersScreen([d.root for d in self.disks]))
        self.choose.back_requested.connect(self.finished)
        self.choose.primary.clicked.connect(self._analyze)

    # Analysis

    def _analyze(self) -> None:
        folders = self.choose.folders
        disks = self.disks
        busy = self.window.open(
            BusyScreen(
                self.tr("I'm looking at the photos…"),
                self.tr("It may take a while with many photos."),
            )
        )
        busy.set_back(False)
        busy.add_secondary(self.tr("Stop"), lambda: self.worker and self.worker.cancel())

        def job(on_progress, should_stop):
            plan = upload.analyze(folders, on_progress=on_progress, should_stop=should_stop)
            with Archive.open(disks) as archive:
                top = upload.top_level_folders(archive)
                for folder in plan.folders:
                    folder.destination = upload.propose_destination(folder, top)
                upload.resolve(plan, archive)
                return plan, top

        def progress(done, total):
            busy.set_progress(done, total, fmt.size(done) + " / " + fmt.size(total))

        self.worker = self.run(job, self._preview, progress, self._failed)
        self.worker.cancelled.connect(self.window.back)

    def _preview(self, result) -> None:
        self.plan, self.top = result
        preview = PreviewScreen(self.plan)
        self.window.replace(preview)
        self.preview = preview
        preview.change_requested.connect(self._change_destination)
        preview.duplicates_toggled.connect(self._toggle_duplicates)
        preview.primary.clicked.connect(self._copy)

    def _change_destination(self, folder: upload.Folder) -> None:
        dialog = DestinationDialog(folder.destination, self.top, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder.destination = dialog.destination
            self._resolve()

    def _toggle_duplicates(self, copy: bool) -> None:
        for item in self.plan.items:
            if item.status == upload.DUPLICATE:
                item.choice = upload.COPY if copy else None
        self._resolve()

    def _resolve(self) -> None:
        with Archive.open(self.disks) as archive:
            upload.resolve(self.plan, archive)
        self.preview.refresh()

    # Copy

    def _copy(self) -> None:
        plan, disks = self.plan, self.disks
        busy = BusyScreen(
            self.tr("I'm copying the photos to both disks…"),
            self.tr(
                "Every photo is checked after copying. You can wait calmly, "
                "or stop and go on another time."
            ),
        )
        self.window.replace(busy)
        busy.set_back(False)
        busy.add_secondary(self.tr("Stop"), lambda: self.worker and self.worker.cancel())
        eta = fmt.Eta(time.monotonic)

        def job(on_progress, should_stop):
            with Archive.open(disks) as archive:
                return upload.apply(plan, archive, on_progress=on_progress, should_stop=should_stop)

        def progress(done, total):
            left = eta.left(done, total)
            detail = fmt.size(done) + " / " + fmt.size(total)
            if left is not None:
                detail += "  ·  " + self.tr("%1 left").replace("%1", fmt.duration(left))
            busy.set_progress(done, total, detail)

        self.worker = self.run(job, self._summary, progress, self._failed)
        self.worker.cancelled.connect(self._stopped)

    def _summary(self, result: upload.Result) -> None:
        can_delete = bool(result.copied or self.plan.count(upload.SAME)) and not result.failed
        summary = SummaryScreen(result, can_delete)
        self.window.replace(summary)
        summary.set_back(False)
        summary.keep_requested.connect(self.finished)
        summary.delete_requested.connect(self._delete_sources)

    def _delete_sources(self) -> None:
        with Archive.open(self.disks) as archive:
            upload.delete_sources(self.plan, archive)
        self.finished.emit()

    def _stopped(self) -> None:
        screen = Screen(
            self.tr("Copy stopped"),
            self.tr(
                "The photos copied so far are safe on both disks. To go on, add the same "
                "folders again: I'll copy only what is missing."
            ),
        )
        self.window.replace(screen)
        screen.set_back(False)
        screen.set_primary(self.tr("OK"), self.finished.emit)

    def _failed(self, message: str) -> None:
        screen = Screen(
            self.tr("Something went wrong"),
            self.tr(
                "%1\n\nCheck that both disks are connected. The photos copied so far are "
                "safe; add the same folders again to go on."
            ).replace("%1", message),
        )
        self.window.replace(screen)
        screen.set_back(False)
        screen.set_primary(self.tr("OK"), self.finished.emit)
