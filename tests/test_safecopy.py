import os

import pytest

from photosaver.core import hashing, safecopy


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "desktop" / "20260810_093015.jpg"
    path.parent.mkdir()
    path.write_bytes(os.urandom(3 * 1024 * 1024 + 17))
    os.utime(path, ns=(1_700_000_000_000_000_000, 1_600_000_000_120_000_000))
    return path


def leftovers(root):
    return [p for p in root.rglob("*") if p.name.endswith(safecopy.PARTIAL_SUFFIX)]


def test_copy_to_two_disks(tmp_path, source):
    a = tmp_path / "disk-a" / "Foto" / "MARE 2026" / source.name
    b = tmp_path / "disk-b" / "Foto" / "MARE 2026" / source.name
    seen = []

    digest = safecopy.safe_copy(source, [a, b], on_progress=seen.append)

    assert digest == hashing.hash_file(source)
    for copy in (a, b):
        assert copy.read_bytes() == source.read_bytes()
        assert copy.stat().st_mtime_ns == source.stat().st_mtime_ns
    assert sum(seen) == source.stat().st_size
    assert leftovers(tmp_path) == []


def test_expected_hash_ok(tmp_path, source):
    digest = hashing.hash_file(source)
    assert safecopy.safe_copy(source, [tmp_path / "a.jpg"], expected_hash=digest) == digest


def test_never_overwrites(tmp_path, source):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    b.write_bytes(b"precious")
    with pytest.raises(FileExistsError):
        safecopy.safe_copy(source, [a, b])
    assert b.read_bytes() == b"precious"
    assert not a.exists()
    assert leftovers(tmp_path) == []


def test_corrupt_source_is_not_spread(tmp_path, source):
    a = tmp_path / "a.jpg"
    with pytest.raises(safecopy.SourceChanged):
        safecopy.safe_copy(source, [a], expected_hash="0" * 64)
    assert not a.exists()
    assert leftovers(tmp_path) == []


def test_bad_copy_is_not_renamed(tmp_path, source, monkeypatch):
    real = hashing.hash_file

    def corrupt_read_back(path, **kwargs):
        digest = real(path, **kwargs)
        return "bad" if path.name.endswith(safecopy.PARTIAL_SUFFIX) else digest

    monkeypatch.setattr(hashing, "hash_file", corrupt_read_back)
    a, b = tmp_path / "a" / "x.jpg", tmp_path / "b" / "x.jpg"
    with pytest.raises(safecopy.VerifyFailed):
        safecopy.safe_copy(source, [a, b])
    assert not a.exists() and not b.exists()
    assert leftovers(tmp_path) == []


def test_cancel_cleans_up(tmp_path, source):
    a = tmp_path / "a.jpg"
    with pytest.raises(hashing.Cancelled):
        safecopy.safe_copy(source, [a], should_stop=lambda: True)
    assert not a.exists()
    assert leftovers(tmp_path) == []


def test_interrupted_copy_is_replaced(tmp_path, source):
    a = tmp_path / "a.jpg"
    safecopy.partial_path(a).write_bytes(b"half a photo")
    safecopy.safe_copy(source, [a])
    assert a.read_bytes() == source.read_bytes()
    assert leftovers(tmp_path) == []


def test_missing_source(tmp_path):
    a = tmp_path / "a.jpg"
    with pytest.raises(FileNotFoundError):
        safecopy.safe_copy(tmp_path / "nope.jpg", [a])
    assert list(tmp_path.iterdir()) == []


def test_empty_file(tmp_path):
    source = tmp_path / "zero.jpg"
    source.write_bytes(b"")
    safecopy.safe_copy(source, [tmp_path / "out" / "zero.jpg"])
    assert (tmp_path / "out" / "zero.jpg").read_bytes() == b""


def test_needs_a_destination(source):
    with pytest.raises(ValueError):
        safecopy.safe_copy(source, [])


def test_partial_name_is_hidden(tmp_path):
    partial = safecopy.partial_path(tmp_path / "x" / "a.jpg")
    assert partial == tmp_path / "x" / ".a.jpg.photosaver-partial"
