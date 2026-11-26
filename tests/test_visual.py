import json

import pytest

from repolens.explain import load_reviewed_story
from repolens.scanner import ScanError
from repolens.visual import validate_visual


def plan(ref):
    def frame(position):
        return {"placements": {"sample": position}, "caption": f"Sample reaches {position}.",
                "evidence_ids": [ref], "values": {}, "active": [position], "paths": []}

    return {
        "title": "Where does the sample go?", "prompt": "Compare the two routes.",
        "grid": {"columns": 3, "rows": 1},
        "objects": [
            {"id": name, "label": name, "shape": "card", "tone": "amber", "column": column, "row": 1}
            for column, name in enumerate(("start", "east", "west"), 1)
        ],
        "paths": [],
        "tokens": [{"id": "sample", "label": "Sample", "tone": "mint"}],
        "choices": [{"id": name, "label": name, "frames": [frame("start"), frame(name)]}
                    for name in ("east", "west")],
    }


@pytest.mark.parametrize("invalid,explanation", [
    ("location", "inside the grid"),
    ("token", "existing objects"),
    ("no-change", "observable change"),
    ("no-evidence", "1–8 entries"),
])
def test_visual_validation_rejects_unrenderable_frames(invalid, explanation):
    visual = plan("sample-source")
    assert validate_visual(visual) == {"sample-source"}
    choice = visual["choices"][0]
    if invalid == "location":
        visual["objects"][0]["column"] = 4
    elif invalid == "token":
        choice["frames"][1]["placements"]["sample"] = "unknown"
    elif invalid == "no-change":
        choice["frames"][1] = choice["frames"][0]
    else:
        choice["frames"][1]["evidence_ids"] = []
    with pytest.raises(ScanError, match=explanation):
        validate_visual(visual)


def test_visual_frame_sources_are_checked_against_the_pinned_snapshot(tmp_path):
    commit = {"sha": "e" * 40, "pinned": True, "remote_url": "https://github.com/example/sample"}
    project = {"repo": "sample", "commit": commit}
    source_url = f"https://github.com/example/sample/blob/{commit['sha']}/README.md#L1"
    story = {
        "schema_version": 1, "project": project, "checklist": {}, "claims": {},
        "unknowns": [], "scenes": [], "setup": {}, "visual": plan("sample-source"),
        "evidence": {"sample-source": {
            "path": "README.md", "line": 1, "end_line": 1, "excerpt": "Repository text.",
            "url": source_url,
        }},
    }

    class Snapshot:
        identity = project

        def lines(self, path):
            assert path == "README.md"
            return ["Repository text."]

    artifact = tmp_path / "story.json"
    artifact.write_text(json.dumps(story))
    assert load_reviewed_story(artifact, Snapshot())["visual"] == story["visual"]
    story["evidence"]["sample-source"]["excerpt"] = "A different line."
    artifact.write_text(json.dumps(story))
    with pytest.raises(ScanError, match="does not match its pinned source"):
        load_reviewed_story(artifact, Snapshot())
