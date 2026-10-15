"""'History' and 'Trash', from the "More" menu."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from PySide6.QtCore import QDateTime, QLocale, QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from ..core import trash
from ..core.index import Event, TrashEntry
from . import format as fmt
from . import theme
from .screen import Banner, Screen
from .session import disk_name

# Events told in the history; the others are details of these (one per file, …)
HIDDEN = {"upload", "full_check_started", "trashed"}


@dataclass
class Line:
    at: str  # ISO date of the most recent event of the line
    kind: str
    count: int
    event: Event


def history_lines(events: list[Event]) -> list[Line]:
    """Most recent first; consecutive events of the same kind become one line."""
    lines: list[Line] = []
    for event in events:
        if event.kind in HIDDEN:
            continue
        if (
            lines
            and lines[-1].kind == event.kind
            and event.kind not in ("upload_done", "full_check_done")
        ):
            lines[-1].count += 1
            continue
        lines.append(Line(event.at, event.kind, 1, event))
    return lines


def local_time(iso: str) -> str:
    when = QDateTime.fromString(iso, Qt.DateFormat.ISODate).toLocalTime()
    return QLocale().toString(when, QLocale.FormatType.ShortFormat)


class Texts(QObject):
    def line(self, line: Line, labels: dict[str, str]) -> str:
        n, detail = line.count, line.event.detail
        kind = line.kind
        if kind == "archive_created":
            return self.tr("You prepared Disk 1")
        if kind == "disk_added":
            label = labels.get(line.event.disk_id or "", detail.get("label", "?"))
            return self.tr("You prepared Disk %1").replace("%1", disk_name(label))
        if kind == "upload_done":
            text = self.tr("Added %n photo(s)", "", detail.get("copied", 0))
            if not detail.get("complete", True):
                text += " " + self.tr("(stopped before the end)")
            return text
        if kind == "full_check_done":
            found = detail.get("differences", 0)
            if found:
                return self.tr("Thorough check: %n thing(s) to sort out", "", found)
            return self.tr("Thorough check: all good")
        texts = {
            "repaired": self.tr("Repaired %n photo(s)", "", n),
            "deleted": self.tr("Deleted %n photo(s) (to the trash)", "", n),
            "forgotten": self.tr("Removed %n photo(s) from the list", "", n),
            "updated": self.tr("Kept the new version of %n photo(s)", "", n),
            "accepted": self.tr("Accepted %n change(s) made without the app", "", n),
            "moved": self.tr("Moved %n photo(s)", "", n),
            "move_undone": self.tr("Put back %n photo(s) where they were", "", n),
            "added": self.tr("Added %n photo(s) found on the disks", "", n),
            "marked_known": self.tr("%n problem(s) marked as known", "", n),
            "restored": self.tr("Restored %n file(s) from the trash", "", n),
            "trash_emptied": self.tr("Emptied the trash (%n file(s))", "", detail.get("files", n)),
            "recovered": self.tr("Finished %n interrupted operation(s)", "", n),
        }
        return texts.get(kind, kind)


class HistoryScreen(Screen):
    def __init__(self, events: list[Event], labels: dict[str, str], parent: QWidget | None = None):
        super().__init__(
            self.tr("History"),
            self.tr("Everything done on your photos, most recent first."),
            parent,
        )
        texts = Texts(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setRootIsDecorated(False)
        for line in history_lines(events):
            item = QTreeWidgetItem([local_time(line.at), texts.line(line, labels)])
            self.tree.addTopLevelItem(item)
        self.tree.resizeColumnToContents(0)
        self.body.addWidget(self.tree, 1)
        if not self.tree.topLevelItemCount():
            self.tree.hide()
            self.body.addWidget(theme.set_role(QLabel(self.tr("Nothing yet.")), "muted"))
            self.body.addStretch(1)


@dataclass
class TrashedFile:
    path: str
    entries: list[TrashEntry]

    @property
    def trashed_at(self) -> str:
        return max(e.trashed_at for e in self.entries)


def trashed_files(entries: list[TrashEntry]) -> list[TrashedFile]:
    """One line per file, whatever the number of disks it was trashed on."""
    by_path: dict[str, list[TrashEntry]] = defaultdict(list)
    for entry in entries:
        by_path[entry.path].append(entry)
    files = [TrashedFile(path, items) for path, items in by_path.items()]
    return sorted(files, key=lambda f: f.trashed_at, reverse=True)


def days_left(trashed_at: str, days: int, now: datetime | None = None) -> int:
    age = (now or datetime.now(UTC)) - datetime.fromisoformat(trashed_at)
    return max(0, days - age.days)


class TrashScreen(Screen):
    restore_requested = Signal(list)  # TrashedFile list
    empty_requested = Signal()

    def __init__(self, entries: list[TrashEntry], can_change: bool, parent: QWidget | None = None):
        super().__init__(
            self.tr("Trash"),
            self.tr(
                "Photos deleted or replaced by the app. They are deleted for good after %n day(s).",
                "",
                trash.DEFAULT_DAYS,
            ),
            parent,
        )
        self.files = trashed_files(entries)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            [
                self.tr("Photo"),
                self.tr("Folder"),
                self.tr("Deleted"),
                self.tr("Deleted for good in"),
            ]
        )
        self.tree.setRootIsDecorated(False)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        for file in self.files:
            folder, _, name = file.path.rpartition("/")
            left = days_left(file.trashed_at, trash.DEFAULT_DAYS)
            item = QTreeWidgetItem(
                [
                    name,
                    folder.replace("/", " › "),
                    local_time(file.trashed_at),
                    self.tr("%n day(s)", "", left),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, file.path)
            self.tree.addTopLevelItem(item)
        for column in range(4):
            self.tree.resizeColumnToContents(column)
        self.body.addWidget(self.tree, 1)
        size = sum(e.size for e in entries)
        info = theme.set_role(
            QLabel(self.tr("%n file(s)", "", len(self.files)) + "  ·  " + fmt.size(size)), "muted"
        )
        self.body.addWidget(info)
        if not can_change:
            self.body.addWidget(
                Banner(
                    self.tr("Connect both disks to restore photos or empty the trash."), "warning"
                )
            )
        self.restore = self.add_secondary(self.tr("Restore"), self._restore)
        self.restore.setEnabled(False)
        self.empty_button = theme.set_role(
            self.add_secondary(self.tr("Empty the trash"), self._empty), "danger"
        )
        self.empty_button.setEnabled(can_change and bool(self.files))
        self.tree.itemSelectionChanged.connect(
            lambda: self.restore.setEnabled(can_change and bool(self.tree.selectedItems()))
        )

    def _restore(self) -> None:
        chosen = {item.data(0, Qt.ItemDataRole.UserRole) for item in self.tree.selectedItems()}
        self.restore_requested.emit([f for f in self.files if f.path in chosen])

    def _empty(self) -> None:
        if self.confirm_empty():
            self.empty_requested.emit()

    def confirm_empty(self) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.tr("Empty the trash"))
        box.setText(
            self.tr("Delete for good %n file(s)? This can't be undone.", "", len(self.files))
        )
        agree = QCheckBox(self.tr("Yes, delete them for good"))
        box.setCheckBox(agree)
        delete = box.addButton(self.tr("Delete for good"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        delete.setEnabled(False)
        agree.toggled.connect(delete.setEnabled)
        box.exec()
        return box.clickedButton() is delete
