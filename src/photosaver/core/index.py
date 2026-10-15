"""The archive index: ``.photosaver/index.sqlite``, one copy on every disk of the archive.

It records what the archive should contain (one row per file, with size, date and hash),
the state of each file on each disk, and the history of every operation. Disks are rows,
not columns, so a third copy needs no schema change.

All writes happen inside :meth:`Index.transaction`, which also bumps the index *revision*:
comparing revisions tells which disk's index is the most recent after an interruption.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import hashing

INDEX_FILE = "index.sqlite"
HASH_ALGORITHM = hashing.ALGORITHM

# Copy states, per file and disk
OK = "ok"
MISSING = "missing"
CORRUPT = "corrupt"

# One script per schema version: MIGRATIONS[n] upgrades from version n to n + 1.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE meta (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE disks (
        id       TEXT PRIMARY KEY,
        label    TEXT NOT NULL,
        added_at TEXT NOT NULL
    );
    CREATE TABLE files (
        id       INTEGER PRIMARY KEY,
        path     TEXT NOT NULL UNIQUE,  -- relative to the archive folder, with '/'
        size     INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL,
        hash     TEXT NOT NULL,
        added_at TEXT NOT NULL
    );
    CREATE INDEX files_hash ON files (hash);
    CREATE TABLE copies (
        file_id     INTEGER NOT NULL REFERENCES files (id) ON DELETE CASCADE,
        disk_id     TEXT NOT NULL REFERENCES disks (id),
        state       TEXT NOT NULL,
        verified_at TEXT,  -- last time the content was read back and its hash checked
        PRIMARY KEY (file_id, disk_id)
    );
    CREATE TABLE events (
        id      INTEGER PRIMARY KEY,
        at      TEXT NOT NULL,
        kind    TEXT NOT NULL,
        path    TEXT,
        disk_id TEXT,
        detail  TEXT  -- JSON
    );
    CREATE INDEX events_at ON events (at);
    """,
]
SCHEMA_VERSION = len(MIGRATIONS)


class IndexFileError(Exception):
    """Base class for index errors."""


class UnsupportedSchema(IndexFileError):
    """The index was written by a newer version of the app."""


class NotInTransaction(IndexFileError):
    """A write was attempted outside :meth:`Index.transaction`."""


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    mtime_ns: int
    hash: str
    added_at: str = ""


@dataclass(frozen=True)
class DiskRecord:
    id: str
    label: str
    added_at: str


@dataclass(frozen=True)
class Copy:
    state: str
    verified_at: str | None


