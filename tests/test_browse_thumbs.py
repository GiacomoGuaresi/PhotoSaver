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


def test_thumbnails_saved_on_every_disk(tmp_path):
    a, b = tmp_path / "a" / ".photosaver", tmp_path / "b" / ".photosaver"
    photo = make_photo(tmp_path / "p.jpg", size=(800, 600))
    data = thumbs.thumbnail([a, b], [tmp_path / "missing.jpg", photo], "ab12")
    assert size_of(data) == (320, 240)
    for data_dir in (a, b):
        assert thumbs.cache_path(data_dir, "ab12") == data_dir / "miniature" / "ab" / "ab12.jpg"
        assert thumbs.cache_path(data_dir, "ab12").read_bytes() == data
    photo.unlink()  # now read from the disks
    assert thumbs.thumbnail([a, b], [photo], "ab12") == data
    assert thumbs.thumbnail([a], [photo], "cd34") is None


def test_unwritable_disk_is_skipped(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    thumbs.store([blocker, tmp_path / "ok"], "ab12", b"jpeg")  # blocker is not a folder
    assert thumbs.read_cached([blocker, tmp_path / "ok"], "ab12") == b"jpeg"


def test_fill_missing(tmp_path):
    archive = tmp_path / "Foto"
    make_photo(archive / "x" / "a.jpg")
    make_photo(archive / "b.jpg", seed=2)
    (archive / "c.mp4").write_bytes(b"video")
    records = [FileRecord("x/a.jpg", 1, 0, "aa11"), FileRecord("b.jpg", 1, 0, "bb22"),
               FileRecord("c.mp4", 1, 0, "cc33")]  # fmt: skip
    data_dir = tmp_path / ".photosaver"
    assert len(thumbs.missing([data_dir], records)) == 2
    assert thumbs.fill([data_dir], [archive], records) == 2
    assert thumbs.missing([data_dir], records) == []
    assert thumbs.fill([data_dir], [archive], records, should_stop=lambda: True) == 0


def test_copy_problems(arch):
    from conftest import put

    from photosaver.core import check, resolve

    put(arch, "FOTO/a.jpg", b"a")
    put(arch, "FOTO/sub/b.jpg", b"b")
    put(arch, "c.jpg", b"c")
    a, b = arch.disks
    with arch.index.transaction():
        arch.index.set_copy("FOTO/a.jpg", b.id, "corrupt")
    arch.path_on(a, "FOTO/sub/b.jpg").unlink()
    put(arch, "new.jpg", b"n", disks=[a], index=False)
    issues = resolve.build_issues(check.quick_check(arch), arch)

    problems = browse.copy_problems(arch.index, [a.id, b.id], issues)
    assert problems == {"FOTO/a.jpg": {b.id: "corrupt"}, "FOTO/sub/b.jpg": {a.id: "missing"}}
    assert browse.folder_problems(problems) == {"": 2, "FOTO": 2, "FOTO/sub": 1}
