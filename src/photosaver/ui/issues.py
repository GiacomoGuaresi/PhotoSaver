"""Problems found by a check, told in plain words and grouped, so there are few decisions.

The engine has one issue per file. Here issues of the same kind, on the same disks and
with the same possible actions become one group with one choice; moves are grouped by
folder, so a renamed folder is one line ("The folder X was renamed Y on Disk 2").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from PySide6.QtCore import QObject

from ..core import resolve
from ..core.resolve import Issue, Option
from .session import disk_name


@dataclass
class Group:
    kind: str
    issues: list[Issue]
    options: list[Option]
    proposed: Option | None
    bad_disks: list[str]  # labels of the disks with the problem
    labels: dict[str, str]  # disk id → label
    moved: tuple[str, str] | None = None  # (from folder, to folder) for moves
    choice: Option | None = field(default=None)

    def __post_init__(self) -> None:
        self.choice = self.proposed

    def apply_choice(self) -> None:
        for issue in self.issues:
            issue.choice = self.choice


def group_issues(issues: list[Issue], labels: dict[str, str]) -> list[Group]:
    """``labels``: disk id → label (A, B…). Groups to decide first come first."""
    groups: dict[tuple, Group] = {}
    for issue in issues:
        bad = sorted(labels.get(d.disk_id, "?") for d in issue.diffs)
        moved = None
        if issue.kind == resolve.I_MOVED and issue.target:
            moved = (_parent(issue.path), _parent(issue.target))
        key = (issue.kind, tuple(bad), tuple(issue.options), issue.proposed, moved)
        if key not in groups:
            groups[key] = Group(
                issue.kind, [], list(issue.options), issue.proposed, bad, labels, moved
            )
        groups[key].issues.append(issue)
    return sorted(groups.values(), key=lambda g: (g.proposed is not None, g.kind))


def _parent(path: str) -> str:
    parent = PurePosixPath(path).parent
    return "" if str(parent) == "." else str(parent)


class Texts(QObject):
    """The sentences of the check screen (a QObject, for translations)."""

    def disks(self, labels: list[str]) -> str:
        names = [self.tr("Disk %1").replace("%1", disk_name(label)) for label in labels]
        return self.tr(" and ").join(names)

    def title(self, group: Group, all_labels: list[str]) -> str:
        """One sentence for the whole group."""
        n = len(group.issues)
        on = self.disks(group.bad_disks)
        every = len(group.bad_disks) >= len(all_labels)
        kind = group.kind
        if kind == resolve.I_CORRUPT:
            if every:
                return self.tr("%n photo(s) got damaged on both disks", "", n)
            return self.tr("%n photo(s) got damaged on %1", "", n).replace("%1", on)
        if kind == resolve.I_MISSING:
            return self.tr("%n photo(s) are missing on %1", "", n).replace("%1", on)
        if kind == resolve.I_LOST:
            return self.tr("%n photo(s) are missing on both disks", "", n)
        if kind == resolve.I_MODIFIED:
            if every:
                return self.tr("%n photo(s) were changed on both disks", "", n)
            return self.tr("%n photo(s) were changed on %1", "", n).replace("%1", on)
        if kind == resolve.I_MOVED and group.moved:
            old, new = (PurePosixPath(folder) for folder in group.moved)
            if old.name != new.name and old.parent == new.parent:
                return (
                    self.tr("The folder “%1” was renamed “%2” on %3 (%n photo(s))", "", n)
                    .replace("%1", old.name)
                    .replace("%2", new.name)
                    .replace("%3", on)
                )
            main = self.tr("the main folder")
            return (
                self.tr("%n photo(s) were moved from “%1” to “%2” on %3", "", n)
                .replace("%1", group.moved[0].replace("/", " › ") or main)
                .replace("%2", group.moved[1].replace("/", " › ") or main)
                .replace("%3", on)
            )
        if kind == resolve.I_MOVED:
            return self.tr("%n photo(s) were moved on %1", "", n).replace("%1", on)
        if kind == resolve.I_UNTRACKED:
            if every:
                return self.tr("%n photo(s) were added without the app", "", n)
            return self.tr("%n photo(s) were added without the app, only on %1", "", n).replace(
                "%1", on
            )
        return self.tr("%n photo(s) have different problems on the two disks", "", n)

    def option(self, group: Group, option: Option, all_labels: list[str]) -> str:
        """What an action does, in plain words."""
        good = [label for label in all_labels if label not in group.bad_disks]
        others = self.disks(good or all_labels)
        action = option.action
        if action in (resolve.REPAIR, resolve.REVERT):
            if group.kind == resolve.I_MODIFIED:
                return self.tr("Put back the original")
            return self.tr("Repair with the good copy from %1").replace("%1", others)
        if action == resolve.COPY:
            return self.tr("Copy them again from %1").replace("%1", others)
        if action == resolve.DELETE_ALL:
            return self.tr("Delete them from %1 too (they go to the trash)").replace("%1", others)
        if action == resolve.FORGET:
            return self.tr("Remove them from the list of your photos")
        if action == resolve.PROPAGATE:
            source = self.disks([group.labels.get(option.disk_id, "?")])
            return self.tr("Keep the version of %1").replace("%1", source)
        if action == resolve.ACCEPT:
            if group.kind == resolve.I_MOVED:
                return self.tr("That's fine, keep them there")
            return self.tr("Keep the change")
        if action == resolve.REPEAT_MOVE:
            return self.tr("Do the same on %1").replace("%1", others)
        if action == resolve.UNDO_MOVE:
            return self.tr("Put them back where they were")
        if action == resolve.ADD:
            if good:
                return self.tr("Add them to your photos (copy them to %1 too)").replace(
                    "%1", others
                )
            return self.tr("Add them to your photos")
        if action == resolve.DELETE:
            return self.tr("Delete them (they go to the trash)")
        return self.tr("Leave it as it is, don't tell me again")
