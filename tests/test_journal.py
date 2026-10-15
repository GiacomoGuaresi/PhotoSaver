import os
import shutil

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import check, resolve, safecopy, trash
from photosaver.core.resolve import Option

A_DATA = b"photo a" * 100


class Crash(BaseException):
    """The app dies: nothing catches this."""


@pytest.fixture
def filled(arch):
    put(arch, "FOTO/a.jpg", A_DATA)
    put(arch, "FOTO/b.jpg", b"photo b" * 100)
    return arch


def path(arch, label, p):
    disk = next(d for d in arch.disks if d.label == label)
    return arch.path_on(disk, p)


def damage(p):
    stat = p.stat()
    p.write_bytes(b"X" + p.read_bytes()[1:])
    os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def crash_and_reopen(arch, issues, monkeypatch, target, attribute, after=0):
    calls = []
    real = getattr(target, attribute)

    def dying(*args, **kwargs):
        calls.append(1)
        if len(calls) > after:
            raise Crash
        return real(*args, **kwargs)

    monkeypatch.setattr(target, attribute, dying)
    with pytest.raises(Crash):
        resolve.apply(issues, arch)
    monkeypatch.setattr(target, attribute, real)
    disks = list(arch.disks)
    arch.close()
    return archive_mod.Archive.open(disks)


def test_interrupted_repair_is_finished(filled, monkeypatch):
    damage(path(filled, "B", "FOTO/a.jpg"))
    issues = resolve.build_issues(check.full_check(filled), filled)
    reopened = crash_and_reopen(filled, issues, monkeypatch, safecopy, "safe_copy")
    with reopened:
        assert not path(reopened, "B", "FOTO/a.jpg").exists()  # trashed, not yet replaced
        (pending,) = resolve.pending(reopened)
        assert (pending.path, pending.chosen) == ("FOTO/a.jpg", Option(resolve.REPAIR))

        outcome = resolve.recover(reopened)
        assert outcome.failed == [] and len(outcome.done) == 1
        assert path(reopened, "B", "FOTO/a.jpg").read_bytes() == A_DATA
        assert resolve.pending(reopened) == []
        assert check.full_check(reopened).clean
        assert reopened.index.events()[0].kind == "full_check_done"
        assert any(e.kind == "recovered" for e in reopened.index.events())


def test_interrupted_delete_everywhere_is_finished(filled, monkeypatch):
    path(filled, "A", "FOTO/b.jpg").unlink()
    issues = resolve.build_issues(check.quick_check(filled), filled)
    issues[0].choice = Option(resolve.DELETE_ALL)
    path(filled, "A", "FOTO/b.jpg").write_bytes(b"photo b" * 100)  # on both, to trash twice
    reopened = crash_and_reopen(filled, issues, monkeypatch, trash, "move_to_trash", after=1)
    with reopened:
        assert path(reopened, "B", "FOTO/b.jpg").exists()
        resolve.recover(reopened)
        assert not path(reopened, "B", "FOTO/b.jpg").exists()
        assert reopened.index.get_file("FOTO/b.jpg") is None
        assert check.quick_check(reopened).clean


def test_interrupted_move_is_finished(filled, monkeypatch):
    shutil.move(path(filled, "A", "FOTO"), path(filled, "A", "FOTO 2026"))
    issues = resolve.build_issues(check.quick_check(filled), filled)
    reopened = crash_and_reopen(filled, issues, monkeypatch, resolve, "_index_move")
    with reopened:
        assert path(reopened, "B", "FOTO 2026/a.jpg").exists()  # renamed, index not updated
        assert len(resolve.pending(reopened)) == 1
        resolve.recover(reopened)
        assert reopened.index.get_file("FOTO 2026/a.jpg") is not None
        # the second issue never started: the check finds it again
        resolve.apply(resolve.build_issues(check.quick_check(reopened), reopened), reopened)
        assert check.full_check(reopened).clean


def test_actions_can_run_twice(filled):
    damage(path(filled, "B", "FOTO/a.jpg"))
    shutil.move(path(filled, "A", "FOTO/b.jpg"), path(filled, "A", "b.jpg"))
    issues = resolve.build_issues(check.full_check(filled), filled)
    assert resolve.apply(issues, filled).failed == []
    assert resolve.apply(issues, filled).failed == []
    assert len(filled.index.trash()) == 1
    assert check.full_check(filled).clean


def test_nothing_pending_normally(filled):
    damage(path(filled, "B", "FOTO/a.jpg"))
    resolve.apply(resolve.build_issues(check.full_check(filled), filled), filled)
    assert resolve.pending(filled) == []
    assert resolve.recover(filled).done == []
