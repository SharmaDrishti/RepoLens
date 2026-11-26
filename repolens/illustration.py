"""Validate data for the freeform, offline lesson stage."""

import re

from .artwork import ASSET_ID
from .scanner import ScanError


TONES = ("ink", "paper", "amber", "rose", "mint", "blue", "violet")
SHAPES = {
    "rect": {"w", "h"},
    "sprite": {"asset", "w", "h"},
    "ellipse": {"w", "h"},
    "polyline": {"points"},
    "polygon": {"points"},
    "curve": {"points"},
    "trace": {"commands"},
    "text": {"text", "size"},
}
POSE = {"x", "y", "tone", "visible", "lift", "tilt", "scale_x", "scale_y"}
MATERIALS = ("paper", "enamel")
SOLID_SHAPES = ("rect", "ellipse", "polygon")
FINISHES = ("solid", "outline", "dashed", "muted")
COMMANDS = {"M": 2, "L": 2, "Q": 4, "C": 6}
OPTIONAL = {
    kind: {"align", "font"} if kind == "text" else {"finish"}
    for kind in SHAPES
}
OPTIONAL["trace"].add("reveal")
OPTIONAL["sprite"].clear()
for kind in ("rect", "ellipse", "sprite"):
    OPTIONAL[kind].update(("pivot", "inscription"))
for kind in SOLID_SHAPES:
    OPTIONAL[kind].update(("material", "depth"))


def require(condition, message):
    if not condition:
        raise ScanError(f"Freeform illustration: {message}.")


def bounded_int(value, low, high):
    return type(value) is int and low <= value <= high


def check_text(value, limit):
    require(isinstance(value, str) and value.strip() and len(value) <= limit
            and value.splitlines() == [value], f"expected one line of up to {limit} characters")


def check_list(value, low, high):
    require(isinstance(value, list) and low <= len(value) <= high,
            f"expected {low}–{high} entries")
    return value


def check_fields(item, names):
    require(isinstance(item, dict) and item.keys() == names,
            f"expected fields {', '.join(sorted(names))}")


def check_id(value, used):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", value)
            and value not in used, "use unique lowercase IDs")


def check_point(dx, dy, x, y, height):
    require(bounded_int(dx, -x, 320 - x) and bounded_int(dy, -y, height - y),
            "path points must fit the stage")


def check_trace(shape, x, y, height):
    require(bounded_int(shape.get("reveal", 100), 0, 100), "trace reveal must be 0–100")
    for i, command in enumerate(check_list(shape["commands"], 2, 64)):
        command = check_list(command, 3, 7)
        op, *coordinates = command
        require(isinstance(op, str) and op in COMMANDS and len(coordinates) == COMMANDS[op]
                and (op == "M") == (i == 0), "trace starts with M and continues with L, Q, or C")
        for dx, dy in zip(coordinates[::2], coordinates[1::2]):
            check_point(dx, dy, x, y, height)


def check_pose(shape, height):
    kind = shape["shape"]
    x, y = shape["x"], shape["y"]
    require(bounded_int(x, 0, 320) and bounded_int(y, 0, height), "position must fit the stage")
    require(shape["tone"] in TONES and type(shape.get("visible", True)) is bool,
            "use a listed tone and a boolean visibility")
    require(bounded_int(shape.get("lift", 0), 0, min(y, 32)), "lift must stay inside the stage (0–32)")
    require(bounded_int(shape.get("tilt", 0), -30, 30), "tilt must be -30–30 degrees")
    require(bounded_int(shape.get("scale_x", 100), 20, 150), "horizontal scale must be 20–150 percent")
    require(bounded_int(shape.get("scale_y", 100), 20, 100), "vertical scale must be 20–100 percent")
    if kind in SOLID_SHAPES:
        depth = shape.get("depth", 0)
        require(bounded_int(depth, 0, 12), "depth must be 0–12")
        material = shape.get("material")
        require(material in MATERIALS if "material" in shape else depth == 0,
                "use paper or enamel material for depth")
    if kind not in ("text", "sprite"):
        require(shape.get("finish", "solid") in FINISHES, "choose solid, outline, dashed, or muted")
    if kind == "sprite":
        require(isinstance(shape["asset"], str) and ASSET_ID.fullmatch(shape["asset"]),
                "use a lowercase artwork ID")
    if kind in ("rect", "ellipse", "sprite"):
        require(bounded_int(shape["w"], 1, 320 - x) and bounded_int(shape["h"], 1, height - y),
                "shape dimensions must fit the stage")
        if "pivot" in shape:
            px, py = check_list(shape["pivot"], 2, 2)
            require(bounded_int(px, 0, shape["w"]) and bounded_int(py, 0, shape["h"]),
                    "pivot must be inside the object")
        if "inscription" in shape:
            check_text(shape["inscription"], 24)
    elif kind == "text":
        check_text(shape["text"], 38)
        require(shape["size"] in ("small", "body", "large"), "choose small, body, or large text")
        require(shape.get("align", "start") in ("start", "middle", "end"), "choose start, middle, or end alignment")
        require(shape.get("font", "sans") in ("sans", "mono"), "choose sans or mono text")
    elif kind == "trace":
        check_trace(shape, x, y, height)
    else:
        bounds = {"polyline": (2, 24), "polygon": (3, 24), "curve": (4, 4)}
        for point in check_list(shape["points"], *bounds[kind]):
            dx, dy = check_list(point, 2, 2)
            check_point(dx, dy, x, y, height)


