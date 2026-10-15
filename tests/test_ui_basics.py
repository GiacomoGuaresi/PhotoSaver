import pytest
from PySide6.QtCore import QLocale

from photosaver.ui import app as app_mod
from photosaver.ui import theme
from photosaver.ui.home import HomeScreen
from photosaver.ui.main_window import MainWindow
from photosaver.ui.screen import Screen


@pytest.fixture
def window(qtbot):
    app_mod.create_application([])
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_theme_tokens_are_all_replaced():
    assert "@" not in theme.style_sheet()


def test_every_icon_exists(qapp):
    for path in theme.ICONS_DIR.glob("*.svg"):
        assert not theme.icon(path.stem).isNull()


def test_navigation(window):
    home = window.reset(HomeScreen())
    assert window.current is home and home.back_button.isHidden()

    step = window.open(Screen("Step", "What to do"))
    assert window.current is step and not step.back_button.isHidden()
    step.back_button.click()
    assert window.current is home

    other = window.open(Screen("Other"))
    window.replace(Screen("Instead"))
    assert window.stack.count() == 2 and window.current.title.text() == "Instead"
    window.back()
    window.back()  # nothing below home
    assert window.current is home
    assert other is not window.current


def test_screen_footer(qtbot):
    screen = Screen("Title")
    qtbot.addWidget(screen)
    assert not screen.footer.isVisibleTo(screen)
    clicked = []
    button = screen.set_primary("Go", lambda: clicked.append(1))
    assert screen.footer.isVisibleTo(screen)
    button.click()
    assert clicked == [1]
    screen.add_secondary("Other", lambda: None)
    assert screen.primary is button


def test_home_read_only(qtbot):
    home = HomeScreen()
    qtbot.addWidget(home)
    home.set_read_only(True)
    assert not home.add.isEnabled() and home.browse.isEnabled() and not home.check.isEnabled()
    home.set_status("Look", "warning")
    assert home.status.role == "warning"


def test_disk_bar(window):
    window.disk_bar.set_disks([("Disk 1", True, "connected"), ("Disk 2", False, "not connected")])
    assert window.disk_bar._disks.count() == 2


def test_italian_translation_loads(qtbot):
    app = app_mod.create_application([])
    translators = app_mod.install_translations(app, QLocale(QLocale.Language.Italian))
    try:
        assert any(t.language().startswith("it") for t in translators)
    finally:
        for t in translators:
            app.removeTranslator(t)


def test_every_text_has_an_italian_translation():
    import xml.etree.ElementTree as ET

    ts = app_mod.I18N_DIR / "photosaver_it.ts"
    for message in ET.parse(ts).getroot().iter("message"):
        translation = message.find("translation")
        assert translation.get("type") != "unfinished", message.find("source").text
