"""'Look at your photos': folders on the left, thumbnails on the right.

Built from the index, so it works with one disk only. Folders are shown in the grid too,
as big tiles: double click to open a folder or to see a photo full screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QListView,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from ..core import scanner
from ..core.browse import Folder, folder_problems
from ..core.disk import Disk
from ..core.index import FileRecord
from . import theme
from .screen import Screen
from .session import disk_name
from .thumbnails import ThumbnailLoader

CELL = 200  # pixels, the side of a tile
GAP = 12
ROLE_ENTRY = Qt.ItemDataRole.UserRole + 1
ROLE_PROBLEM = Qt.ItemDataRole.UserRole + 2  # text of the problem, or None
BADGE = 30


@dataclass(frozen=True)
class Entry:
    folder: Folder | None = None
    record: FileRecord | None = None

    @property
    def name(self) -> str:
        if self.folder is not None:
            return self.folder.name
        return self.record.path.rsplit("/", 1)[-1]


class ProblemTexts(QObject):
    """Badges in words: what is wrong with a photo or a folder."""

    def file(self, problems: dict[str, str], labels: dict[str, str]) -> str:
        lines = []
        for disk_id, kind in sorted(problems.items(), key=lambda p: labels.get(p[0], "")):
            disk = self.tr("Disk %1").replace("%1", disk_name(labels.get(disk_id, "?")))
            text = {
                "missing": self.tr("Missing on %1"),
                "corrupt": self.tr("Damaged on %1"),
                "modified": self.tr("Changed on %1"),
            }.get(kind, self.tr("Something is wrong on %1"))
            lines.append(text.replace("%1", disk))
        return "\n".join(lines) + "\n" + self.tr("Check the disks to sort it out.")

    def folder(self, count: int) -> str:
        return self.tr("%n photo(s) here need attention. Check the disks.", "", count)


class GridModel(QAbstractListModel):
    def __init__(
        self,
        loader: ThumbnailLoader,
        problems: dict[str, dict[str, str]] | None = None,
        labels: dict[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.loader = loader
        self.problems = problems or {}
        self.folder_problems = folder_problems(self.problems)
        self.labels = labels or {}
        self.texts = ProblemTexts(self)
        self.entries: list[Entry] = []
        self._rows: dict[str, list[int]] = {}
        loader.ready.connect(self._thumbnail_ready)

    def show_folder(self, folder: Folder) -> None:
        self.beginResetModel()
        self.entries = [Entry(folder=child) for child in folder.children()]
        self.entries += [Entry(record=record) for record in folder.files]
        self._rows = {}
        for row, entry in enumerate(self.entries):
            if entry.record is not None:
                self._rows.setdefault(entry.record.hash, []).append(row)
        self.endResetModel()

    def rowCount(self, parent=None) -> int:  # noqa: N802 (Qt)
        return 0 if parent is not None and parent.isValid() else len(self.entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        entry = self.entries[index.row()]
        if role == ROLE_ENTRY:
            return entry
        if role == ROLE_PROBLEM:
            return self._problem(entry)
        if role == Qt.ItemDataRole.ToolTipRole:
            problem = self._problem(entry)
            return f"{entry.name}\n\n{problem}" if problem else entry.name
        if role == Qt.ItemDataRole.DecorationRole and entry.record is not None:
            pixmap = self.loader.get(entry.record.hash)
            if pixmap is None and scanner.kind_of(entry.name) != scanner.VIDEO:
                self.loader.request(entry.record.hash, entry.record.path)
            return pixmap
        return None

    def _problem(self, entry: Entry) -> str | None:
        if entry.folder is not None:
            count = self.folder_problems.get(entry.folder.path, 0)
            return self.texts.folder(count) if count else None
        problems = self.problems.get(entry.record.path)
        return self.texts.file(problems, self.labels) if problems else None

    def _thumbnail_ready(self, key: str) -> None:
        for row in self._rows.get(key, []):
            index = self.index(row)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DecorationRole])


class TileDelegate(QStyledItemDelegate):
    """Draws a tile: the thumbnail, or a folder with its name and number of photos."""

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 (Qt)
        return QSize(CELL, CELL)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        entry: Entry = index.data(ROLE_ENTRY)
        rect = option.rect.adjusted(GAP // 2, GAP // 2, -GAP // 2, -GAP // 2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.SURFACE_2 if hover or selected else theme.SURFACE)
        painter.drawRoundedRect(rect, theme.RADIUS, theme.RADIUS)

        if entry.folder is not None:
            self._paint_folder(painter, rect, entry.folder)
        else:
            pixmap = index.data(Qt.ItemDataRole.DecorationRole)
            if pixmap is not None:
                inner = rect.adjusted(6, 6, -6, -6)
                scaled = pixmap.scaled(
                    inner.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = rect.x() + (rect.width() - scaled.width()) // 2
                y = rect.y() + (rect.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                self._paint_placeholder(painter, rect, entry)

        if index.data(ROLE_PROBLEM):
            badge = QRect(rect.right() - BADGE - 6, rect.y() + 6, BADGE, BADGE)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.BG)
            painter.drawEllipse(badge)
            theme.icon("triangle-alert", theme.WARNING).paint(painter, badge.adjusted(5, 4, -5, -6))

        if selected:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(theme.ACCENT, 3))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), theme.RADIUS, theme.RADIUS)
        painter.restore()

    def _paint_folder(self, painter: QPainter, rect: QRect, folder: Folder) -> None:
        icon = theme.icon("folder", theme.ACCENT_HOVER)
        icon.paint(painter, QRect(rect.center().x() - 36, rect.y() + 28, 72, 72))
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(theme.TEXT)
        text_rect = QRect(rect.x() + 8, rect.y() + 108, rect.width() - 16, 44)
        flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
        painter.drawText(text_rect, int(flags), folder.name)
        painter.setFont(QFont(painter.font().family(), round(painter.font().pointSizeF() * 0.85)))
        painter.setPen(theme.TEXT_MUTED)
        count_rect = QRect(rect.x() + 8, rect.bottom() - 30, rect.width() - 16, 24)
        painter.drawText(
            count_rect, int(Qt.AlignmentFlag.AlignCenter), self.tr("%n photo(s)", "", folder.count)
        )

    def _paint_placeholder(self, painter: QPainter, rect: QRect, entry: Entry) -> None:
        video = scanner.kind_of(entry.name) == scanner.VIDEO
        icon = theme.icon("film" if video else "image", theme.TEXT_FAINT)
        icon.paint(painter, QRect(rect.center().x() - 28, rect.center().y() - 40, 56, 56))
        painter.setPen(theme.TEXT_MUTED if video else QColor(theme.TEXT_FAINT))
        name_rect = QRect(rect.x() + 8, rect.center().y() + 24, rect.width() - 16, 40)
        flags = (
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWrapAnywhere
        )
        painter.drawText(name_rect, int(flags), entry.name)


class ViewerScreen(Screen):
    """Folders and thumbnails. ``open_requested(records, row)``: show a photo full screen."""

    open_requested = Signal(list, int)

    def __init__(
        self,
        root: Folder,
        disks: list[Disk],
        problems: dict[str, dict[str, str]] | None = None,
        labels: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(self.tr("Your photos"), parent=parent)
        self.root = root
        self.disks = disks
        self.archives = [disk.archive for disk in disks]
        self.loader = ThumbnailLoader(self._sources, [disk.data_dir for disk in disks], self)

        splitter = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setMinimumWidth(240)
        self._items: dict[str, QTreeWidgetItem] = {}
        top = QTreeWidgetItem([self.tr("All your photos"), str(root.count)])
        top.setData(0, Qt.ItemDataRole.UserRole, "")
        top.setIcon(0, theme.icon("images", theme.ACCENT_HOVER))
        self.tree.addTopLevelItem(top)
        self._items[""] = top
        self._fill(top, root)
        top.setExpanded(True)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.currentItemChanged.connect(self._folder_chosen)
        splitter.addWidget(self.tree)

        self.model = GridModel(self.loader, problems, labels, self)
        counts = self.model.folder_problems
        for path, item in self._items.items():
            if counts.get(path):
                item.setIcon(0, theme.icon("triangle-alert", theme.WARNING))
                item.setToolTip(0, self.model.texts.folder(counts[path]))
        self.grid = QListView()
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setUniformItemSizes(True)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.grid.setGridSize(QSize(CELL, CELL))
        self.grid.setMouseTracking(True)
        self.grid.setModel(self.model)
        self.grid.setObjectName("grid")
        self.grid.setItemDelegate(TileDelegate(self.grid))
        self.grid.doubleClicked.connect(self._open)
        splitter.addWidget(self.grid)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 800])
        self.body.addWidget(splitter, 1)
        self.tree.setCurrentItem(top)

    def _fill(self, parent: QTreeWidgetItem, folder: Folder) -> None:
        for child in folder.children():
            item = QTreeWidgetItem([child.name, str(child.count)])
            item.setData(0, Qt.ItemDataRole.UserRole, child.path)
            item.setIcon(0, theme.icon("folder", theme.TEXT_MUTED))
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
            parent.addChild(item)
            self._items[child.path] = item
            self._fill(item, child)

    @property
    def folder(self) -> Folder:
        item = self.tree.currentItem()
        path = item.data(0, Qt.ItemDataRole.UserRole) if item else ""
        return self.root.find(path) or self.root

    def show_folder(self, path: str) -> None:
        item = self._items.get(path)
        if item is not None:
            self.tree.setCurrentItem(item)

    def _folder_chosen(self) -> None:
        folder = self.folder
        self.set_texts(folder.name or self.tr("Your photos"))
        self.model.show_folder(folder)

    def _open(self, index: QModelIndex) -> None:
        entry: Entry = index.data(ROLE_ENTRY)
        if entry.folder is not None:
            self.show_folder(entry.folder.path)
            return
        records = [e.record for e in self.model.entries if e.record is not None]
        self.open_requested.emit(records, records.index(entry.record))

    def _sources(self, key: str, path: str) -> list[Path]:
        parts = path.split("/")
        return [archive.joinpath(*parts) for archive in self.archives]
