import json
from pathlib import Path
import re
import subprocess

import pytest

from repolens.explain import explain, load_reviewed_story
from repolens.scanner import ScanError
from repolens.snapshot import open_snapshot


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "record-filter"
    root.mkdir()
    (root / "README.md").write_text(
        "# Record filter\n\nRecord filter is a Python library for filtering records.\n\n"
        "It checks each record for a name and returns the records that have a name.\n\n"
        "## Installation\n\n```sh\npip install record-filter\n```\n\n"
        "## Usage\n\n```python\nfrom filter import named\nnamed([{'name': 'Pat'}])\n```\n"
    )
    (root / "filter.py").write_text("def named(records):\n    return [record for record in records if record.get('name')]\n")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "https://github.com/example/record-filter.git"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "Synthetic fixture"], check=True)
    return root


def synthetic(stage, payload):
    if stage == "Understanding":
        ref = next(key for key, item in payload["evidence"].items() if item["type"] == "documentation")
        def claim(identifier, section, label, text):
            return {"id": identifier, "section": section, "label": label, "text": text, "evidence_ids": [ref]}
        return {"claims": [
            claim("intro", "purpose", "Filter records", "A Python library that keeps named records."),
            claim("check", "mechanism", "Check records", "Check whether each record has a name."),
            claim("keep", "mechanism", "Keep named records", "Return the records that have a name."),
            {**claim("bad", "capability", "Invalid", "Unsafe </script><script>"), "evidence_ids": ["made-up"]},
        ], "unknowns": []}
    assert stage == "Story"
    assert {item["id"] for item in payload["claims"]} == {"intro", "check", "keep"}
    return {"scenes": [
        {"kind": "walkthrough", "title": "Follow a record", "objective": "See what happens to a record.",
         "accessibility": "Filter walkthrough", "claim_ids": ["check", "keep"]},
        {"kind": "flow", "title": "Invalid scene", "objective": "Bad", "accessibility": "Bad", "claim_ids": ["bad"]},
    ]}


def test_two_stage_explanation_embeds_only_checked_sources(project):
    calls = []
    def invoke(stage, payload):
        calls.append(stage)
        return synthetic(stage, payload)

    out = project.parent / "report.html"
    result = explain(str(project), out, project.parent / "cache", invoke=invoke,
                     artifact_out=project.parent / "story.json")
    assert calls == ["Understanding", "Story"]
    assert result["mode"] == "synthetic_test"
    assert result["scenes"][0]["claim_ids"] == ["check", "keep"]
    assert all(scene["title"] != "Invalid scene" for scene in result["scenes"])
    assert result["checklist"]["mechanisms"] == "partial"
    assert any(item["text"] == "pip install record-filter" for item in result["setup"]["install"])
    assert all(item["url"].startswith("https://github.com/example/record-filter/blob/" + result["project"]["commit"]["sha"])
               for item in result["evidence"].values())
    html = out.read_text()
    payload = json.loads(re.search(r'<script type="application/json" id="repolens-data">(.*?)</script>', html, re.S)[1])
    assert payload["story"] == json.loads((project.parent / "story.json").read_text())
    assert not re.search(r'<script[^>]+\bsrc=|<link[^>]+\brel="stylesheet"', html)


def test_invalid_story_falls_back_and_missing_key_fails_explicitly(project, monkeypatch):
    def invalid(stage, payload):
        return {"scenes": ["wrong shape"]} if stage == "Story" else synthetic(stage, payload)

    out = project.parent / "report.html"
    result = explain(str(project), out, project.parent / "cache", invoke=invalid)
    assert any(item.startswith("Invalid") or "Unexpected fields" in item for item in result["unknowns"])
    assert all(scene["kind"] in {"intro", "explorer"} for scene in result["scenes"])
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ScanError, match="Understanding.*GEMINI_API_KEY"):
        explain(str(project), out, project.parent / "cache")


def test_explain_cli_can_generate_labeled_deterministic_report(project):
    import sys
    out = project.parent / "offline.html"
    command = [sys.executable, "-m", "repolens", "explain", str(project), "--no-ai", "--out", str(out)]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    assert "deterministic" in result.stdout
    assert out.is_file()


def test_gemini_transport_uses_project_model_for_both_stages(project, monkeypatch):
    from io import BytesIO
    from repolens import providers

    requests = []
    def transport(request, timeout):
        body = json.loads(request.data)
        config = body["generationConfig"]
        assert '"maxItems"' not in json.dumps(config["responseJsonSchema"])
        assert config["maxOutputTokens"] == 700 and timeout == 7
        assert "/models/test-model:" in request.full_url
        payload = json.loads(body["contents"][0]["parts"][0]["text"])["facts"]
        stage = ("Understanding", "Story")[len(requests)]
        requests.append(stage)
        reply = synthetic(stage, payload)
        return BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(reply)}]}}]}).encode())

    monkeypatch.setenv("GEMINI_API_KEY", "fake-fixture-key")
    monkeypatch.setattr(providers, "urlopen", transport)
    out = project.parent / "report.html"
    result = explain(str(project), out, project.parent / "cache", model="test-model", tokens=700, timeout=7)
    assert requests == ["Understanding", "Story"]
    assert result["mode"] == "ai"  # Production path with mocked transport, not a credentialed run.
    assert "fake-fixture-key" not in out.read_text()


def test_prepared_report_requires_the_waiting_task_to_start(project):
    out = project.parent / "offline.html"
    artifact = project.parent / "reviewed.json"
    cache = project.parent / "cache"
    story = explain(str(project), out, cache, no_ai=True)
    ref = next(iter(story["evidence"]))
    start = {"limit": 2, "waiting": 1, "running": 2, "settled": 0}

    def step(identifier, event, limit, waiting, running, settled):
        return {"id": identifier, "event": event, "caption": "Follow the task.", "fact_ids": ["illustration"],
                "state": {"limit": limit, "waiting": waiting, "running": running, "settled": settled}}

    lower = {"id": "lower", "choice": 1, "initial_state": start, "steps": [step("reduce", "limit", 1, 1, 2, 0)]}
    story["behavior"] = {
        "project": story["project"], "family": "capacity", "question": "When can waiting work start?",
        "semantic_review": "reviewed", "generation": {}, "facts": {"illustration": {"evidence": [{"id": ref}]}},
        "scenarios": [
            {"id": "hold", "choice": 2, "initial_state": start, "steps": [step("hold-1", "settle", 2, 0, 2, 1)]},
            lower,
        ],
    }
    snapshot = open_snapshot(str(project), out, cache)
    artifact.write_text(json.dumps(story))
    with pytest.raises(ScanError, match="show when at least one waiting task starts"):
        load_reviewed_story(artifact, snapshot)
    lower["steps"].extend([step("settle-1", "settle", 1, 1, 1, 1), step("settle-2", "settle", 1, 0, 1, 2)])
    lower["steps"][-1]["provenance"] = "source_review"
    artifact.write_text(json.dumps(story))
    reviewed = load_reviewed_story(artifact, snapshot)
    assert reviewed["behavior"]["scenarios"][1]["steps"][-1]["provenance"] == "source_review"
