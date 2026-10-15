import pytest
from conftest import put

from photosaver.core import archive as archive_mod
from photosaver.core import check, resolve
from photosaver.ui import app as app_mod
from photosaver.ui.check_flow import ResultsScreen
from photosaver.ui.connect import BusyScreen, ConnectScreen, DoneScreen
from photosaver.ui.controller import CONNECT, HOME, READ_ONLY
from photosaver.ui.home import HomeScreen


@pytest.fixture
def roots():
    return []


@pytest.fixture
def ui(qtbot, roots):
    app_mod.create_application([])
    window, controller = app_mod.build(roots)
    qtbot.addWidget(window)
    yield window, controller
    controller.session.stop()
    for worker in list(controller._workers):
        worker.wait(5000)


def start_and_wait_home(qtbot, ui):
    window, controller = ui
    controller.start()
    qtbot.waitUntil(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))
    return window.current


def test_nothing_connected(ui):
    window, controller = ui
    controller.start()
    assert controller.mode == CONNECT
    screen = window.current
    assert isinstance(screen, ConnectScreen)
    assert not screen.one_disk.isEnabled() and screen.message.isHidden()


def test_both_disks_safe(qtbot, ui, roots, two_disks):
    roots.extend(d.root for d in two_disks)
    home = start_and_wait_home(qtbot, ui)
    assert home.status.role == "safe"
    assert home.add.isEnabled()
    assert ui[0].disk_bar._disks.count() == 2


def test_one_disk_read_only(qtbot, ui, roots, two_disks):
    window, controller = ui
    roots.append(two_disks[0].root)
    controller.start()
    screen = window.current
    assert isinstance(screen, ConnectScreen) and screen.one_disk.isEnabled()
    screen.one_disk.click()
    assert controller.mode == READ_ONLY
    home = window.current
    assert home.status.role == "warning" and "2" in home.status.label.text()
    assert not home.add.isEnabled() and home.browse.isEnabled()

    roots.append(two_disks[1].root)  # the second disk arrives
    controller.session.refresh()
    qtbot.waitUntil(lambda: controller.mode == HOME)
    assert window.current.add.isEnabled()


def test_unplugged_disk_goes_back_to_connect(qtbot, ui, roots, two_disks):
    window, controller = ui
    roots.extend(d.root for d in two_disks)
    start_and_wait_home(qtbot, ui)
    roots.pop()
    controller.session.refresh()
    assert controller.mode == CONNECT and isinstance(window.current, ConnectScreen)


def test_problems_found(qtbot, ui, roots, arch):
    put(arch, "FOTO/a.jpg", b"photo")
    arch.path_on(arch.disks[1], "FOTO/a.jpg").unlink()
    roots.extend(d.root for d in arch.disks)
    home = start_and_wait_home(qtbot, ui)
    assert home.status.role == "warning"
    assert not home.status.action.isHidden()
    home.status.action.click()  # "Let's look together": straight to the results
    window = ui[0]
    qtbot.waitUntil(lambda: isinstance(window.current, ResultsScreen))


def test_interrupted_action_is_fixed(qtbot, ui, roots, arch):
    put(arch, "FOTO/a.jpg", b"photo")
    arch.path_on(arch.disks[1], "FOTO/a.jpg").unlink()
    issue = resolve.build_issues(check.quick_check(arch), arch)[0]
    issue.choice = resolve.Option(resolve.COPY)
    arch.index.begin(resolve.JOURNAL_OPERATION, resolve._to_journal(issue))
    arch.sync_indexes()
    roots.extend(d.root for d in arch.disks)

    home = start_and_wait_home(qtbot, ui)
    assert home.status.role == "warning" and home.status.action.text()
    home.status.action.click()
    window, controller = ui
    qtbot.waitUntil(lambda: controller.mode == HOME and window.current.status.role == "safe")
    assert arch.path_on(arch.disks[1], "FOTO/a.jpg").exists()


def test_mixed_and_new_disks(qtbot, ui, roots, tmp_path, two_disks):
    window, controller = ui
    (tmp_path / "x").mkdir()
    other = archive_mod.create_archive(tmp_path / "x", label="A", archive_dir="Foto")
    roots.extend([two_disks[0].root, other.root])
    controller.start()
    assert window.current.message.role == "danger"

    roots.clear()
    (tmp_path / "new").mkdir()
    roots.append(tmp_path / "new")
    controller.session.refresh()
    screen = window.current
    assert screen.message.role == "warning" and not screen.message.action.isHidden()


def test_done(qtbot, ui, roots, two_disks):
    window, controller = ui
    roots.extend(d.root for d in two_disks)
    start_and_wait_home(qtbot, ui)
    window.disk_bar.done.click()
    assert isinstance(window.current, DoneScreen)
    roots.pop()
    controller.session.refresh()
    assert isinstance(window.current, DoneScreen)


def test_busy_screen_progress(qtbot):
    screen = BusyScreen("Working")
    qtbot.addWidget(screen)
    screen.set_progress(5, 10, "half")
    assert screen.bar.value() == 500 and screen.detail.text() == "half"
