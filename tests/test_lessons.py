import pytest

from repolens.lessons import check_intro_lesson, check_lesson_menu, lesson_references
from repolens.scanner import ScanError


def sample_lessons():
    return [
        {"id": "meaning", "kind": "compare", "after": 1, "title": "Two outputs", "prompt": "Compare the outputs.",
         "columns": ["First", "Second"], "rows": [{"label": "Result", "cells": [
             {"text": "A", "evidence_ids": ["first"]}, {"text": "B", "evidence_ids": ["second"]},
         ]}]},
        {"id": "example", "kind": "annotate", "after": 2, "title": "Read the example",
         "prompt": "Choose a part.", "source_id": "snippet", "notes": [
             {"label": "Input", "first": 1, "last": 1, "caption": "Set the input.", "evidence_ids": ["first"]},
             {"label": "Output", "first": 2, "last": 2, "caption": "Show the output.", "evidence_ids": ["second"]},
         ]},
    ]


def test_distinct_sections_keep_placement_and_evidence():
    evidence = {"first": {}, "second": {}, "snippet": {"excerpt": "input\noutput"}}
    assert lesson_references(sample_lessons(), 2, evidence) == set(evidence)


@pytest.mark.parametrize("invalid,message", [
    ("placement", "existing chapter boundary"),
    ("comparison", "2–2 entries"),
    ("source-line", "inside the excerpt"),
    ("citation", "available excerpt"),
])
def test_rejects_unrenderable_explanations(invalid, message):
    evidence = {"first": {}, "second": {}, "snippet": {"excerpt": "input\noutput"}}
    lessons = sample_lessons()
    if invalid == "placement":
        lessons[1]["after"] = 3
    elif invalid == "comparison":
        lessons[0]["rows"][0]["cells"].pop()
    elif invalid == "source-line":
        lessons[1]["notes"][1]["last"] = 3
    else:
        lessons[0]["rows"][0]["cells"][0]["evidence_ids"] = ["missing"]
    with pytest.raises(ScanError, match=message):
        lesson_references(lessons, 2, evidence)


def illustration():
    def choice(identifier, x):
        return {"id": identifier, "label": identifier, "frames": [
            {"caption": "Start", "evidence_ids": ["start"], "changes": {}},
            {"caption": "Finish", "evidence_ids": ["end"], "changes": {"marker": {"x": x}}},
        ]}

    return {"id": "positions", "kind": "illustrate", "after": 0, "title": "Position",
            "prompt": "Pick a result.", "height": 108,
            "objects": [
                {"id": "guide", "shape": "polyline", "x": 10, "y": 60, "tone": "ink",
                 "points": [[0, 0], [225, 0]]},
                {"id": "marker", "shape": "ellipse", "x": 20, "y": 40, "tone": "blue",
                 "w": 30, "h": 20},
            ],
            "choices": [choice("near", 60), choice("far", 200)]}


def test_illustration_cites_frames_in_all_choices():
    assert lesson_references([illustration()], 1, {"start": {}, "end": {}}) == {"start", "end"}


@pytest.mark.parametrize("change, message", [
    ({"marker": {"x": 315}}, "dimensions must fit"),
    ({"marker": {"x": True}}, "position must fit"),
    ({"marker": {"x": 20}}, "visibly change"),
    ({"marker": {"x": 60}}, "distinct drawings"),
    ({"marker": {"onclick": "unsupported"}}, "unsupported object change"),
    ({"missing": {"x": 50}}, "refer to existing objects"),
])
def test_illustration_rejects_invalid_or_indistinguishable_outcomes(change, message):
    lesson = illustration()
    lesson["choices"][1]["frames"][1]["changes"] = change
    with pytest.raises(ScanError, match=message):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_illustration_supports_curves_aligned_labels_and_finish_changes():
    lesson = illustration()
    lesson["objects"].extend([
        {"id": "curve", "shape": "curve", "x": 0, "y": 30, "tone": "ink",
         "points": [[30, 45], [42, 9], [96, 9], [120, 45]], "finish": "muted"},
        {"id": "label", "shape": "text", "x": 120, "y": 20, "tone": "ink",
         "text": "Result", "size": "small", "font": "mono", "align": "middle"},
    ])
    lesson["choices"][0]["frames"][-1]["changes"]["curve"] = {"finish": "dashed"}
    assert lesson_references([lesson], 1, {"start": {}, "end": {}}) == {"start", "end"}


