import time

import pytest

from photosaver.core import archive as archive_mod
from photosaver.core import check, resolve
from photosaver.core.disk import open_disk
from photosaver.devtools import dev_disks
from photosaver.ui import app as app_mod
from photosaver.ui.check_flow import ChooseCheckScreen, ResultsScreen
from photosaver.ui.controller import HOME
from photosaver.ui.issues import Texts, group_issues


@pytest.fixture
def dev(tmp_path):
    root = tmp_path / "dev-disks"
    dev_disks.setup(root)
    return root


def open_dev(dev):
    return archive_mod.Archive.open([open_disk(dev / "disk-a"), open_disk(dev / "disk-b")])


def groups_of(dev):
    with open_dev(dev) as arch:
        issues = resolve.build_issues(check.full_check(arch), arch)
        labels = {d.id: d.label for d in arch.disks}
    return group_issues(issues, labels)


def test_renamed_folder_is_one_line(qapp, dev):
    dev_disks.break_disks(dev, ["move"])
    (group,) = groups_of(dev)
    text = Texts().title(group, ["A", "B"])
    assert "renamed" in text and "(rinominata)" in text and "Disk 2" in text
    assert len(group.issues) > 1
    assert Texts().option(group, group.proposed, ["A", "B"]) == "Do the same on Disk 1"


def test_groups_and_texts(qapp, dev):
    dev_disks.break_disks(dev, ["corrupt", "delete", "add", "edit"], seed=2)
    groups = groups_of(dev)
    texts = Texts()
    titles = [texts.title(g, ["A", "B"]) for g in groups]
    assert titles[0].startswith("1 photo") and groups[0].proposed is None  # to decide first
    assert any("damaged on Disk 2" in t for t in titles)
    assert any("added without the app, only on Disk 1" in t for t in titles)
    for group in groups:
        for option in group.options:
            assert texts.option(group, option, ["A", "B"])


@pytest.fixture
def ui(qtbot, dev):
    app_mod.create_application([])
    window, controller = app_mod.build([dev / "disk-a", dev / "disk-b"])
    qtbot.addWidget(window)
    yield window, controller
    controller.shutdown()


def test_break_everything_and_fix_from_the_home(qtbot, ui, dev):
    window, controller = ui
    dev_disks.break_disks(dev, list(dev_disks.SCENARIOS), seed=1)
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    home = window.current
    assert home.status.role == "warning"
    home.status.action.click()
    qtbot.waitUntil(lambda: isinstance(window.current, ResultsScreen), timeout=10000)
    results = window.current
    assert results.rows and not results.undecided.isHidden()
    not_now = [
        b for b in results.footer.findChildren(type(results.primary)) if b.text() == "Not now"
    ]
    assert not_now and not not_now[0].isHidden()
    for row in results.rows:
        if row.group.choice is None:
            row.choice.setCurrentIndex(1)  # the first real action
    assert results.undecided.isHidden() and results.primary.isEnabled()
    results.primary.click()
    qtbot.waitUntil(
        lambda: isinstance(window.current, ResultsScreen) and not window.current.groups,
        timeout=20000,
    )
    # the quick check after fixing is clean; only the thorough one sees silent damage
    with open_dev(dev) as arch:
        assert [d.kind for d in check.full_check(arch).differences] == [check.CORRUPT]
    window.current.primary.click()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    assert window.current.status.role == "safe"


def test_thorough_check_from_the_tile(qtbot, ui, dev):
    window, controller = ui
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    dev_disks.break_disks(dev, ["corrupt"])  # only a thorough check sees it
    window.current.check.click()
    choose = window.current
    assert isinstance(choose, ChooseCheckScreen) and choose.quick.isChecked()
    choose.full.setChecked(True)
    choose.primary.click()
    qtbot.waitUntil(lambda: isinstance(window.current, ResultsScreen), timeout=20000)
    (row,) = window.current.rows
    assert row.group.kind == resolve.I_CORRUPT and row.group.choice is not None
    row.toggle.click()
    assert not row.files.isHidden()


def test_stop_thorough_check(qtbot, ui, dev, monkeypatch):
    window, controller = ui
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    real = check.full_check

    def slow(archive, *, on_progress=None, should_stop=None):
        deadline = time.monotonic() + 5
        while not should_stop() and time.monotonic() < deadline:
            time.sleep(0.01)
        return real(archive, on_progress=on_progress, should_stop=should_stop)

    monkeypatch.setattr(check, "full_check", slow)
    window.current.check.click()
    window.current.full.setChecked(True)
    window.current.primary.click()
    busy = window.current
    busy.footer.findChildren(type(busy.back_button))[-1].click()
    qtbot.waitUntil(lambda: window.current.title.text() == "Check stopped", timeout=10000)
    window.current.primary.click()
    qtbot.waitUntil(lambda: controller.mode == HOME)
