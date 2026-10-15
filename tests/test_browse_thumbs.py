import io

import pytest
from PIL import Image

from photosaver.core import browse, thumbs
from photosaver.core.index import FileRecord
from photosaver.devtools.fake_media import make_file, make_photo


def rec(path):
    return FileRecord(path, 1, 0, "h")


def test_build_tree():
    root = browse.build_tree(
        [rec("FOTO 2026/MARE 2026/b.jpg"), rec("FOTO 2026/MARE 2026/a.jpg"), rec("sciolta.jpg"),
         rec("FOTO 2025/c.jpg")],
        folders=["FOTO 2026/vuota", "FOTO 2025"],
    )  # fmt: skip
    assert [f.name for f in root.children()] == ["FOTO 2025", "FOTO 2026"]
    assert [r.path for r in root.files] == ["sciolta.jpg"]
    sea = root.find("FOTO 2026/MARE 2026")
    assert sea.path == "FOTO 2026/MARE 2026"
    assert [r.path.rsplit("/", 1)[1] for r in sea.files] == ["a.jpg", "b.jpg"]
    assert root.find("FOTO 2026").count == 2 and root.count == 4
    assert root.find("FOTO 2026/vuota").count == 0
    assert root.find("nope") is None
    assert [f.path for f in root.walk()][:2] == ["", "FOTO 2025"]


def test_disk_folders(tmp_path):
    (tmp_path / "A" / "B").mkdir(parents=True)
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "file.jpg").write_bytes(b"x")
    assert sorted(browse.disk_folders(tmp_path)) == ["A", "A/B"]


def size_of(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "JPEG"
        return image.size


def test_thumbnail_is_small(tmp_path):
    path = make_photo(tmp_path / "a.jpg", size=(1200, 800))
    assert size_of(thumbs.make_thumbnail(path)) == (320, 213)


def test_thumbnail_follows_orientation(tmp_path):
    path = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° when showing
    Image.new("RGB", (600, 300), "red").save(path, exif=exif)
    width, height = size_of(thumbs.make_thumbnail(path))
    assert height > width


def test_thumbnail_of_heic(tmp_path):
    path = tmp_path / "a.heic"
    Image.new("RGB", (640, 480), "blue").save(path, "HEIF")
    assert size_of(thumbs.make_thumbnail(path)) == (320, 240)


@pytest.mark.parametrize("name", ["clip.mp4", "broken.jpg", "zero.jpg"])
def test_no_thumbnail(tmp_path, name):
    path = make_file(tmp_path / name, b"" if name == "zero.jpg" else b"not an image")
    with pytest.raises(thumbs.NoThumbnail):
        thumbs.make_thumbnail(path)


def test_can_have_thumbnail():
    assert thumbs.can_have_thumbnail("a.JPG") and thumbs.can_have_thumbnail("a.nef")
    assert not thumbs.can_have_thumbnail("a.mov")
