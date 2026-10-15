import pytest

from photosaver import cli
from photosaver.core import archive
from photosaver.core.disk import open_disk
from photosaver.devtools import dev_disks


@pytest.fixture
def dev(tmp_path):
    dev_disks.create(tmp_path / "dev")
    return tmp_path / "dev"


def test_init_two_disks_and_status(dev, capsys):
    a, b = dev / "disk-a", dev / "disk-b"
    assert cli.main(["init", str(a), "--label", "A"]) == 0
    assert cli.main(["init", str(b), "--label", "B", "--join", str(a)]) == 0

    disk_a, disk_b = open_disk(a), open_disk(b)
    assert disk_a.info.archive_id == disk_b.info.archive_id
    assert disk_b.archive == b / "Foto"
    with archive.open_index(disk_a) as ia, archive.open_index(disk_b) as ib:
        assert [d.label for d in ia.disks()] == ["A", "B"]
        assert ia.revision == ib.revision

    capsys.readouterr()
    assert cli.main(["status", str(b)]) == 0
    out = capsys.readouterr().out
    assert "Disk B" in out
    assert "files    0, 0 B" in out
    assert "disk_added" in out and "archive_created" in out


def test_init_twice_fails(dev, capsys):
    assert cli.main(["init", str(dev / "disk-a"), "--label", "A"]) == 0
    assert cli.main(["init", str(dev / "disk-a"), "--label", "A"]) == 1
    assert "already a PhotoSaver disk" in capsys.readouterr().err


def test_scan(dev, capsys):
    assert cli.main(["scan", str(dev / "desktop" / "LAGO 2026")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("16 media files")
    assert "3 ignored (not photos or videos):" in out
    assert "LAGO 2026" not in out  # paths are relative


def test_scan_long_lists_are_cut(tmp_path, capsys):
    for n in range(cli.SHOWN + 3):
        (tmp_path / f"{n}.txt").write_text("x")
    cli.main(["scan", str(tmp_path)])
    assert "… and 3 more" in capsys.readouterr().out


def test_errors_are_reported(tmp_path, capsys):
    assert cli.main(["status", str(tmp_path)]) == 1
    assert cli.main(["scan", str(tmp_path / "missing")]) == 1
    err = capsys.readouterr().err
    assert "not a PhotoSaver disk" in err and "not a folder" in err


@pytest.mark.parametrize(("size", "text"), [(0, "0 B"), (1500, "1.5 KB"), (4.2e9, "4.2 GB")])
def test_size(size, text):
    assert cli._size(size) == text


def test_upload(dev, capsys):
    a, b = str(dev / "disk-a"), str(dev / "disk-b")
    cli.main(["init", a, "--label", "A"])
    cli.main(["init", b, "--label", "B", "--join", a])
    sea = str(dev / "desktop" / "MARE 2026")
    capsys.readouterr()

    assert cli.main(["upload", sea, "--disks", a, b]) == 0
    out = capsys.readouterr().out
    assert "MARE 2026  →  2026/MARE 2026" in out
    assert "To copy: 33 files" in out
    assert not (dev / "disk-a" / "Foto" / "2026").exists()

    assert cli.main(["upload", sea, "--disks", a, b, "--apply", "--delete-sources"]) == 0
    out = capsys.readouterr().out
    assert "Copied and verified on 2 disks: 33 files" in out
    assert "Deleted 33 originals" in out
    assert (dev / "disk-b" / "Foto" / "2026" / "MARE 2026" / "Spiaggia").is_dir()


def test_check(dev, capsys):
    a, b = str(dev / "disk-a"), str(dev / "disk-b")
    cli.main(["init", a, "--label", "A"])
    cli.main(["init", b, "--label", "B", "--join", a])
    cli.main(["upload", str(dev / "desktop" / "LAGO 2026"), "--disks", a, b, "--apply"])
    capsys.readouterr()

    assert cli.main(["check", "--disks", a, b]) == 0
    assert "16 files in the index, 0 differences" in capsys.readouterr().out

    next((dev / "disk-b" / "Foto").rglob("*.jpg")).unlink()
    assert cli.main(["check", "--disks", a, b]) == 1
    out = capsys.readouterr().out
    assert "missing   B  " in out
    assert ": (to choose)   [copy, delete_all, known]" in out

    assert cli.main(["check", "--disks", a]) == 0
    assert "Not connected: B" in capsys.readouterr().out

    assert cli.main(["check", "--disks", a, "--full"]) == 0
    assert "16 files in the index, 0 differences" in capsys.readouterr().out
