import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import check, edit, status


@pytest.fixture
def filled(arch):
    put(arch, "FOTO 2026/MARE/a.jpg", b"a")
    put(arch, "FOTO 2026/MARE/b.jpg", b"b")
    put(arch, "FOTO 2026/c.jpg", b"c")
    return arch


def on_all(arch, path):
    return [arch.path_on(d, path).exists() for d in arch.disks]


def paths(arch):
    return sorted(r.path for r in arch.index.files())


@pytest.mark.parametrize("name", ["", ".hidden", "a/b", "a\\b", 'a"b', "a:b", "x.", ".."])
def test_bad_names(name):
    with pytest.raises(edit.EditError):
        edit.check_name(name)


def test_rename_file(filled):
    assert edit.rename(filled, "FOTO 2026/c.jpg", "spiaggia.jpg") == "FOTO 2026/spiaggia.jpg"
    assert on_all(filled, "FOTO 2026/spiaggia.jpg") == [True, True]
    assert on_all(filled, "FOTO 2026/c.jpg") == [False, False]
    assert "FOTO 2026/spiaggia.jpg" in paths(filled)
    assert check.full_check(filled).clean


def test_rename_folder(filled):
    edit.rename(filled, "FOTO 2026/MARE", "MARE 2026")
    assert paths(filled) == [
        "FOTO 2026/MARE 2026/a.jpg",
        "FOTO 2026/MARE 2026/b.jpg",
        "FOTO 2026/c.jpg",
    ]
    assert filled.index.events()[0].kind == "renamed"
    assert check.full_check(filled).clean


def test_rename_only_letter_case(filled):
    edit.rename(filled, "FOTO 2026/MARE", "Mare")
    assert paths(filled)[0] == "FOTO 2026/Mare/a.jpg"
    assert check.full_check(filled).clean


def test_rename_never_overwrites(filled):
    with pytest.raises(edit.EditError):
        edit.rename(filled, "FOTO 2026/MARE/a.jpg", "B.JPG")
    assert paths(filled) == ["FOTO 2026/MARE/a.jpg", "FOTO 2026/MARE/b.jpg", "FOTO 2026/c.jpg"]


def test_move(filled):
    edit.new_folder(filled, "", "ALBUM")
    edit.move(filled, "FOTO 2026/MARE", "ALBUM")
    assert paths(filled)[:2] == ["ALBUM/MARE/a.jpg", "ALBUM/MARE/b.jpg"]
    with pytest.raises(edit.EditError):
        edit.move(filled, "ALBUM", "ALBUM/MARE")
    assert check.full_check(filled).clean


def test_new_folder(filled):
    assert edit.new_folder(filled, "FOTO 2026", "NEVE") == "FOTO 2026/NEVE"
    assert on_all(filled, "FOTO 2026/NEVE") == [True, True]
    with pytest.raises(edit.EditError):
        edit.new_folder(filled, "FOTO 2026", "neve")


def test_delete_files_and_folders(filled):
    assert edit.delete(filled, ["FOTO 2026/MARE", "FOTO 2026/c.jpg"]) == 3
    assert paths(filled) == []
    assert on_all(filled, "FOTO 2026/MARE") == [False, False]
    assert len(filled.index.trash()) == 6  # 3 files × 2 disks
    assert check.full_check(filled).clean


def test_delete_keeps_folders_with_other_files(filled):
    for disk in filled.disks:
        (filled.path_on(disk, "FOTO 2026/MARE") / "note.txt").write_text("keep")
    edit.delete(filled, ["FOTO 2026/MARE"])
    assert on_all(filled, "FOTO 2026/MARE/note.txt") == [True, True]


def test_needs_both_disks(filled, two_disks):
    filled.close()
    only_a = archive_mod.Archive.open([two_disks[0]])
    with only_a, pytest.raises(archive_mod.ArchiveError):
        edit.rename(only_a, "FOTO 2026/c.jpg", "d.jpg")


class Crash(BaseException):
    pass


def test_interrupted_rename_is_finished(filled, monkeypatch):
    real = filled.index.move_file

    def dying(*args):
        raise Crash

    monkeypatch.setattr(filled.index, "move_file", dying)
    with pytest.raises(Crash):
        edit.rename(filled, "FOTO 2026/MARE", "MARE 2026")
    monkeypatch.setattr(filled.index, "move_file", real)
    filled.sync_indexes()
    disks = list(filled.disks)
    filled.close()
    assert status.startup_check(disks).interrupted == 1
    status.recover(disks)
    with archive_mod.Archive.open(disks) as arch:
        assert paths(arch)[0] == "FOTO 2026/MARE 2026/a.jpg"
        assert check.full_check(arch).clean
        assert edit.pending(arch) == 0
