import pytest

from photosaver.core import archive, hashing
from photosaver.core.index import OK, FileRecord


@pytest.fixture
def two_disks(tmp_path):
    """Disks A and B of a new, empty archive."""
    for name in ("disk-a", "disk-b"):
        (tmp_path / name).mkdir()
    a = archive.create_archive(tmp_path / "disk-a", label="A", archive_dir="Foto")
    b = archive.join_archive(a, tmp_path / "disk-b", label="B")
    return a, b


@pytest.fixture
def arch(two_disks):
    with archive.Archive.open(list(two_disks)) as opened:
        yield opened


def put(arch, path, data: bytes, *, disks=None, index=True):
    """Place a file in the archive by hand: on the disks and, optionally, in the index."""
    for disk in disks if disks is not None else arch.disks:
        target = arch.path_on(disk, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if index:
        stat = arch.path_on(arch.disks[0], path).stat()
        with arch.index.transaction():
            arch.index.put_file(
                FileRecord(path, len(data), stat.st_mtime_ns, hashing.hash_bytes(data))
            )
            for disk in arch.disks:
                arch.index.set_copy(path, disk.id, OK)
        arch.sync_indexes()
