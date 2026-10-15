import os
import shutil

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import check, hashing, resolve
from photosaver.core.index import FileRecord
from photosaver.core.resolve import Option

A_DATA = b"photo a" * 100
B_DATA = b"photo b" * 100


@pytest.fixture
def filled(arch):
    put(arch, "FOTO 2026/MARE/a.jpg", A_DATA)
    put(arch, "FOTO 2026/MARE/b.jpg", B_DATA)
    return arch


def disk(arch, label):
    return next(d for d in arch.disks if d.label == label)


def path(arch, label, p):
    return arch.path_on(disk(arch, label), p)


def issues(arch, full=False):
    report = (check.full_check if full else check.quick_check)(arch)
    return resolve.build_issues(report, arch)


def fix(arch, chosen=None, full=False):
    found = issues(arch, full)
    for issue in found:
        if chosen is not None:
            issue.choice = chosen if isinstance(chosen, Option) else Option(chosen)
    outcome = resolve.apply(found, arch)
    assert outcome.failed == []
    return found


def damage(p):
    stat = p.stat()
    data = bytearray(p.read_bytes())
    data[10] ^= 0xFF
    p.write_bytes(bytes(data))
    os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def trashed(arch):
    return sorted((e.path, e.reason) for e in arch.index.trash())


def test_repair_bit_rot(filled):
    damage(path(filled, "A", "FOTO 2026/MARE/a.jpg"))
    (issue,) = issues(filled, full=True)
    assert issue.kind == resolve.I_CORRUPT
    assert issue.proposed == Option(resolve.REPAIR)

    resolve.apply([issue], filled)
    assert path(filled, "A", "FOTO 2026/MARE/a.jpg").read_bytes() == A_DATA
    assert trashed(filled) == [("FOTO 2026/MARE/a.jpg", "replaced")]
    assert check.full_check(filled).clean


def test_corrupt_everywhere_cannot_be_repaired(filled):
    for label in "AB":
        damage(path(filled, label, "FOTO 2026/MARE/a.jpg"))
    (issue,) = issues(filled, full=True)
    assert issue.options == [Option(resolve.KNOWN)] and issue.proposed is None


def test_missing_on_a_disk_that_had_it_is_asked(filled):
    path(filled, "B", "FOTO 2026/MARE/b.jpg").unlink()
    (issue,) = issues(filled)
    assert issue.kind == resolve.I_MISSING
    assert issue.proposed is None
    assert Option(resolve.COPY) in issue.options and Option(resolve.DELETE_ALL) in issue.options


def test_missing_copy_back(filled):
    path(filled, "B", "FOTO 2026/MARE/b.jpg").unlink()
    fix(filled, resolve.COPY)
    assert path(filled, "B", "FOTO 2026/MARE/b.jpg").read_bytes() == B_DATA
    assert check.quick_check(filled).clean


def test_missing_on_a_disk_that_never_had_it_is_proposed(filled):
    with filled.index.transaction():
        filled.index.put_file(FileRecord("NEW/c.jpg", 3, 0, hashing.hash_bytes(b"new")))
        filled.index.set_copy("NEW/c.jpg", disk(filled, "A").id, "ok")
    put(filled, "NEW/c.jpg", b"new", disks=[disk(filled, "A")], index=False)
    os.utime(path(filled, "A", "NEW/c.jpg"), ns=(0, 0))
    (issue,) = issues(filled)
    assert issue.proposed == Option(resolve.COPY)


def test_deleted_on_one_disk_delete_everywhere(filled):
    path(filled, "A", "FOTO 2026/MARE/b.jpg").unlink()
    fix(filled, resolve.DELETE_ALL)
    assert not path(filled, "B", "FOTO 2026/MARE/b.jpg").exists()
    assert filled.index.get_file("FOTO 2026/MARE/b.jpg") is None
    assert trashed(filled) == [("FOTO 2026/MARE/b.jpg", "deleted")]
    assert check.quick_check(filled).clean


def test_lost_everywhere_forget(filled):
    for label in "AB":
        path(filled, label, "FOTO 2026/MARE/b.jpg").unlink()
    (issue,) = issues(filled)
    assert issue.kind == resolve.I_LOST
    fix(filled, resolve.FORGET)
    assert filled.index.get_file("FOTO 2026/MARE/b.jpg") is None


def edit(p, data=b"edited"):
    p.write_bytes(data)
    os.utime(p, ns=(0, p.stat().st_mtime_ns + 10**12))


def test_edited_on_one_disk_keep_the_edit(filled):
    edit(path(filled, "A", "FOTO 2026/MARE/a.jpg"))
    (issue,) = issues(filled)
    assert issue.kind == resolve.I_MODIFIED and issue.proposed is None
    fix(filled, Option(resolve.PROPAGATE, disk(filled, "A").id))
    assert path(filled, "B", "FOTO 2026/MARE/a.jpg").read_bytes() == b"edited"
    assert filled.index.get_file("FOTO 2026/MARE/a.jpg").hash == hashing.hash_bytes(b"edited")
    assert trashed(filled) == [("FOTO 2026/MARE/a.jpg", "replaced")]
    assert check.full_check(filled).clean


