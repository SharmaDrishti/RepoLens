"""Load and validate a repository lesson's embedded static cover."""

import base64
import binascii

from .scanner import ScanError

MAX_BYTES = 2 * 1024 * 1024
METADATA = {"alt", "evidence_ids"}


def cover_references(cover):
    if not isinstance(cover, dict) or not isinstance(cover.get("alt"), str):
        raise ScanError("The cover needs an accessible description and source citations.")
    alt = cover["alt"]
    ids = cover.get("evidence_ids")
    if (not alt.strip() or len(alt) > 300 or not isinstance(ids, list) or not 1 <= len(ids) <= 8
            or any(not isinstance(ref, str) or not ref for ref in ids)):
        raise ScanError("Use a short cover description and one to eight source citations.")
    return set(ids)


def jpeg_size(image):
    if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
        raise ScanError("Use a static JPEG cover image.")
    cursor = 2
    while cursor + 4 <= len(image) and image[cursor] == 255:
        marker = image[cursor + 1]
        if marker == 255:
            cursor += 1
            continue
        size = int.from_bytes(image[cursor + 2:cursor + 4], "big")
        if size < 2 or cursor + 2 + size > len(image):
            break
        if marker in (0xc0, 0xc1, 0xc2) and size >= 8:
            height = int.from_bytes(image[cursor + 5:cursor + 7], "big")
            width = int.from_bytes(image[cursor + 7:cursor + 9], "big")
            if 1 <= width <= 4096 and 1 <= height <= 4096:
                return width, height
            break
        if marker == 0xda:
            break
        cursor += size + 2
    raise ScanError("The cover JPEG must have readable dimensions up to 4096 pixels per side.")


def load_cover(folder, metadata):
    if not isinstance(metadata, dict) or metadata.keys() != METADATA:
        raise ScanError("Supply cover alt text and evidence IDs.")
    cover_references(metadata)
    asset = folder / "cover.jpg"
    if asset.is_symlink() or not asset.is_file():
        raise ScanError("Save the generated image as cover.jpg in the report folder.")
    with asset.open("rb") as source:
        image = source.read(MAX_BYTES + 1)
    if len(image) > MAX_BYTES:
        raise ScanError("Compress the cover JPEG to 2 MB or smaller.")
    width, height = jpeg_size(image)
    return {**metadata, "width": width, "height": height, "data": base64.b64encode(image).decode("ascii")}


def validate_cover(cover):
    refs = cover_references(cover)
    data = cover.get("data")
    if (cover.keys() != METADATA | {"data", "width", "height"}
            or not isinstance(data, str) or len(data) > 4 * ((MAX_BYTES + 2) // 3)):
        raise ScanError("The embedded JPEG cover is missing or too large.")
    try:
        image = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ScanError("The embedded cover needs valid base64 image data.") from error
    if len(image) > MAX_BYTES:
        raise ScanError("Compress the cover JPEG to 2 MB or smaller.")
    width, height = jpeg_size(image)
    if any(type(cover[key]) is not int for key in ("width", "height")) or (width, height) != (cover["width"], cover["height"]):
        raise ScanError("The embedded cover dimensions do not match the JPEG.")
    return refs
