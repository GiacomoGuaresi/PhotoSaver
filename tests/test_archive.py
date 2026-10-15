import pytest

from photosaver.core import archive
from photosaver.core.index import FileRecord


@pytest.fixture
def disks(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).mkdir()
    a = archive.create_archive(tmp_path / "a", label="A", archive_dir="Foto")
    b = archive.join_archive(a, tmp_path / "b", label="B")
    return a, b


def test_open_both(disks):
    a, b = disks
    with archive.Archive.open([b, a]) as arch:
        assert [d.label for d in arch.disks] == ["A", "B"]
        assert arch.complete and arch.missing == [] and arch.stale == []
        assert arch.path_on(b, "FOTO 2026/x.jpg") == b.archive / "FOTO 2026" / "x.jpg"


def test_one_disk_is_incomplete(disks):
    a, _ = disks
    with archive.Archive.open([a]) as arch:
        assert not arch.complete
        assert arch.missing == ["B"]


def test_most_recent_index_wins_and_syncs(disks):
    a, b = disks
    with archive.open_index(b) as index, index.transaction():
        index.put_file(FileRecord("x.jpg", 1, 1, "h"))
    with archive.Archive.open([a, b]) as arch:
        assert arch.primary is b
        assert arch.stale == [a]
        arch.sync_indexes()
        assert arch.stale == []
    with archive.open_index(a) as index:
        assert index.get_file("x.jpg") is not None


def test_mixed_archives(tmp_path, disks):
    a, _ = disks
    other = archive.create_archive(tmp_path / "c", label="A", archive_dir="Foto")
    with pytest.raises(archive.MixedArchives):
        archive.Archive.open([a, other])


def test_no_disks():
    with pytest.raises(ValueError):
        archive.Archive.open([])
