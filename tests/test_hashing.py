import hashlib

import pytest

from photosaver.core import hashing


def test_matches_sha256(tmp_path):
    data = bytes(range(256)) * 10_000  # bigger than one chunk
    path = tmp_path / "a.jpg"
    path.write_bytes(data)
    assert hashing.hash_file(path) == hashlib.sha256(data).hexdigest()
    assert hashing.hash_bytes(data) == hashlib.sha256(data).hexdigest()


def test_empty_file(tmp_path):
    path = tmp_path / "zero.jpg"
    path.write_bytes(b"")
    assert hashing.hash_file(path) == hashlib.sha256(b"").hexdigest()


def test_one_byte_changes_the_hash(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"\x00" * 5000)
    b.write_bytes(b"\x00" * 4999 + b"\x01")
    assert hashing.hash_file(a) != hashing.hash_file(b)


def test_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(hashing, "CHUNK", 4)
    path = tmp_path / "a"
    path.write_bytes(b"0123456789")
    seen = []
    hashing.hash_file(path, on_progress=seen.append)
    assert seen == [4, 4, 2]


def test_cancel(tmp_path, monkeypatch):
    monkeypatch.setattr(hashing, "CHUNK", 4)
    path = tmp_path / "a"
    path.write_bytes(b"0123456789")
    with pytest.raises(hashing.Cancelled):
        hashing.hash_file(path, should_stop=lambda: True)
