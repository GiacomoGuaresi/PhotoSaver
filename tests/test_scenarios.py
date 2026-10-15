"""End to end: an archive set up like a user would, broken in every way the scenarios
know, then checked and fixed. Nothing may be lost."""

import pytest

from photosaver.core import archive, check, hashing, resolve, scanner, upload
from photosaver.core.disk import open_disk
from photosaver.core.resolve import KNOWN
from photosaver.devtools import dev_disks


@pytest.fixture
def dev(tmp_path):
    root = tmp_path / "dev-disks"
    dev_disks.setup(root, seed=3)
    return root


def open_archive(root):
    return archive.Archive.open([open_disk(root / "disk-a"), open_disk(root / "disk-b")])


def test_setup_is_clean(dev):
    with open_archive(dev) as arch:
        assert arch.index.count_files()[0] == 41
        assert check.full_check(arch).clean


@pytest.mark.parametrize("name", sorted(dev_disks.SCENARIOS))
def test_each_scenario_is_found(dev, name):
    dev_disks.break_disks(dev, [name], seed=1)
    with open_archive(dev) as arch:
        report = check.full_check(arch)
    if name in ("partial", "desktop"):
        assert report.clean  # leftovers of a copy and desktop oddities are not differences
    else:
        assert not report.clean


def test_break_everything_then_fix(dev):
    with open_archive(dev) as arch:
        before = {record.hash for record in arch.index.files()}

    done = dev_disks.break_disks(dev, list(dev_disks.SCENARIOS), seed=1)
    assert len(done) == len(dev_disks.SCENARIOS)

    with open_archive(dev) as arch:
        for _ in range(3):
            issues = resolve.build_issues(check.full_check(arch), arch)
            if not issues:
                break
            for issue in issues:  # the proposal, or the first real choice
                if issue.proposed is None:
                    issue.choice = next((o for o in issue.options if o.action != KNOWN), None)
            assert resolve.apply(issues, arch).failed == []
        assert check.full_check(arch).clean

        # every photo that was in the archive is still there, or in the trash
        kept = {record.hash for record in arch.index.files()}
        trashed = {e.hash for e in arch.index.trash() if e.hash}
        for disk in arch.disks:
            folder = disk.data_dir / "cestino"
            if folder.exists():
                for path in folder.rglob("*"):
                    if path.is_file():
                        trashed.add(hashing.hash_file(path))
        assert before <= kept | trashed


def test_desktop_oddities_are_reported_on_upload(dev):
    dev_disks.break_disks(dev, ["desktop"])
    with open_archive(dev) as arch:
        plan = upload.analyze([dev / "desktop" / "LAGO 2026"])
        folder = plan.folders[0]
        assert sum(p.endswith(".lnk") for p in folder.ignored) == 3
        assert any(i.size == 0 for i in folder.items)
        assert scanner.kind_of("x.jpg.lnk") is None
        assert arch.complete


def test_break_refuses_unmarked_folders(tmp_path):
    with pytest.raises(dev_disks.NotDevDisks):
        dev_disks.break_disks(tmp_path, ["corrupt"])
