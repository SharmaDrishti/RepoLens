"""Check the teaching sections a prepared report asks the renderer to show."""

import re

from .artwork import ASSET_ID
from .experiment import experiment_references
from .guide import guide_references
from .illustration import illustration_references, reveal_references
from .scanner import ScanError
from .visual import validate_visual


def lesson_references(lessons, chapter_count, evidence):
    """Validate the lesson data and return the evidence IDs it uses."""
    def check(condition, message):
        if not condition:
            raise ScanError(f"Teaching section: {message}.")

    def fields(value, *names):
        check(isinstance(value, dict) and value.keys() == set(names),
              f"expected fields {', '.join(names)}")

    def text(value, limit):
        check(isinstance(value, str) and value.strip() and len(value) <= limit,
              f"expected text of 1–{limit} characters")

    def entries(value, minimum, maximum):
        check(isinstance(value, list) and minimum <= len(value) <= maximum,
              f"expected {minimum}–{maximum} entries")
        return value

    refs = set()

    def cite(items):
        for ref in entries(items, 1, 8):
            text(ref, 300)
            check(ref in evidence, "citation must refer to an available excerpt")
            refs.add(ref)

    ids = set()
    headers = ("id", "kind", "after")
    for lesson in entries(lessons, 1, 6):
        check(isinstance(lesson, dict), "expected a lesson object")
        identifier = lesson.get("id")
        check(isinstance(identifier, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", identifier)
              and identifier not in ids, "IDs must be unique lowercase names")
        ids.add(identifier)
        after = lesson.get("after")
        check(type(after) is int and 0 <= after <= chapter_count, "placement must refer to an existing chapter boundary")
        kind = lesson.get("kind")
        if kind == "animate":
            fields(lesson, *headers, "plan")
            for ref in validate_visual(lesson["plan"]):
                cite([ref])
            continue
        if kind == "guide":
            fields(lesson, *headers, "guide")
            for ref in guide_references(lesson["guide"]):
                cite([ref])
            continue

        common = (*headers, "title", "prompt")
        text(lesson.get("title"), 100)
        text(lesson.get("prompt"), 240)
        if kind == "experiment":
            cite(experiment_references(lesson))
        elif kind == "reveal":
            optional = ("cues",) if "cues" in lesson else ()
            fields(lesson, *common, "alt", "height", "objects", "states", "duration_ms", *optional)
            for ref in reveal_references(lesson):
                cite([ref])
        elif kind == "illustrate":
            fields(lesson, *common, "height", "objects", "choices")
            for ref in illustration_references(lesson):
                cite([ref])
        elif kind == "picture":
            fields(lesson, *common, "views")
            assets, labels = set(), set()
            for view in entries(lesson["views"], 1, 2):
                fields(view, "label", "alt", "asset", "points")
                text(view["label"], 40)
                text(view["alt"], 300)
                text(view["asset"], 32)
                check(ASSET_ID.fullmatch(view["asset"]) and view["asset"] not in assets,
                      "use separate picture assets with lowercase IDs")
                check(view["label"] not in labels, "give picture views distinct labels")
                assets.add(view["asset"])
                labels.add(view["label"])
                coordinates = set()
                for point in entries(view["points"], 1, 6):
                    fields(point, "x", "y", "label", "caption", "evidence_ids")
                    text(point["label"], 64)
                    text(point["caption"], 350)
                    x, y = point["x"], point["y"]
                    check(type(x) is int and type(y) is int and 8 <= x <= 92 and 8 <= y <= 92,
                          "picture points must stay within 8–92 percent of the image")
                    check((x, y) not in coordinates, "place picture points at distinct positions")
                    coordinates.add((x, y))
                    cite(point["evidence_ids"])
        elif kind == "compare":
            fields(lesson, *common, "columns", "rows")
            columns = entries(lesson["columns"], 2, 3)
            for heading in columns:
                text(heading, 40)
            check(len(set(columns)) == len(columns), "comparison headings must be distinct")
            differs = False
            for row in entries(lesson["rows"], 1, 6):
                fields(row, "label", "cells")
                text(row["label"], 48)
                values = set()
                for cell in entries(row["cells"], len(columns), len(columns)):
                    fields(cell, "text", "evidence_ids")
                    text(cell["text"], 160)
                    values.add(cell["text"])
                    cite(cell["evidence_ids"])
                differs |= len(values) > 1
            check(differs, "a comparison must show a difference in the outcomes")
        elif kind == "annotate":
            fields(lesson, *common, "source_id", "notes")
            cite([lesson["source_id"]])
            excerpt = evidence[lesson["source_id"]]["excerpt"]
            count = len(excerpt.split("\n"))
            check(count <= 24, "use a source excerpt of at most 24 lines")
            ranges = set()
            for note in entries(lesson["notes"], 2, 6):
                fields(note, "label", "first", "last", "caption", "evidence_ids")
                text(note["label"], 42)
                text(note["caption"], 350)
                first, last = note["first"], note["last"]
                check(type(first) is int and type(last) is int and 1 <= first <= last <= count,
                      "annotation line numbers must stay inside the excerpt")
                check((first, last) not in ranges, "give each annotation a distinct source range")
                ranges.add((first, last))
                cite(note["evidence_ids"])
        elif kind == "explore":
            fields(lesson, *common, "parts")
            labels = set()
            for part in entries(lesson["parts"], 2, 6):
                fields(part, "label", "caption", "example", "evidence_ids")
                text(part["label"], 42)
                check(part["label"] not in labels, "give each part a distinct label")
                labels.add(part["label"])
                text(part["caption"], 350)
                text(part["example"], 160)
                cite(part["evidence_ids"])
        else:
            check(False, "choose compare, annotate, explore, animate, illustrate, experiment, picture, guide, or reveal")
    return refs


def check_lesson_menu(menu, lessons):
    """The first entry is a recommended starting point among independent lessons."""
    if menu is None:
        return
    ids = {lesson["id"] for lesson in lessons}
    if (not isinstance(menu, list) or not 2 <= len(menu) <= len(ids)
            or any(not isinstance(item, str) or item not in ids for item in menu)
            or len(set(menu)) != len(menu)):
        raise ScanError("List two or more distinct independent lesson IDs in lesson_menu.")


def check_intro_lesson(identifier, lessons, menu):
    if identifier is None:
        return
    if (not isinstance(identifier, str) or identifier in (menu or [])
            or all(lesson["id"] != identifier for lesson in lessons)):
        raise ScanError("The opening example must refer to a lesson outside the lesson chooser.")