def drawing_objects(drawing):
    height = drawing["height"]
    require(bounded_int(height, 96, 300), "height must be 96–300")
    objects = {}
    for shape in check_list(drawing["objects"], 2, 40):
        require(isinstance(shape, dict), "expected an object")
        identifier, kind = shape.get("id"), shape.get("shape")
        check_id(identifier, objects)
        require(isinstance(kind, str) and kind in SHAPES, "unknown drawing shape")
        required = {"id", "shape", "x", "y", "tone"} | SHAPES[kind]
        check_fields(shape, required | (shape.keys() & ((POSE - {"x", "y", "tone"}) | OPTIONAL[kind] | {"arc"})))
        require(bounded_int(shape.get("arc", 0), 0, 24), "motion arc must be 0–24")
        check_pose(shape, height)
        objects[identifier] = shape

    return objects, height


def checked_frame(changes, objects, height):
    require(isinstance(changes, dict) and changes.keys() <= objects.keys(),
            "changes must refer to existing objects")
    visible = []
    for identifier, shape in objects.items():
        patch = changes.get(identifier, {})
        allowed = POSE | (SHAPES[shape["shape"]] & {"w", "h", "text"})
        allowed.update(OPTIONAL[shape["shape"]] & {"finish", "reveal"})
        require(isinstance(patch, dict) and patch.keys() <= allowed, "unsupported object change")
        pose = {**shape, **patch}
        check_pose(pose, height)
        if pose.get("visible", True) and (shape["shape"] != "trace" or pose.get("reveal", 100) > 0):
            mark = {key: value for key, value in pose.items() if key not in ("id", "visible", "arc")}
            if shape["shape"] not in ("text", "sprite"):
                mark.setdefault("finish", "solid")
            if shape["shape"] == "trace":
                mark.setdefault("reveal", 100)
            for key, default in (("lift", 0), ("tilt", 0), ("scale_x", 100), ("scale_y", 100)):
                mark.setdefault(key, default)
            visible.append(mark)
    require(visible, "each frame must show part of the drawing")
    return visible


def check_motion_cues(cues, base, objects, height):
    previous = 0
    for cue in check_list(cues, 1, 8):
        check_fields(cue, {"at", "changes"})
        require(bounded_int(cue["at"], previous + 1, 99),
                "motion cues must use increasing percentages from 1 to 99")
        require(isinstance(cue["changes"], dict) and all(isinstance(patch, dict) for patch in cue["changes"].values()),
                "motion cues must supply object changes")
        checked_frame({**base, **{
            key: {**base.get(key, {}), **patch} for key, patch in cue["changes"].items()
        }}, objects, height)
        previous = cue["at"]


def reveal_references(lesson):
    """Check the two poses of an interactive opening example."""
    check_text(lesson["title"], 68)
    check_text(lesson["prompt"], 135)
    check_text(lesson["alt"], 260)
    require(bounded_int(lesson["duration_ms"], 500, 3500), "opening movement must take 500–3500 ms")
    objects, height = drawing_objects(lesson)
    first, last = check_list(lesson["states"], 2, 2)
    refs, poses = set(), []
    for state in (first, last):
        check_fields(state, {"label", "caption", "changes", "evidence_ids"})
        check_text(state["label"], 32)
        check_text(state["caption"], 135)
        poses.append(checked_frame(state["changes"], objects, height))
        for ref in check_list(state["evidence_ids"], 1, 8):
            check_text(ref, 300)
            refs.add(ref)
    require(poses[0] != poses[1] and first["label"] != last["label"],
            "the opening choice must show a distinct result and action")
    if "cues" in lesson:
        check_motion_cues(lesson["cues"], first["changes"], objects, height)
    return refs


def hero_references(hero):
    """Check a looping opening and return the citations for its visual idea."""
    required = {"alt", "height", "objects", "frames", "evidence_ids"}
    require(isinstance(hero, dict) and required <= hero.keys() <= required | {"title"},
            "opening needs alt, height, objects, frames, and evidence_ids")
    check_text(hero["alt"], 300)
    if "title" in hero:
        check_text(hero["title"], 80)
    objects, height = drawing_objects(hero)
    refs = check_list(hero["evidence_ids"], 1, 8)
    for ref in refs:
        check_text(ref, 300)
    previous = None
    first = None
    frames = check_list(hero["frames"], 3, 8)
    for frame in frames:
        optional = {"cues"} & frame.keys() if isinstance(frame, dict) else set()
        check_fields(frame, {"changes", "duration_ms"} | optional)
        require(bounded_int(frame["duration_ms"], 650, 4000), "opening timing must be 650–4000 ms per frame")
        visible = checked_frame(frame["changes"], objects, height)
        require(visible != previous, "opening frames must visibly differ")
        if first is None:
            first = visible
        previous = visible
        if "cues" in frame:
            check_motion_cues(frame["cues"], frame["changes"], objects, height)
    require(first != previous, "the final opening frame should differ from the first")
    return set(refs)


def illustration_references(lesson):
    """Return all cited frame IDs after checking renderability."""
    objects, height = drawing_objects(lesson)
    choices, labels = set(), set()
    refs, outcomes = [], []
    for choice in check_list(lesson["choices"], 2, 4):
        check_fields(choice, {"id", "label", "frames"})
        check_id(choice["id"], choices)
        choices.add(choice["id"])
        check_text(choice["label"], 48)
        require(choice["label"] not in labels, "choice labels must be distinct")
        labels.add(choice["label"])
        previous = None
        for frame in check_list(choice["frames"], 2, 6):
            check_fields(frame, {"caption", "evidence_ids", "changes"})
            check_text(frame["caption"], 350)
            refs.extend(check_list(frame["evidence_ids"], 1, 8))
            visible = checked_frame(frame["changes"], objects, height)
            require(visible != previous, "every frame must visibly change the drawing after the first")
            previous = visible
        require(previous not in outcomes, "choices must finish with distinct drawings")
        outcomes.append(previous)
    return refs