def test_edited_on_one_disk_revert(filled):
    edit(path(filled, "A", "FOTO 2026/MARE/a.jpg"))
    fix(filled, resolve.REVERT)
    assert path(filled, "A", "FOTO 2026/MARE/a.jpg").read_bytes() == A_DATA
    assert check.full_check(filled).clean


def test_same_edit_everywhere_is_accepted(filled):
    for label in "AB":
        edit(path(filled, label, "FOTO 2026/MARE/a.jpg"))
    (issue,) = issues(filled)
    assert issue.proposed == Option(resolve.ACCEPT)
    resolve.apply([issue], filled)
    assert check.full_check(filled).clean


def test_move_on_one_disk_is_repeated(filled):
    shutil.move(path(filled, "A", "FOTO 2026/MARE"), path(filled, "A", "FOTO 2026/MARE 2026"))
    found = issues(filled)
    assert {(i.kind, i.proposed) for i in found} == {(resolve.I_MOVED, Option(resolve.REPEAT_MOVE))}
    resolve.apply(found, filled)
    assert path(filled, "B", "FOTO 2026/MARE 2026/a.jpg").read_bytes() == A_DATA
    assert filled.index.get_file("FOTO 2026/MARE 2026/b.jpg") is not None
    assert filled.index.get_file("FOTO 2026/MARE/b.jpg") is None
    assert check.full_check(filled).clean


def test_move_undone(filled):
    shutil.move(path(filled, "B", "FOTO 2026/MARE/a.jpg"), path(filled, "B", "x.jpg"))
    fix(filled, resolve.UNDO_MOVE)
    assert path(filled, "B", "FOTO 2026/MARE/a.jpg").exists()
    assert check.full_check(filled).clean


def test_same_move_everywhere_is_accepted(filled):
    for label in "AB":
        shutil.move(path(filled, label, "FOTO 2026/MARE/a.jpg"), path(filled, label, "a.jpg"))
    (issue,) = issues(filled)
    assert issue.proposed == Option(resolve.ACCEPT)
    resolve.apply([issue], filled)
    assert filled.index.get_file("a.jpg") is not None
    assert check.full_check(filled).clean


def test_added_by_hand_on_one_disk(filled):
    put(filled, "FOTO 2026/new.jpg", b"by hand", disks=[disk(filled, "B")], index=False)
    (issue,) = issues(filled)
    assert (issue.kind, issue.proposed) == (resolve.I_UNTRACKED, Option(resolve.ADD))
    resolve.apply([issue], filled)
    assert path(filled, "A", "FOTO 2026/new.jpg").read_bytes() == b"by hand"
    assert check.full_check(filled).clean


def test_added_by_hand_differently(filled):
    put(filled, "x.jpg", b"one", disks=[disk(filled, "A")], index=False)
    put(filled, "x.jpg", b"two", disks=[disk(filled, "B")], index=False)
    (issue,) = issues(filled)
    assert issue.proposed is None
    fix(filled, resolve.DELETE)
    assert check.quick_check(filled).clean
    assert len(filled.index.trash()) == 2


def test_mark_known(filled):
    damage(path(filled, "A", "FOTO 2026/MARE/a.jpg"))
    fix(filled, resolve.KNOWN, full=True)
    report = check.full_check(filled)
    assert report.clean and report.known == 1


def test_complex_case(filled):
    path(filled, "A", "FOTO 2026/MARE/a.jpg").unlink()
    damage(path(filled, "B", "FOTO 2026/MARE/a.jpg"))
    (issue,) = issues(filled, full=True)
    assert issue.kind == resolve.I_COMPLEX and issue.proposed is None
    # no good copy left: only "known", which keeps the damaged one
    assert issue.options == [Option(resolve.KNOWN)]


def test_nothing_chosen_nothing_done(filled):
    path(filled, "B", "FOTO 2026/MARE/b.jpg").unlink()
    outcome = resolve.apply(issues(filled), filled)
    assert outcome.done == [] and outcome.failed == []


def test_failures_are_reported(filled):
    path(filled, "A", "FOTO 2026/MARE/b.jpg").unlink()
    found = issues(filled)
    found[0].choice = Option(resolve.COPY)
    path(filled, "B", "FOTO 2026/MARE/b.jpg").unlink()  # the good copy disappears
    outcome = resolve.apply(found, filled)
    assert [i for i, _ in outcome.failed] == found


def test_needs_all_disks(filled, two_disks):
    filled.close()
    only_a = archive_mod.Archive.open([two_disks[0]])
    with only_a, pytest.raises(archive_mod.ArchiveError):
        resolve.apply([], only_a)
