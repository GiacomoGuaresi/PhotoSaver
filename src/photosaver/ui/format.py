"""Numbers for people: sizes, durations, counts."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QLocale


def size(value: int) -> str:
    """``4.2 GB``, in the user's language."""
    return QLocale().formattedDataSize(value, 1, QLocale.DataSizeFormat.DataSizeSIFormat)


def duration(seconds: float) -> str:
    """A rough, friendly duration: 'less than a minute', 'about 5 minutes', 'about 2 hours'."""
    if seconds < 60:
        return QCoreApplication.translate("format", "less than a minute")
    minutes = round(seconds / 60)
    if minutes < 90:
        return QCoreApplication.translate("format", "about %n minute(s)", None, minutes)
    return QCoreApplication.translate("format", "about %n hour(s)", None, round(seconds / 3600))


class Eta:
    """Time left of a long operation, from how fast it went so far."""

    def __init__(self, clock) -> None:
        self._clock = clock
        self._start = clock()

    def left(self, done: int, total: int) -> float | None:
        elapsed = self._clock() - self._start
        if done <= 0 or total <= 0 or elapsed < 2:
            return None
        return elapsed * (total - done) / done
