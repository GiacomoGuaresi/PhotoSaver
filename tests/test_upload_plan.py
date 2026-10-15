from datetime import datetime

import pytest
from conftest import put

from photosaver.core import upload
from photosaver.core.upload import CONFLICT, COPY, DUPLICATE, NEW, RENAME, SAME, SKIP
from photosaver.devtools.fake_media import make_photo


@pytest.fixture
def desktop(tmp_path):
    root = tmp_path / "desktop"
    sea = root / "MARE 2026"
    make_photo(sea / "20260810_090000.jpg", taken=datetime(2026, 8, 10, 9), seed=1)
    make_photo(sea / "20260810_100000.jpg", taken=datetime(2026, 8, 10, 10), seed=2)
    make_photo(sea / "Spiaggia" / "20260811_090000.jpg", taken=datetime(2026, 8, 11, 9), seed=3)
    (sea / "note.txt").write_text("x")
    return root


def plan_for(arch, *folders, destination=None):
    plan = upload.analyze(list(folders))
    for folder in plan.folders:
        folder.destination = (
            destination
            if destination is not None
            else upload.propose_destination(folder, upload.top_level_folders(arch))
        )
    upload.resolve(plan, arch)
    return plan


def by_name(plan):
    return {item.relative: item for item in plan.items}


def test_analyze(desktop):
    seen = []
    plan = upload.analyze([desktop / "MARE 2026"], on_progress=lambda d, t: seen.append((d, t)))
    (folder,) = plan.folders
    assert [i.relative for i in folder.items] == [
        "20260810_090000.jpg",
        "20260810_100000.jpg",
        "Spiaggia/20260811_090000.jpg",
    ]
    assert folder.ignored == ["note.txt"]
    assert folder.items[0].taken == datetime(2026, 8, 10, 9)
    assert folder.years == {2026: 3}
    assert seen[-1][0] == seen[-1][1] == sum(i.size for i in folder.items)


def test_new_folder_into_new_archive(arch, desktop):
    plan = plan_for(arch, desktop / "MARE 2026")
    assert plan.folders[0].destination == "2026/MARE 2026"
    assert {i.status for i in plan.items} == {NEW}
    assert by_name(plan)["Spiaggia/20260811_090000.jpg"].target == (
        "2026/MARE 2026/Spiaggia/20260811_090000.jpg"
    )
    assert len(plan.to_copy()) == 3
    assert plan.copy_size == sum(i.size for i in plan.items)


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        (["FOTO 2025", "FOTO 2026"], "FOTO 2026"),
        (["FOTO 2024", "FOTO 2025"], "FOTO 2026"),  # named like the others
        (["Viaggi"], "2026"),
    ],
)
def test_year_folder(arch, desktop, existing, expected):
    for name in existing:
        (arch.disks[0].archive / name).mkdir()
    plan = plan_for(arch, desktop / "MARE 2026")
    assert plan.folders[0].destination == f"{expected}/MARE 2026"


def test_whole_archive_tree_goes_to_root(arch, tmp_path):
    tree = tmp_path / "FOTO FAMIGLIA"
    make_photo(tree / "FOTO 2024" / "a.jpg", taken=datetime(2024, 1, 1), seed=1)
    make_photo(tree / "FOTO 2025" / "NEVE 2025" / "b.jpg", taken=datetime(2025, 1, 1), seed=2)
    plan = plan_for(arch, tree)
    assert plan.folders[0].destination == ""
    assert sorted(i.target for i in plan.items) == ["FOTO 2024/a.jpg", "FOTO 2025/NEVE 2025/b.jpg"]


def test_same_file_already_there_is_skipped(arch, desktop):
    data = (desktop / "MARE 2026" / "20260810_090000.jpg").read_bytes()
    put(arch, "FOTO 2026/MARE 2026/20260810_090000.jpg", data)
    plan = plan_for(arch, desktop / "MARE 2026")
    item = by_name(plan)["20260810_090000.jpg"]
    assert (item.status, item.action) == (SAME, SKIP)
    assert by_name(plan)["20260810_100000.jpg"].status == NEW


def test_name_conflict_renames(arch, desktop):
    put(arch, "FOTO 2026/MARE 2026/20260810_090000.jpg", b"another photo")
    put(arch, "FOTO 2026/MARE 2026/20260810_090000_2.jpg", b"and another")
    plan = plan_for(arch, desktop / "MARE 2026")
    item = by_name(plan)["20260810_090000.jpg"]
    assert (item.status, item.action) == (CONFLICT, RENAME)
    assert item.target == "FOTO 2026/MARE 2026/20260810_090000_3.jpg"

    item.choice = SKIP
    upload.resolve(plan, arch)
    assert (item.action, item.copied) == (SKIP, False)


def test_conflicts_ignore_letter_case(arch, desktop):
    put(arch, "foto 2026/mare 2026/20260810_090000.JPG", b"another photo")
    plan = plan_for(arch, desktop / "MARE 2026", destination="FOTO 2026/MARE 2026")
    assert by_name(plan)["20260810_090000.jpg"].status == CONFLICT


def test_file_on_disk_outside_the_index(arch, desktop):
    data = (desktop / "MARE 2026" / "20260810_090000.jpg").read_bytes()
    put(arch, "X/MARE 2026/20260810_090000.jpg", data, disks=arch.disks[:1], index=False)
    put(arch, "X/MARE 2026/20260810_100000.jpg", b"different", disks=arch.disks[1:], index=False)
    plan = plan_for(arch, desktop / "MARE 2026", destination="X/MARE 2026")
    assert by_name(plan)["20260810_090000.jpg"].status == NEW  # adopted when uploading
    item = by_name(plan)["20260810_100000.jpg"]
    assert item.status == CONFLICT
    assert item.target == "X/MARE 2026/20260810_100000_2.jpg"


def test_duplicate_elsewhere_in_archive(arch, desktop):
    data = (desktop / "MARE 2026" / "20260810_090000.jpg").read_bytes()
    put(arch, "ALBUM/copy.jpg", data)
    plan = plan_for(arch, desktop / "MARE 2026")
    item = by_name(plan)["20260810_090000.jpg"]
    assert (item.status, item.action, item.duplicates) == (DUPLICATE, SKIP, ["ALBUM/copy.jpg"])

    item.choice = COPY
    upload.resolve(plan, arch)
    assert item.copied and item.target.endswith("MARE 2026/20260810_090000.jpg")


def test_duplicate_inside_the_upload(arch, desktop, tmp_path):
    other = tmp_path / "desktop" / "ALTRO"
    other.mkdir()
    (other / "copia.jpg").write_bytes((desktop / "MARE 2026" / "20260810_090000.jpg").read_bytes())
    plan = plan_for(arch, desktop / "MARE 2026", other)
    item = by_name(plan)["copia.jpg"]
    assert item.status == DUPLICATE
    assert item.duplicates == ["2026/MARE 2026/20260810_090000.jpg"]


def test_two_folders_into_the_same_place(arch, tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    make_photo(one / "a.jpg", taken=datetime(2026, 1, 1), seed=1)
    make_photo(two / "a.jpg", taken=datetime(2026, 1, 1), seed=2)
    plan = plan_for(arch, one, two, destination="2026/X")
    first, second = plan.items
    assert (first.status, first.target) == (NEW, "2026/X/a.jpg")
    assert (second.status, second.target) == (CONFLICT, "2026/X/a_2.jpg")


def test_empty_folder(arch, tmp_path):
    (tmp_path / "empty").mkdir()
    plan = plan_for(arch, tmp_path / "empty")
    assert plan.folders[0].destination == "empty"
    assert plan.items == []
