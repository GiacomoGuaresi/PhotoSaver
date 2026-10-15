import shutil

import pytest
from conftest import put

from photosaver.core import check


@pytest.fixture
def filled(arch):
    put(arch, "FOTO 2026/MARE/a.jpg", b"photo a" * 100)
    put(arch, "FOTO 2026/MARE/b.jpg", b"photo b" * 100)
    put(arch, "ALBUM/a.jpg", b"photo a" * 100)  # same content, intentional duplicate
    return arch


def disk(arch, label):
    return next(d for d in arch.disks if d.label == label)


def move(arch, label, old, new):
    d = disk(arch, label)
    target = arch.path_on(d, new)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(arch.path_on(d, old), target)


def summary(report):
    return sorted((d.kind, d.path, d.target) for d in report.differences)


@pytest.mark.parametrize("run", [check.quick_check, check.full_check])
def test_move_on_one_disk(filled, run):
    move(filled, "B", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE 2026/b.jpg")
    report = run(filled)
    assert summary(report) == [("moved", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE 2026/b.jpg")]
    assert report.differences[0].disk_id == disk(filled, "B").id


def test_rename(filled):
    move(filled, "A", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE/spiaggia.jpg")
    assert summary(check.quick_check(filled)) == [
        ("moved", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE/spiaggia.jpg")
    ]


def test_same_move_on_both_disks(filled):
    for label in ("A", "B"):
        move(filled, label, "FOTO 2026/MARE", "FOTO 2026/MARE 2026")
    assert summary(check.quick_check(filled)) == [
        ("moved", "FOTO 2026/MARE/a.jpg", "FOTO 2026/MARE 2026/a.jpg"),
        ("moved", "FOTO 2026/MARE/a.jpg", "FOTO 2026/MARE 2026/a.jpg"),
        ("moved", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE 2026/b.jpg"),
        ("moved", "FOTO 2026/MARE/b.jpg", "FOTO 2026/MARE 2026/b.jpg"),
    ]


def test_duplicates_pair_by_name(filled):
    move(filled, "A", "ALBUM/a.jpg", "ALBUM 2/a.jpg")
    move(filled, "A", "FOTO 2026/MARE/a.jpg", "FOTO 2026/x.jpg")
    assert summary(check.quick_check(filled)) == [
        ("moved", "ALBUM/a.jpg", "ALBUM 2/a.jpg"),
        ("moved", "FOTO 2026/MARE/a.jpg", "FOTO 2026/x.jpg"),
    ]


def test_different_content_is_not_a_move(filled):
    d = disk(filled, "A")
    filled.path_on(d, "FOTO 2026/MARE/b.jpg").unlink()
    put(filled, "FOTO 2026/c.jpg", b"something else", disks=[d], index=False)
    assert summary(check.quick_check(filled)) == [
        ("missing", "FOTO 2026/MARE/b.jpg", None),
        ("untracked", "FOTO 2026/c.jpg", None),
    ]


def test_copy_is_not_a_move(filled):
    put(filled, "FOTO 2026/copy.jpg", b"photo b" * 100, disks=filled.disks[:1], index=False)
    assert summary(check.quick_check(filled)) == [("untracked", "FOTO 2026/copy.jpg", None)]
