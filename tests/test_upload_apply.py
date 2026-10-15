from datetime import datetime

import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import hashing, upload
from photosaver.core.index import OK
from photosaver.devtools.fake_media import make_photo


@pytest.fixture
def sea(tmp_path):
    folder = tmp_path / "desktop" / "MARE 2026"
    for n in range(4):
        make_photo(folder / f"2026081{n}_090000.jpg", taken=datetime(2026, 8, 10 + n, 9), seed=n)
    make_photo(folder / "Spiaggia" / "20260815_090000.jpg", taken=datetime(2026, 8, 15), seed=9)
    (folder / "note.txt").write_text("keep me")
    return folder


def planned(arch, *folders):
    plan = upload.analyze(list(folders))
    for folder in plan.folders:
        folder.destination = upload.propose_destination(folder, upload.top_level_folders(arch))
    upload.resolve(plan, arch)
    return plan


def test_upload_to_both_disks(arch, sea):
    plan = planned(arch, sea)
    seen = []
    result = upload.apply(plan, arch, on_progress=lambda d, t: seen.append((d, t)))

    assert len(result.copied) == 5 and result.failed == []
    assert seen[-1][0] == seen[-1][1] == plan.copy_size
    for item in plan.items:
        record = arch.index.get_file(item.target)
        assert record.hash == item.hash
        assert {c.state for c in arch.index.copies(item.target).values()} == {OK}
        for disk in arch.disks:
            copy = arch.path_on(disk, item.target)
            assert hashing.hash_file(copy) == item.hash
            assert copy.stat().st_mtime_ns == item.mtime_ns
    kinds = [e.kind for e in arch.index.events()]
    assert kinds[0] == "upload_done" and kinds.count("upload") == 5
    assert arch.index.events()[0].detail["complete"] is True


def test_indexes_are_synced(arch, sea, two_disks):
    upload.apply(planned(arch, sea), arch)
    for disk in two_disks:
        with archive_mod.open_index(disk) as index:
            assert index.count_files()[0] == 5
            assert index.revision == arch.index.revision


def test_upload_again_copies_nothing(arch, sea):
    upload.apply(planned(arch, sea), arch)
    plan = planned(arch, sea)
    assert {i.status for i in plan.items} == {upload.SAME}
    assert upload.apply(plan, arch).copied == []


def test_resume_after_interruption(arch, sea):
    plan = planned(arch, sea)

    def stop_on_third_file():
        return arch.index.count_files()[0] >= 2

    with pytest.raises(hashing.Cancelled):
        upload.apply(plan, arch, should_stop=stop_on_third_file)
    assert arch.index.events()[0].detail["complete"] is False
    copied_before = arch.index.count_files()[0]
    assert 0 < copied_before < 5

    result = upload.apply(planned(arch, sea), arch)
    assert len(result.copied) == 5 - copied_before
    assert arch.index.count_files()[0] == 5


def test_adopts_file_already_on_a_disk(arch, sea):
    plan = planned(arch, sea)
    item = plan.items[0]
    put(arch, item.target, item.source.read_bytes(), disks=arch.disks[:1], index=False)
    result = upload.apply(plan, arch)
    assert item in result.copied
    copy = arch.path_on(arch.disks[0], item.target)
    assert copy.stat().st_mtime_ns == item.mtime_ns


def test_changed_source_fails_alone(arch, sea):
    plan = planned(arch, sea)
    plan.items[0].source.write_bytes(b"edited after the analysis")
    result = upload.apply(plan, arch)
    assert [item for item, _ in result.failed] == [plan.items[0]]
    assert len(result.copied) == 4
    assert arch.index.get_file(plan.items[0].target) is None
    for disk in arch.disks:
        assert not arch.path_on(disk, plan.items[0].target).exists()


def test_deleted_source_fails_alone(arch, sea):
    plan = planned(arch, sea)
    plan.items[1].source.unlink()
    result = upload.apply(plan, arch)
    assert [item for item, _ in result.failed] == [plan.items[1]]


def test_needs_all_disks(two_disks, sea):
    with archive_mod.Archive.open([two_disks[0]]) as only_a:
        plan = planned(only_a, sea)
        with pytest.raises(archive_mod.ArchiveError, match="B"):
            upload.apply(plan, only_a)


def test_delete_sources(arch, sea):
    plan = planned(arch, sea)
    upload.apply(plan, arch)
    cleanup = upload.delete_sources(plan, arch)
    assert len(cleanup.deleted) == 5 and cleanup.kept == []
    assert sorted(p.name for p in sea.rglob("*")) == [
        "note.txt"
    ]  # ignored file and its folder stay


def test_delete_sources_keeps_what_is_not_safe(arch, sea):
    plan = planned(arch, sea)
    conflict = plan.items[0]
    put(arch, conflict.target, b"another photo")
    upload.resolve(plan, arch)
    conflict.choice = upload.SKIP
    upload.resolve(plan, arch)
    changed = plan.items[1]
    upload.apply(plan, arch)
    changed.source.write_bytes(b"edited")

    cleanup = upload.delete_sources(plan, arch)
    kept = dict(cleanup.kept)
    assert kept[conflict.source] == "not in the archive"
    assert kept[changed.source] == "changed since the upload"
    assert len(cleanup.deleted) == 3
    assert (sea / "Spiaggia").exists() is False


def test_delete_sources_of_duplicates(arch, sea):
    plan = planned(arch, sea)
    item = plan.items[0]
    put(arch, "ALBUM/same.jpg", item.source.read_bytes())
    upload.resolve(plan, arch)
    assert item.status == upload.DUPLICATE and not item.copied
    upload.apply(plan, arch)
    assert item.source in upload.delete_sources(plan, arch).deleted
