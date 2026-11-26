import base64

import pytest

from repolens.cover import load_cover, validate_cover
from repolens.scanner import ScanError


METADATA = {"alt": "Illustration of an example project.", "evidence_ids": ["project-purpose"]}
JPEG_HEADER = bytes.fromhex("ffd8 ffc0 0011 08 0300 0480 03 01 22 00 02 11 01 03 11 01 ffd9")


def test_cover_embeds_local_jpeg_and_returns_citations(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(JPEG_HEADER)
    cover = load_cover(tmp_path, METADATA)
    assert (cover["width"], cover["height"]) == (1152, 768)
    assert base64.b64decode(cover["data"]) == JPEG_HEADER
    assert validate_cover(cover) == {"project-purpose"}


def test_cover_rejects_a_symlink(tmp_path):
    outside = tmp_path / "another.jpg"
    outside.write_bytes(JPEG_HEADER)
    (tmp_path / "cover.jpg").symlink_to(outside)
    with pytest.raises(ScanError, match="Save the generated image"):
        load_cover(tmp_path, METADATA)


@pytest.mark.parametrize("change, message", [
    ({"width": 4096}, "dimensions do not match"),
    ({"data": "!"}, "valid base64"),
    ({"data": base64.b64encode(b"<svg/>").decode()}, "static JPEG"),
    ({"evidence_ids": []}, "source citations"),
])
def test_cover_rejects_invalid_embedded_art(change, message):
    cover = dict(METADATA, width=1152, height=768, data=base64.b64encode(JPEG_HEADER).decode())
    with pytest.raises(ScanError, match=message):
        validate_cover({**cover, **change})
