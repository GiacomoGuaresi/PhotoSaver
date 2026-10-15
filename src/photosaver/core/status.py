"""What to tell the user when the disks are connected: is everything fine?"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from . import check, edit, resolve, trash
from .archive import Archive
from .disk import Disk


@dataclass
class Startup:
    interrupted: int = 0  # actions left unfinished last time
    issues: list[resolve.Issue] = field(default_factory=list)
    errors: int = 0  # unreadable files or folders
    emptied: int = 0  # files deleted for good from the trash, too old
    files: int = 0
    size: int = 0

    @property
    def safe(self) -> bool:
        return not self.interrupted and not self.issues and not self.errors


def startup_check(
    disks: list[Disk],
    *,
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Startup:
    """Realign the indexes, empty the old files of the trash, run the quick check."""
    with Archive.open(disks) as archive:
        if archive.stale and archive.complete:
            archive.sync_indexes()
        emptied = 0
        if archive.complete:
            emptied = trash.empty(archive, older_than_days=trash.DEFAULT_DAYS)
            if emptied:
                archive.sync_indexes()
        interrupted = len(resolve.pending(archive)) + edit.pending(archive)
        result = Startup(interrupted=interrupted, emptied=emptied)
        result.files, result.size = archive.index.count_files()
        report = check.quick_check(archive, on_progress=on_progress, should_stop=should_stop)
        result.issues = resolve.build_issues(report, archive)
        result.errors = len(report.errors)
    return result


def recover(disks: list[Disk], **_) -> resolve.Outcome:
    """Finish the actions and the changes interrupted last time."""
    with Archive.open(disks) as archive:
        edit.recover(archive)
        return resolve.recover(archive)
