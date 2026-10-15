"""The engine on real exFAT volumes (letter case, 10 ms dates, renames).

Skipped unless PHOTOSAVER_EXFAT lists two exFAT mount points: see scripts/exfat_loop.py.
Each test works in its own folders on the two volumes and removes them at the end.
"""

import os
import shutil
import uuid
from pathlib import Path

import pytest

from photosaver.core import archive, check, edit, hashing, resolve, safecopy, upload
from photosaver.core.resolve import KNOWN
from photosaver.devtools import dev_disks
from photosaver.devtools.fake_media import make_photo

VOLUMES = [Path(p) for p in os.environ.get("PHOTOSAVER_EXFAT", "").split(os.pathsep) if p]
pytestmark = pytest.mark.skipif(
    "PHOTOSAVER_EXFAT" not in os.environ, reason="needs two exFAT volumes"
)


def test_two_volumes_given():
    assert len(VOLUMES) >= 2 and all(v.is_dir() for v in VOLUMES), "PHOTOSAVER_EXFAT"


@pytest.fixture
def roots():
    name = f"test-{uuid.uuid4().hex[:8]}"
    folders = [volume / name for volume in VOLUMES[:2]]
    for folder in folders:
        folder.mkdir()
    yield folders
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)


@pytest.fixture
def arch(roots):
    a = archive.create_archive(roots[0], label="A", archive_dir="Foto")
    b = archive.join_archive(a, roots[1], label="B")
    with archive.Archive.open([a, b]) as opened:
        yield opened


def test_letter_case_is_ignored(roots):
    (roots[0] / "Foto.jpg").write_bytes(b"x")
    assert (roots[0] / "FOTO.JPG").exists()


def test_safe_copy_keeps_the_date_to_10_ms(tmp_path, roots):
    source = make_photo(tmp_path / "a.jpg")
    os.utime(source, ns=(1_700_000_000_123_456_789, 1_700_000_000_123_456_789))
    target = roots[0] / "a.jpg"
    safecopy.safe_copy(source, [target])
    assert abs(target.stat().st_mtime_ns - source.stat().st_mtime_ns) < 10_000_000
    assert hashing.hash_file(target) == hashing.hash_file(source)


def test_upload_and_checks(tmp_path, arch):
    dev_disks.create(tmp_path / "dev")
    plan = upload.analyze([tmp_path / "dev" / "desktop" / "MARE 2026"])
    plan.folders[0].destination = "FOTO 2026/MARE 2026"
    upload.resolve(plan, arch)
    assert len(upload.apply(plan, arch).copied) == 33
    assert check.quick_check(arch).clean
    assert check.full_check(arch).clean


def test_name_conflicts_ignore_case(tmp_path, arch):
    make_photo(arch.path_on(arch.disks[0], "foto/a.jpg"), seed=1)
    make_photo(tmp_path / "up" / "A.JPG", seed=2)
    plan = upload.analyze([tmp_path / "up"])
    plan.folders[0].destination = "FOTO"
    upload.resolve(plan, arch)
    assert plan.items[0].status == upload.CONFLICT


def test_rename_only_letter_case(tmp_path, arch):
    make_photo(tmp_path / "up" / "a.jpg")
    plan = upload.analyze([tmp_path / "up"])
    plan.folders[0].destination = "mare"
    upload.resolve(plan, arch)
    upload.apply(plan, arch)
    edit.rename(arch, "mare", "MARE")
    for disk in arch.disks:
        assert os.listdir(disk.archive) == ["MARE"]
    assert check.full_check(arch).clean


def test_break_everything_then_fix(tmp_path, roots):
    root = tmp_path / "dev-disks"
    dev_disks.setup(root, seed=3)
    for name, target in zip(("disk-a", "disk-b"), roots, strict=True):
        shutil.copytree(root / name, target, dirs_exist_ok=True)
    shutil.rmtree(root / "disk-a")
    shutil.rmtree(root / "disk-b")
    for name, target in zip(("disk-a", "disk-b"), roots, strict=True):
        (root / name).symlink_to(target)  # break_disks works on dev-disks/disk-*
    dev_disks.break_disks(root, list(dev_disks.SCENARIOS), seed=1)
    disks = [archive.open_disk(r) for r in roots]
    with archive.Archive.open(disks) as arch:
        for _ in range(3):
            issues = resolve.build_issues(check.full_check(arch), arch)
            if not issues:
                break
            for issue in issues:
                if issue.proposed is None:
                    issue.choice = next((o for o in issue.options if o.action != KNOWN), None)
            assert resolve.apply(issues, arch).failed == []
        assert check.full_check(arch).clean
