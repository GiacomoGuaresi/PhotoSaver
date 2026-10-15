import json

import pytest

from photosaver.core import disk


def test_init_and_open(tmp_path):
    created = disk.init_disk(tmp_path, label="A", archive_dir="Foto")

    assert (tmp_path / ".photosaver" / "disk.json").is_file()
    assert (tmp_path / "Foto").is_dir()
    assert disk.is_disk(tmp_path)

    opened = disk.open_disk(tmp_path)
    assert opened == created
    assert opened.label == "A"
    assert opened.archive == tmp_path / "Foto"
    assert opened.data_dir == tmp_path / ".photosaver"


def test_second_disk_joins_the_archive(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = disk.init_disk(tmp_path / "a", label="A", archive_dir="Foto")
    b = disk.init_disk(tmp_path / "b", label="B", archive_dir="Foto", archive_id=a.info.archive_id)

    assert b.info.archive_id == a.info.archive_id
    assert b.id != a.id


def test_existing_files_are_kept(tmp_path):
    (tmp_path / "Foto").mkdir()
    (tmp_path / "Foto" / "old.jpg").write_bytes(b"x")
    disk.init_disk(tmp_path, label="A", archive_dir="Foto")
    assert (tmp_path / "Foto" / "old.jpg").read_bytes() == b"x"


def test_init_twice_is_refused(tmp_path):
    first = disk.init_disk(tmp_path, label="A", archive_dir="Foto")
    with pytest.raises(disk.AlreadyADisk):
        disk.init_disk(tmp_path, label="B", archive_dir="Foto")
    assert disk.open_disk(tmp_path) == first


def test_init_missing_folder(tmp_path):
    with pytest.raises(disk.NotADisk):
        disk.init_disk(tmp_path / "missing", label="A", archive_dir="Foto")


@pytest.mark.parametrize("name", ["", ".photosaver", "a/b", "a\\b", ".."])
def test_invalid_archive_dir(tmp_path, name):
    with pytest.raises(ValueError):
        disk.init_disk(tmp_path, label="A", archive_dir=name)
    assert not (tmp_path / ".photosaver").exists()


def test_open_plain_folder(tmp_path):
    assert not disk.is_disk(tmp_path)
    with pytest.raises(disk.NotADisk):
        disk.open_disk(tmp_path)


@pytest.mark.parametrize("content", ["{broken", "[]", '{"format": 1}', '{"format": "1"}'])
def test_open_damaged_file(tmp_path, content):
    (tmp_path / ".photosaver").mkdir()
    (tmp_path / ".photosaver" / "disk.json").write_text(content)
    with pytest.raises(disk.NotADisk):
        disk.open_disk(tmp_path)


def test_open_newer_format(tmp_path):
    disk.init_disk(tmp_path, label="A", archive_dir="Foto")
    path = tmp_path / ".photosaver" / "disk.json"
    data = json.loads(path.read_text())
    path.write_text(json.dumps(data | {"format": disk.FORMAT + 1}))
    with pytest.raises(disk.UnsupportedFormat):
        disk.open_disk(tmp_path)


def test_write_json_leaves_no_temp_file(tmp_path):
    disk.write_json(tmp_path / "x.json", {"a": 1})
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]