def test_illustration_rejects_curve_control_points_offstage():
    lesson = illustration()
    lesson["objects"][0]["shape"] = "curve"
    lesson["objects"][0]["points"] = [[0, 0], [20, -61], [40, 0], [60, 0]]
    with pytest.raises(ScanError, match="path points must fit"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_illustration_supports_progressively_drawn_trace():
    lesson = illustration()
    lesson["objects"][0] = {
        "id": "guide", "shape": "trace", "x": 10, "y": 10, "tone": "ink", "reveal": 0,
        "commands": [["M", 0, 0], ["Q", 45, 35, 60, 40], ["L", 80, 65]],
    }
    for choice, reveal in zip(lesson["choices"], (35, 100)):
        choice["frames"][-1]["changes"]["guide"] = {"reveal": reveal}
    assert lesson_references([lesson], 1, {"start": {}, "end": {}}) == {"start", "end"}

    lesson["choices"][0]["frames"][-1]["changes"]["guide"]["reveal"] = 101
    with pytest.raises(ScanError, match="trace reveal"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_illustration_rejects_unpositioned_trace():
    lesson = illustration()
    lesson["objects"][0] = {
        "id": "guide", "shape": "trace", "x": 10, "y": 10, "tone": "ink",
        "commands": [["L", 0, 0], ["L", 80, 65]],
    }
    with pytest.raises(ScanError, match="trace starts with M"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_illustration_accepts_matching_material_and_motion_fields():
    lesson = illustration()
    lesson["objects"][1].update(material="enamel", depth=6, arc=14)
    lesson["choices"][0]["frames"][-1]["changes"]["marker"].update(lift=10, tilt=-8, scale_y=85)
    assert lesson_references([lesson], 1, {"start": {}, "end": {}}) == {"start", "end"}


@pytest.mark.parametrize("field, value, message", [
    ("depth", 13, "depth must be"),
    ("lift", 38, "lift must stay"),
    ("arc", 28, "motion arc must be"),
    ("tilt", -31, "tilt must be"),
    ("scale_y", 0, "vertical scale must be"),
])
def test_illustration_rejects_out_of_range_material_and_motion_fields(field, value, message):
    lesson = illustration()
    lesson["objects"][1].update(material="paper", **{field: value})
    with pytest.raises(ScanError, match=message):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_illustration_rejects_asset_paths():
    lesson = illustration()
    lesson["objects"][1].update(shape="sprite", asset="../unsafe")
    with pytest.raises(ScanError, match="lowercase artwork ID"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_looping_opening_validates_phases_and_citations():
    from repolens.illustration import hero_references

    hero = {key: value for key, value in illustration().items() if key in ("height", "objects")}
    hero.update(alt="A marker crossing the stage.", evidence_ids=["intro"], frames=[
        {"duration_ms": 900, "changes": {}},
        {"duration_ms": 1000, "changes": {"marker": {"x": 60}}},
        {"duration_ms": 1000, "changes": {"marker": {"x": 120}}},
    ])
    assert hero_references(hero) == {"intro"}

    hero["frames"][-1]["duration_ms"] = -1
    with pytest.raises(ScanError, match="opening timing"):
        hero_references(hero)
    hero["frames"][-1] = hero["frames"][0]
    with pytest.raises(ScanError, match="final opening frame"):
        hero_references(hero)


def test_filter_experiment_checks_sources_and_record_poses():
    base = illustration()
    lesson = dict(id="filters", after=1, kind="experiment", title="Filter records", prompt="Choose values.",
                  explanation="Every active group applies.", height=base["height"], objects=base["objects"],
                  groups=[{"id": "place", "label": "Place"}, {"id": "type", "label": "Type"}],
                  items=[], evidence_ids=["rule"])
    values = [("East", "Print"), ("East", "Audio"), ("West", "Audio")]
    for index, (place, type_) in enumerate(values):
        identifier = f"record-{index}"
        lesson["objects"].append({**base["objects"][1], "id": identifier, "x": 50 + (50 * index)})
        lesson["items"].append({
            "id": identifier, "label": identifier, "values": {"place": place, "type": type_},
            "hidden": {identifier: {"y": 65}},
        })
    assert lesson_references([lesson], 1, {"rule": {}}) == {"rule"}
    lesson["items"][2]["hidden"] = lesson["items"][1]["hidden"]
    with pytest.raises(ScanError, match="unique marks"):
        lesson_references([lesson], 1, {"rule": {}})


def test_guided_story_collects_frame_evidence_and_rejects_wrong_timing():
    from repolens.guide import guide_references

    fixture = illustration()
    chapters = []
    for id in ("start", "finish"):
        frames = fixture["choices"][0]["frames"]
        chapters.append(dict(id=id, title=id, height=fixture["height"], objects=fixture["objects"],
                             frames=[dict(frame, duration_ms=5500) for frame in frames]))
    guide = dict(title="One visual story", prompt="Watch what changes.", chapters=chapters)
    assert guide_references(guide) == {"start", "end"}
    chapters[1]["frames"][1]["duration_ms"] = 20
    with pytest.raises(ScanError, match="guided step duration"):
        guide_references(guide)


def test_guide_caps_steps_across_chapters():
    from repolens.guide import guide_references

    base = illustration()
    frames = [dict(frame, duration_ms=5000) for frame in base["choices"][0]["frames"]]
    template = dict(height=base["height"], objects=base["objects"], frames=frames)
    guide = dict(title="Guide", prompt="Watch the drawing.", chapters=[
        dict(template, id=name, title=name) for name in ("first", "second", "third")
    ])
    assert guide_references(guide) == {"start", "end"}
    guide["chapters"][2]["frames"] = [*frames, frames[0]]
    with pytest.raises(ScanError, match="at most six steps"):
        guide_references(guide)


def test_picture_can_compare_two_visual_states():
    from repolens.artwork import artwork_ids

    point = dict(x=24, y=55, label="Detail", caption="This detail follows the source.", evidence_ids=["source"])
    picture = dict(id="view", after=0, kind="picture", title="Compare", prompt="Look for the change.",
                   views=[dict(label=label, alt=label, asset=label, points=[point.copy()])
                          for label in ("before", "after")])
    assert lesson_references([picture], 1, {"source": {}}) == {"source"}
    assert artwork_ids([picture]) == {"before", "after"}
    picture["views"][1]["points"][0]["x"] = 96
    with pytest.raises(ScanError, match="8–92 percent"):
        lesson_references([picture], 1, {"source": {}})


@pytest.mark.parametrize("menu", [["meaning"], ["meaning", "meaning"], ["meaning", "missing"]])
def test_lesson_choices_require_distinct_existing_lessons(menu):
    check_lesson_menu(["example", "meaning"], sample_lessons())
    with pytest.raises(ScanError, match="independent lesson IDs"):
        check_lesson_menu(menu, sample_lessons())


def test_guided_lesson_packs_animation_and_supporting_art():
    from repolens.artwork import artwork_ids, section_art_references

    base = illustration()
    base["objects"][1].update(shape="sprite", asset="marker-art")
    frames = [dict(frame, duration_ms=5500) for frame in base["choices"][0]["frames"]]
    frames[1].update(motion_ms=2100, callout={"text": "Changed position", "x": 50, "y": 65})
    lesson = dict(id="motion", after=0, kind="guide", guide={
        "title": "Follow the marker", "prompt": "Notice where it lands.",
        "chapters": [dict(id="position", title="Motion", height=base["height"],
                          objects=base["objects"], frames=frames)],
    })
    art = {"chapter-0": {"asset": "context", "alt": "A contextual sketch.", "evidence_ids": ["context"]}}
    assert lesson_references([lesson], 1, {"start": {}, "end": {}}) == {"start", "end"}
    assert section_art_references(art, 1, [lesson]) == {"context"}
    assert artwork_ids([lesson], section_art=art) == {"marker-art", "context"}
    with pytest.raises(ScanError, match="existing report section"):
        section_art_references(art, 0, [lesson])
    frames[1]["motion_ms"] = 5100
    with pytest.raises(ScanError, match="leave at least 1200 ms"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})


def test_opening_is_separate_and_support_art_matches_a_subsection():
    from repolens.artwork import section_art_references

    lessons = sample_lessons()
    check_intro_lesson("meaning", lessons, ["other"])
    with pytest.raises(ScanError, match="outside the lesson chooser"):
        check_intro_lesson("meaning", lessons, ["meaning", "example"])
    illustration = {"asset": "context", "alt": "A stack of marked papers.", "evidence_ids": ["source"]}
    scenes = [{"claim_ids": ["applications"]}]
    assert section_art_references({"chapter-0-applications": illustration}, 1, lessons, scenes) == {"source"}
    with pytest.raises(ScanError, match="existing report section"):
        section_art_references({"chapter-0-unlisted": illustration}, 1, lessons, scenes)


def test_hero_motion_cues_are_ordered_and_keep_object_changes_on_stage():
    from repolens.illustration import hero_references

    drawing = illustration()
    hero = dict(height=drawing["height"], objects=drawing["objects"], alt="A moving paper marker.",
                evidence_ids=["source"], frames=[
                    {"changes": {}, "duration_ms": 2600, "cues": [
                        {"at": 22, "changes": {"marker": {"x": 85, "lift": 14}}},
                        {"at": 65, "changes": {"marker": {"x": 125, "lift": 4}}},
                    ]},
                    {"changes": {"marker": {"x": 145}}, "duration_ms": 1800},
                    {"changes": {"marker": {"x": 165}}, "duration_ms": 1800},
                ])
    assert hero_references(hero) == {"source"}
    second = hero["frames"][0]["cues"][1]
    second["at"] = 20
    with pytest.raises(ScanError, match="increasing percentages"):
        hero_references(hero)
    second["at"] = 65
    second["changes"]["marker"]["x"] = 310
    with pytest.raises(ScanError, match="dimensions must fit"):
        hero_references(hero)


def test_compact_opening_requires_a_visible_result_and_collects_evidence():
    base = illustration()
    lesson = dict(id="opening", after=0, kind="reveal", title="See the change", prompt="Reveal the new result.",
                  height=base["height"], objects=base["objects"], alt="One object moves along the same line.",
                  duration_ms=1800, states=[
                      dict(label="Reveal", caption="The starting position.", changes={}, evidence_ids=["first"]),
                      dict(label="Reset", caption="The new position.", changes={"marker": {"x": 60}}, evidence_ids=["second"]),
                  ])
    assert lesson_references([lesson], 0, {"first": {}, "second": {}}) == {"first", "second"}
    lesson["states"][1]["changes"] = {}
    with pytest.raises(ScanError, match="distinct result"):
        lesson_references([lesson], 0, {"first": {}, "second": {}})


def test_illustration_validates_a_lettered_moving_face():
    lesson = illustration()
    mark = lesson["objects"][1]
    mark.update(pivot=[15, 10], inscription="Results")
    assert lesson_references([lesson], 1, {"start": {}, "end": {}}) == {"start", "end"}
    mark["pivot"] = [31, 10]
    with pytest.raises(ScanError, match="pivot must be inside"):
        lesson_references([lesson], 1, {"start": {}, "end": {}})
