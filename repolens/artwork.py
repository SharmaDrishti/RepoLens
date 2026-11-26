"""Embed static PNG artwork used by the lesson renderer."""

import base64
import binascii
import re

from .scanner import ScanError

ASSET_ID = re.compile(r"[a-z][a-z0-9-]{0,31}")
MAX_FILE_BYTES = 750 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_ASSETS = 20


def section_art_references(section_art, chapter_count, lessons, scenes=()):
    targets = {"learn-setup", "learn-source"}
    targets.update(f"learn-setup-{group}" for group in (
        "requirements", "install", "first_run", "expected_output", "gotchas"
    ))
    targets.update(f"chapter-{index}" for index in range(chapter_count))
    targets.update(f"chapter-{index}-{claim}" for index, scene in enumerate(scenes) for claim in scene["claim_ids"])
    targets.update(f"lesson-{lesson['id']}" for lesson in lessons)
    if not isinstance(section_art, dict) or not section_art.keys() <= targets:
        raise ScanError("Supporting artwork must target an existing report section or lesson.")
    refs = set()
    for art in section_art.values():
        if (not isinstance(art, dict) or art.keys() != {"asset", "alt", "evidence_ids"}
                or not isinstance(art["asset"], str) or not ASSET_ID.fullmatch(art["asset"])
                or not isinstance(art["alt"], str) or not art["alt"].strip() or len(art["alt"]) > 300
                or not isinstance(art["evidence_ids"], list) or not 1 <= len(art["evidence_ids"]) <= 8
                or any(not isinstance(ref, str) or not ref or len(ref) > 300 for ref in art["evidence_ids"])):
            raise ScanError("Supporting artwork needs an asset ID, short alt text, and pinned evidence IDs.")
        refs.update(art["evidence_ids"])
    return refs


def artwork_uses(lessons, hero=None, guide=None, section_art=None):
    def sprites(drawings):
        return {mark["asset"] for drawing in drawings for mark in drawing["objects"] if mark["shape"] == "sprite"}

    if hero is not None:
        yield "opening graphic", sprites([hero])
    if guide is not None:
        yield "guided story", sprites(guide["chapters"])
    for lesson in lessons:
        key = f"lesson-{lesson['id']}"
        if lesson["kind"] in ("illustrate", "experiment", "reveal"):
            yield key, sprites([lesson])
        elif lesson["kind"] == "guide":
            yield key, sprites(lesson["guide"]["chapters"])
        elif lesson["kind"] == "picture":
            yield key, {view["asset"] for view in lesson["views"]}
    for section, art in (section_art or {}).items():
        yield f"supporting art for {section}", {art["asset"]}


def artwork_ids(lessons, hero=None, guide=None, section_art=None):
    return {asset for _, assets in artwork_uses(lessons, hero, guide, section_art) for asset in assets}


def validate_distinct_artwork(story):
    """Catch reused illustrations even if the same PNG was given a new name."""
    if "artwork_policy" not in story:
        return
    if story["artwork_policy"] != "distinct":
        raise ScanError("The artwork policy must be distinct.")
    owners = {}
    artwork = story.get("artwork", {})
    for section, assets in artwork_uses(story.get("lessons", []), story.get("hero"),
                                       story.get("guide"), story.get("section_art")):
        for asset in sorted(assets):
            contents = artwork[asset]
            owner = owners.setdefault(contents, section)
            if owner != section:
                raise ScanError(f"Artwork {asset!r} repeats between {owner} and {section}. Use distinct illustrations.")


def check_png(data):
    if (not data.startswith(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR") or len(data) < 45
            or len(data) > MAX_FILE_BYTES):
        raise ScanError("Use static PNG artwork of at most 750 KiB per piece.")
    width, height = (int.from_bytes(data[index:index + 4], "big") for index in (16, 20))
    if not 1 <= width <= 1600 or not 1 <= height <= 1600:
        raise ScanError("Artwork must be at most 1600 pixels per side.")
    offset, alpha, pixels = 8, data[25] in (4, 6), False
    while offset + 12 <= len(data):
        end = offset + int.from_bytes(data[offset:offset + 4], "big") + 12
        kind = data[offset + 4:offset + 8]
        if end > len(data) or kind == b"acTL":
            break
        if kind == b"tRNS":
            alpha = True
        elif kind == b"IDAT":
            pixels = True
        elif kind == b"IEND":
            if end == len(data) and pixels and alpha:
                return
            break
        offset = end
    raise ScanError("Artwork needs a complete still PNG with transparency.")


def load_artwork(folder, ids):
    if not ids:
        return {}
    if len(ids) > MAX_ASSETS:
        raise ScanError(f"Use at most {MAX_ASSETS} artwork pieces per report.")
    directory = folder / "artwork"
    if directory.is_symlink():
        raise ScanError("Use the report’s own artwork directory.")

    total, assets = 0, {}
    for name in sorted(ids):
        if not ASSET_ID.fullmatch(name):
            raise ScanError("Use a lowercase artwork ID.")
        path = directory / f"{name}.png"
        if path.is_symlink() or not path.is_file():
            raise ScanError(f"Missing local artwork: {name}.png.")
        with path.open("rb") as source:
            image = source.read(MAX_FILE_BYTES + 1)
        check_png(image)
        total += len(image)
        if total > MAX_TOTAL_BYTES:
            raise ScanError("Compress the combined artwork to 4 MiB or smaller.")
        assets[name] = base64.b64encode(image).decode("ascii")
    return assets


def validate_artwork(assets, ids):
    if not isinstance(assets, dict) or assets.keys() != ids or len(ids) > MAX_ASSETS:
        raise ScanError("The embedded artwork must match the illustration’s referenced pieces.")
    total = 0
    for encoded in assets.values():
        if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
            raise ScanError("The embedded artwork is missing or too large.")
        try:
            image = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ScanError("The embedded artwork needs valid base64 image data.") from error
        check_png(image)
        total += len(image)
        if total > MAX_TOTAL_BYTES:
            raise ScanError("Compress the combined artwork to 4 MiB or smaller.")
