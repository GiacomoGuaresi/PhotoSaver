import pytest

from photosaver.core import archive, detect
from photosaver.ui import app as app_mod
from photosaver.ui.connect import ConnectScreen
from photosaver.ui.controller import CONNECT, HOME
from photosaver.ui.home import HomeScreen
from photosaver.ui.prepare import ChooseDiskScreen, ConfirmScreen, IntroScreen, PreparedScreen


@pytest.fixture
def setup(qtbot, tmp_path):
    roots = []
    for name in ("usb-1", "usb-2"):
        (tmp_path / name).mkdir()
        roots.append(tmp_path / name)
    app_mod.create_application([])
    window, controller = app_mod.build(roots)
    qtbot.addWidget(window)
    controller.start()
    yield window, controller, roots
    controller.session.stop()
    for worker in list(controller._workers):
        worker.wait(5000)


def test_new_disk_is_proposed(setup):
    window, controller, _ = setup
    screen = window.current
    assert isinstance(screen, ConnectScreen)
    assert screen.message.role == "warning" and not screen.message.action.isHidden()


def test_prepare_both_disks(qtbot, setup):
    window, controller, roots = setup
    window.current.message.action.click()
    assert isinstance(window.current, IntroScreen)
    window.current.primary.click()

    choose = window.current
    assert isinstance(choose, ChooseDiskScreen)
    assert choose.chosen is None and not choose.primary.isEnabled()  # two candidates
    next(iter(choose._choices)).setChecked(True)
    assert choose.chosen == roots[0]
    choose.primary.click()

    confirm = window.current
    assert isinstance(confirm, ConfirmScreen) and not confirm.primary.isEnabled()
    confirm.agree.setChecked(True)
    confirm.primary.click()

    ready = window.current
    assert isinstance(ready, PreparedScreen) and ready.back_button.isHidden()
    assert detect.scan_roots(roots).disks[0].label == "A"
    controller.session.refresh()
    assert window.current is ready  # disk changes don't interrupt the flow
    ready.primary.click()

    choose = window.current
    assert choose.chosen == roots[1]  # the only one left
    choose.primary.click()
    window.current.agree.setChecked(True)
    window.current.primary.click()
    assert isinstance(window.current, PreparedScreen)
    window.current.primary.click()

    qtbot.waitUntil(lambda: controller.mode == HOME and isinstance(window.current, HomeScreen))
    disks = detect.scan_roots(roots).disks
    assert sorted(d.label for d in disks) == ["A", "B"]
    assert disks[0].info.archive_id == disks[1].info.archive_id
    with archive.open_index(disks[1]) as index:
        assert len(index.disks()) == 2


def test_back_from_intro(setup):
    window, controller, _ = setup
    window.current.first_time.click()
    assert isinstance(window.current, IntroScreen)
    window.current.back_button.click()
    assert controller.mode == CONNECT and isinstance(window.current, ConnectScreen)
    assert not controller.busy


def test_choose_waits_for_a_disk(qtbot, setup, tmp_path):
    window, controller, roots = setup
    (roots[0] / "file.txt").write_text("x")
    (roots[1] / "file.txt").write_text("x")
    controller.session.refresh()
    window.current.first_time.click()
    window.current.primary.click()
    choose = window.current
    assert not choose.waiting.isHidden() and choose.note.text()
    (roots[0] / "file.txt").unlink()
    controller.session.refresh()
    assert choose.chosen == roots[0] and choose.waiting.isHidden()
