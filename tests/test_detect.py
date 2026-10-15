import os

from photosaver.core import archive, detect


def test_configured_roots():
    env = {detect.ENV_DISKS: os.pathsep.join(["/a", "/b", ""])}
    assert [p.as_posix() for p in detect.configured_roots(env)] == ["/a", "/b"]
    assert detect.configured_roots({}) == []


def test_scan_sorts_folders(tmp_path, two_disks):
    empty = tmp_path / "empty"
    (empty / "lost+found").mkdir(parents=True)
    other = tmp_path / "other"
    (other / "music").mkdir(parents=True)
    broken = tmp_path / "broken"
    (broken / ".photosaver").mkdir(parents=True)
    (broken / ".photosaver" / "disk.json").write_text("{")
    roots = [two_disks[0].root, two_disks[1].root, empty, other, broken, tmp_path / "missing"]

    found = detect.scan_roots(roots)
    assert [d.label for d in found.disks] == ["A", "B"]
    assert found.empty == [empty] and found.other == [other] and found.unreadable == [broken]


def test_waiting():
    assert detect.assess(detect.Found()).situation == detect.WAITING


def test_complete(two_disks):
    result = detect.assess(detect.scan_roots([d.root for d in reversed(two_disks)]))
    assert result.situation == detect.COMPLETE
    assert [d.label for d in result.disks] == ["A", "B"]
    assert result.missing == [] and result.all_labels == ["A", "B"]


def test_partial(two_disks):
    result = detect.assess(detect.scan_roots([two_disks[1].root]))
    assert result.situation == detect.PARTIAL
    assert result.missing == ["A"] and result.all_labels == ["A", "B"]


def test_partial_with_first_disk_knows_the_second(two_disks):
    # disk A's index is copied to B when B joins, so A knows B too
    result = detect.assess(detect.scan_roots([two_disks[0].root]))
    assert result.missing == ["B"]


def test_mixed(tmp_path, two_disks):
    (tmp_path / "x").mkdir()
    other = archive.create_archive(tmp_path / "x", label="A", archive_dir="Foto")
    result = detect.assess(detect.scan_roots([two_disks[0].root, other.root]))
    assert result.situation == detect.MIXED


def test_free_space(tmp_path):
    assert detect.free_space(tmp_path) > 0
    assert detect.free_space(tmp_path / "missing") is None