@dataclass(frozen=True)
class Event:
    at: str
    kind: str
    path: str | None
    disk_id: str | None
    detail: dict


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Index:
    def __init__(self, connection: sqlite3.Connection, path: Path) -> None:
        self._db = connection
        self.path = path
        self._in_transaction = False

    # Opening

    @classmethod
    def create(cls, path: Path, *, archive_id: str) -> Index:
        if path.exists():
            raise FileExistsError(f"{path} already exists")
        index = cls._connect(path)
        with index.transaction():
            index._set_meta("archive_id", archive_id)
            index._set_meta("hash_algorithm", HASH_ALGORITHM)
            index._set_meta("created", now())
        return index

    @classmethod
    def open(cls, path: Path) -> Index:
        if not path.is_file():
            raise FileNotFoundError(f"{path} does not exist")
        return cls._connect(path)

    @classmethod
    def _connect(cls, path: Path) -> Index:
        db = sqlite3.connect(path, isolation_level=None)
        try:
            # No WAL: it needs shared memory, unreliable on removable exFAT drives.
            db.execute("PRAGMA journal_mode = DELETE")
            db.execute("PRAGMA synchronous = FULL")
            db.execute("PRAGMA foreign_keys = ON")
            _migrate(db)
        except BaseException:
            db.close()
            raise
        return cls(db, path)

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> Index:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # Transactions and revision

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Group writes: all or nothing. Each committed transaction bumps the revision."""
        if self._in_transaction:
            yield
            return
        self._db.execute("BEGIN IMMEDIATE")
        self._in_transaction = True
        try:
            yield
            self._set_meta("revision", str(self.revision + 1))
            self._db.execute("COMMIT")
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        finally:
            self._in_transaction = False

    def _write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        if not self._in_transaction:
            raise NotInTransaction("index writes must happen inside a transaction")
        return self._db.execute(sql, params)

    @property
    def revision(self) -> int:
        return int(self._get_meta("revision") or 0)

    @property
    def archive_id(self) -> str:
        return self._get_meta("archive_id") or ""

    @property
    def schema_version(self) -> int:
        return self._db.execute("PRAGMA user_version").fetchone()[0]

    def _get_meta(self, key: str) -> str | None:
        row = self._db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self._write("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

    # Disks

    def add_disk(self, disk_id: str, label: str) -> None:
        self._write(
            "INSERT INTO disks (id, label, added_at) VALUES (?, ?, ?)", (disk_id, label, now())
        )

    def disks(self) -> list[DiskRecord]:
        rows = self._db.execute("SELECT id, label, added_at FROM disks ORDER BY label, added_at")
        return [DiskRecord(*row) for row in rows]

    # Files

    def put_file(self, record: FileRecord) -> None:
        """Add a file, or update size, date and hash of the file at the same path."""
        self._write(
            """
            INSERT INTO files (path, size, mtime_ns, hash, added_at) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (path) DO UPDATE SET
                size = excluded.size, mtime_ns = excluded.mtime_ns, hash = excluded.hash
            """,
            (record.path, record.size, record.mtime_ns, record.hash, record.added_at or now()),
        )

    def get_file(self, path: str) -> FileRecord | None:
        row = self._db.execute(
            "SELECT path, size, mtime_ns, hash, added_at FROM files WHERE path = ?", (path,)
        ).fetchone()
        return FileRecord(*row) if row else None

    def files(self) -> Iterator[FileRecord]:
        rows = self._db.execute(
            "SELECT path, size, mtime_ns, hash, added_at FROM files ORDER BY path"
        )
        return (FileRecord(*row) for row in rows)

    def files_with_hash(self, hash_: str) -> list[FileRecord]:
        rows = self._db.execute(
            "SELECT path, size, mtime_ns, hash, added_at FROM files WHERE hash = ? ORDER BY path",
            (hash_,),
        )
        return [FileRecord(*row) for row in rows]

    def count_files(self) -> tuple[int, int]:
        """Number of files and total size in bytes."""
        count, size = self._db.execute("SELECT COUNT(*), TOTAL(size) FROM files").fetchone()
        return count, int(size)

    def remove_file(self, path: str) -> None:
        self._write("DELETE FROM files WHERE path = ?", (path,))

    def move_file(self, old: str, new: str) -> None:
        cursor = self._write("UPDATE files SET path = ? WHERE path = ?", (new, old))
        if cursor.rowcount == 0:
            raise KeyError(old)

    # Copies on each disk

    def set_copy(
        self, path: str, disk_id: str, state: str, *, verified_at: str | None = None
    ) -> None:
        cursor = self._write(
            """
            INSERT INTO copies (file_id, disk_id, state, verified_at)
            SELECT id, ?, ?, ? FROM files WHERE path = ?
            ON CONFLICT (file_id, disk_id) DO UPDATE SET
                state = excluded.state,
                verified_at = COALESCE(excluded.verified_at, copies.verified_at)
            """,
            (disk_id, state, verified_at, path),
        )
        if cursor.rowcount == 0:
            raise KeyError(path)

    def copies(self, path: str) -> dict[str, Copy]:
        rows = self._db.execute(
            """
            SELECT disk_id, state, verified_at FROM copies
            JOIN files ON files.id = copies.file_id WHERE files.path = ?
            """,
            (path,),
        )
        return {disk_id: Copy(state, verified_at) for disk_id, state, verified_at in rows}

    # History

    def log(
        self, kind: str, *, path: str | None = None, disk_id: str | None = None, **detail
    ) -> None:
        self._write(
            "INSERT INTO events (at, kind, path, disk_id, detail) VALUES (?, ?, ?, ?, ?)",
            (now(), kind, path, disk_id, json.dumps(detail) if detail else None),
        )

    def events(self, limit: int | None = None) -> list[Event]:
        """Most recent first."""
        rows = self._db.execute(
            "SELECT at, kind, path, disk_id, detail FROM events ORDER BY id DESC LIMIT ?",
            (-1 if limit is None else limit,),
        )
        return [
            Event(at, kind, path, disk_id, json.loads(detail) if detail else {})
            for at, kind, path, disk_id, detail in rows
        ]

    # Copying the index to another disk

    def copy_to(self, path: Path) -> None:
        """Write a consistent copy of the index to ``path``, replacing it atomically."""
        tmp = path.with_name(path.name + ".tmp")
        tmp.unlink(missing_ok=True)
        target = sqlite3.connect(tmp)
        try:
            self._db.backup(target)
        finally:
            target.close()
        with tmp.open("rb+") as file:
            os.fsync(file.fileno())
        os.replace(tmp, path)


def _migrate(db: sqlite3.Connection) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise UnsupportedSchema("the index was written by a newer PhotoSaver: please update")
    for target in range(version, SCHEMA_VERSION):
        db.execute("BEGIN IMMEDIATE")
        try:
            for statement in _statements(MIGRATIONS[target]):
                db.execute(statement)
            db.execute(f"PRAGMA user_version = {target + 1}")
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise


def _statements(script: str) -> list[str]:
    """Split a migration script into statements (executescript would commit on its own)."""
    statements, current = [], ""
    for line in script.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            statements.append(current.strip())
            current = ""
    return [s for s in statements if s]
