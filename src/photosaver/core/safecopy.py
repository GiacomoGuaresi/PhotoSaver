"""Verified copy: a file never appears under its final name until its copy is proven good.

For each destination:

1. write to ``.<name>.photosaver-partial`` next to the final file;
2. flush it to the disk (``fsync``);
3. read it back from the disk and compare its hash with the source;
4. give it the source's modification time;
5. rename it to the final name.

The source is read once, however many destinations there are (upload to disk A and B
together). An existing file is never overwritten. An interruption leaves at most a
``.photosaver-partial`` file, which the scanner skips and the next copy replaces.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from . import hashing

PARTIAL_SUFFIX = ".photosaver-partial"


class CopyError(Exception):
    """Base class for copy errors. No destination is left half-written."""


class SourceChanged(CopyError):
    """The source content does not match the expected hash (changed or corrupt)."""


class VerifyFailed(CopyError):
    """A copy read back from the destination differs from the source."""


def partial_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.name}{PARTIAL_SUFFIX}")


def safe_copy(
    source: Path,
    destinations: Sequence[Path],
    *,
    expected_hash: str | None = None,
    on_progress: Callable[[int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> str:
    """Copy ``source`` to every destination with verification and return its hash.

    ``expected_hash``, when given, is checked against the content actually read, so a
    corrupt source is never spread. ``on_progress`` receives the bytes read for each chunk
    of the source; ``should_stop`` is polled between chunks (raises
    :class:`hashing.Cancelled`).

    On error, partial files are removed. Destinations are renamed into place only at the
    very end, after all of them are verified.
    """
    if not destinations:
        raise ValueError("no destination")
    for destination in destinations:
        if destination.exists():
            raise FileExistsError(f"{destination} already exists: never overwritten")

    stat = source.stat()
    partials = [partial_path(destination) for destination in destinations]
    created: list[Path] = []
    try:
        source_hash = _write_partials(source, partials, created, on_progress, should_stop)
        if expected_hash is not None and source_hash != expected_hash:
            raise SourceChanged(f"{source} does not match its expected hash")

        for partial in partials:
            _drop_cache(partial)
            if hashing.hash_file(partial, should_stop=should_stop) != source_hash:
                raise VerifyFailed(f"{partial} differs from {source} after copy")
            os.utime(partial, ns=(stat.st_atime_ns, stat.st_mtime_ns))

        for partial, destination in zip(partials, destinations, strict=True):
            if destination.exists():
                raise FileExistsError(f"{destination} appeared during the copy")
            os.rename(partial, destination)
            created.remove(partial)
            _sync_folder(destination.parent)
    finally:
        for partial in created:
            with contextlib.suppress(OSError):
                partial.unlink()
    return source_hash


def _write_partials(
    source: Path,
    partials: list[Path],
    created: list[Path],
    on_progress: Callable[[int], None] | None,
    should_stop: Callable[[], bool] | None,
) -> str:
    hasher = hashing.new_hasher()
    buffer = bytearray(hashing.CHUNK)
    view = memoryview(buffer)
    with contextlib.ExitStack() as stack:
        reader = stack.enter_context(source.open("rb", buffering=0))
        writers = []
        for partial in partials:
            partial.parent.mkdir(parents=True, exist_ok=True)
            partial.unlink(missing_ok=True)  # left over by an interrupted copy
            writers.append(stack.enter_context(partial.open("xb")))
            created.append(partial)

        while read := reader.readinto(buffer):
            chunk = view[:read]
            hasher.update(chunk)
            for writer in writers:
                writer.write(chunk)
            if on_progress:
                on_progress(read)
            if should_stop and should_stop():
                raise hashing.Cancelled(str(source))

        for writer in writers:
            writer.flush()
            os.fsync(writer.fileno())
    return hasher.hexdigest()


def _drop_cache(path: Path) -> None:
    """Ask the OS to forget the file's cached pages, so reading it back reads the disk.

    Only on systems that support it (Linux); elsewhere the read-back may come from cache.
    """
    if not hasattr(os, "posix_fadvise"):
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    finally:
        os.close(fd)


def _sync_folder(folder: Path) -> None:
    """Make a rename durable (POSIX only: Windows cannot open folders this way)."""
    if os.name != "posix":
        return
    fd = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError:
        pass  # some filesystems do not support syncing folders
    finally:
        os.close(fd)
