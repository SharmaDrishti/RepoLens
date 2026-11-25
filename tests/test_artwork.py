import struct
import zlib

import pytest

from repolens.artwork import artwork_ids, load_artwork, validate_artwork, validate_distinct_artwork
from repolens.scanner import ScanError


def chunk(kind, data=b""):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(color_type=6, animated=False):
    header = struct.pack(">IIBBBBB", 1, 1, 8, color_type, 0, 0, 0)
    control = chunk(b"acTL", struct.pack(">II", 1, 0)) if animated else b""
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + control
            + chunk(b"IDAT", zlib.compress(bytes(5 if color_type == 6 else 4))) + chunk(b"IEND"))


def test_reused_artwork_is_embedded_once(tmp_path):
    marker = {"shape": "sprite", "asset": "music-file"}
    ids = artwork_ids([{"id": "playback", "kind": "illustrate", "objects": [marker, marker]}])
    directory = tmp_path / "artwork"
    directory.mkdir()
    (directory / "music-file.png").write_bytes(png())
    packed = load_artwork(tmp_path, ids)
    assert list(packed) == ["music-file"]
    validate_artwork(packed, ids)
    with pytest.raises(ScanError, match="referenced pieces"):
        validate_artwork(packed, {"missing"})


@pytest.mark.parametrize("image", [png(color_type=2), png(animated=True), png()[:-8]])
def test_rejects_opaque_animated_or_incomplete_artwork(tmp_path, image):
    directory = tmp_path / "artwork"
    directory.mkdir()
    (directory / "music-file.png").write_bytes(image)
    with pytest.raises(ScanError, match="still PNG with transparency"):
        load_artwork(tmp_path, {"music-file"})


def test_distinct_reports_reject_cross_section_reuse_and_renamed_copies(tmp_path):
    directory = tmp_path / "artwork"
    directory.mkdir()
    for name in ("cover", "renamed"):
        (directory / f"{name}.png").write_bytes(png())
    marker = {"shape": "sprite", "asset": "cover"}
    story = {
        "artwork_policy": "distinct",
        "hero": {"objects": [marker, marker]},
        "section_art": {},
        "artwork": load_artwork(tmp_path, {"cover", "renamed"}),
    }
    validate_distinct_artwork(story)
    for asset in ("cover", "renamed"):
        story["section_art"] = {"learn-setup": {"asset": asset}}
        with pytest.raises(ScanError, match="repeats between opening graphic and supporting art for learn-setup"):
            validate_distinct_artwork(story)
