import copy
import json
import re
import subprocess
import sys

import pytest

from repolens import snapshot as snapshots
from repolens.__main__ import main
from repolens.checker import build_evidence, validate_claim
from repolens.knowledge import validate_knowledge
from repolens.page import verify_template
from repolens.reader_language import plain_is_grounded
from repolens.readers import write_context
from repolens.scanner import ScanError


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write_project(root):
    (root / "README.md").write_text(
        "# Sample\n\nSample is a Python package for creating command line interfaces with as little code as necessary.\n"
        "\n## Install\n\n```sh\n$ pip install sample==1.2\n```\n"
        "\n## Usage\n\nAutomatic help page generation for commands.\n"
    )
    example = root / "examples" / "demo"
    example.mkdir(parents=True)
    (example / "pyproject.toml").write_text('[project.scripts]\ndemo = "launch:main"\n')
    (example / "launch.py").write_text("import helper\n\ndef main():\n    pass\n")
    (root / "helper.py").write_text("def run():\n    pass\n")
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", "https://github.com/example/sample.git")
    git(root, "add", ".")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c",
        "commit.gpgsign=false", "commit", "-qm", "Fixture")


def run_build(monkeypatch, root, output, knowledge_path):
    monkeypatch.setattr(sys, "argv", ["repolens", "build", str(root), "--no-ai", "--out",
                                     str(output), "--knowledge-out", str(knowledge_path)])
    assert main() == 0
    return json.loads(re.search(r'id="repolens-data">(.*?)</script>', output.read_text()).group(1))


def test_build_and_context_share_ingestion_and_embed_available_context(tmp_path, monkeypatch):
    root = tmp_path / "sample"
    root.mkdir()
    write_project(root)
    counts = {"scan": 0, "resolve": 0}
    scan_root, source_root = snapshots.scan_root, snapshots.source_root

    def count_scan(*args, **kwargs):
        counts["scan"] += 1
        return scan_root(*args, **kwargs)

    def count_resolve(*args, **kwargs):
        counts["resolve"] += 1
        return source_root(*args, **kwargs)

    monkeypatch.setattr(snapshots, "scan_root", count_scan)
    monkeypatch.setattr(snapshots, "source_root", count_resolve)
    output, knowledge_path = tmp_path / "report.html", tmp_path / "knowledge.json"
    payload = run_build(monkeypatch, root, output, knowledge_path)
    assert counts == {"scan": 1, "resolve": 1}
    model = payload["knowledge"]
    assert model == json.loads(knowledge_path.read_text())
    validate_knowledge(model)
    assert model["snapshot"]["working_tree"] == "clean"
    assert model["snapshot"]["cache"]["remote_freshness"] == "not_applicable"
    assert model["context"]["purpose"]["what_it_is"]["plain"]["text"].startswith("A tool for making programs")
    assert model["context"]["use_cases"]["use_cases"]
    install, = model["context"]["getting_started"]["install"]["items"]
    assert install["text"] == "pip install sample==1.2"
    assert model["evidence"][install["evidence_ids"][0]]["excerpt"] == "$ pip install sample==1.2"
    flow = model["developer"]["reading_guide"]["flow"]
    assert flow["kind"] == "import_path"
    assert flow["entry_scope"] == {"kind": "example", "path": "examples/demo"}
    entry, = model["developer"]["entry_declarations"]
    assert model["evidence"][entry["evidence_ids"][0]]["line"] == 2
    html = output.read_text()
    assert "Static import tour" in html and "Example entry" in html
    assert not re.search(r'<script[^>]+src=|<link[^>]+rel="stylesheet"', html)

    context = tmp_path / "context"
    write_context(str(root), context, tmp_path / "cache")
    assert counts == {"scan": 2, "resolve": 2}
    for name, key in (("purpose", "purpose"), ("usecases", "use_cases"), ("getstarted", "getting_started")):
        data = json.loads((context / (name + ".json")).read_text())
        assert model["context"][key] == {k: v for k, v in data.items() if k not in {"repo", "commit", "evidence"}}
        for record in data["evidence"]:
            assert model["evidence"][record["id"]]["excerpt"] == record["text"]

    corrupt = copy.deepcopy(model)
    corrupt["context"]["purpose"]["what_it_is"]["evidence_ids"] = ["unknown"]
    with pytest.raises(ScanError, match="missing evidence"):
        validate_knowledge(corrupt)
    corrupt = copy.deepcopy(model)
    corrupt["schema_version"] = 99
    with pytest.raises(ScanError, match="version"):
        validate_knowledge(corrupt)


def test_dirty_checkout_uses_working_tree_without_commit_links(tmp_path, monkeypatch):
    root = tmp_path / "sample"
    root.mkdir()
    write_project(root)
    (root / "README.md").write_text("Sample is a Python package for reading and converting data files.\n")
    payload = run_build(monkeypatch, root, tmp_path / "page.html", tmp_path / "knowledge.json")
    knowledge = payload["knowledge"]
    snapshot = knowledge["snapshot"]
    assert snapshot["working_tree"] == "dirty"
    assert snapshot["content"] == "working_tree"
    assert snapshot["commit"]["sha"] == git(root, "rev-parse", "HEAD")
    assert not snapshot["commit"]["pinned"]
    assert "converting data files" in knowledge["context"]["purpose"]["what_it_is"]["text"]
    assert knowledge["evidence"] and all(item["url"] is None for item in knowledge["evidence"].values())


def test_cached_snapshot_exposes_reuse_without_freshness_claim(tmp_path, monkeypatch):
    root = tmp_path / "sample"
    root.mkdir()
    write_project(root)

    def cached(source, cache, *, cache_info):
        cache_info["reused"] = True
        return root

    monkeypatch.setattr(snapshots, "source_root", cached)
    snapshot = snapshots.open_snapshot("https://github.com/example/sample", tmp_path / "out", tmp_path)
    assert snapshot.identity["working_tree"] == "clean"
    assert snapshot.identity["cache"] == {"mode": "reused", "remote_freshness": "not_checked"}


def test_missing_documentation_stays_explicit_in_offline_build(tmp_path, monkeypatch):
    root = tmp_path / "empty-docs"
    root.mkdir()
    (root / "README").write_text("Hello world!\n")
    data = run_build(monkeypatch, root, tmp_path / "page.html", tmp_path / "knowledge.json")
    model = data["knowledge"]
    assert model["context"]["purpose"]["what_it_is"]["text"] == "unknown"
    assert model["context"]["purpose"]["who_uses_it"]["status"] == "unknown"
    assert model["context"]["use_cases"]["use_cases"] == []
    assert model["context"]["getting_started"]["install"]["status"] == "not_documented"
    assert model["developer"]["entry_declarations"] == []


def test_stale_frontend_template_is_rejected():
    with pytest.raises(ScanError, match="template is stale"):
        verify_template("<html></html>")


@pytest.mark.xfail(strict=True, reason="Known limitation: vocabulary matching cannot verify relationship direction")
def test_semantic_guard_should_reject_reversed_relationship():
    assert not plain_is_grounded("B calls A.", ["A calls B."])


@pytest.mark.xfail(strict=True, reason="Known limitation: legacy interpretation check verifies citations, not entailment")
def test_interpretation_should_reject_contradiction_with_real_evidence_id(tmp_path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("pass\n")
    evidence, diagnostics = build_evidence({
        "commit": {"pinned": False}, "entry_points": [],
        "edges": [{"id": "imp:0001", "from": "a.py", "to": "b.py", "line": 1, "kind": "import"}],
    }, tmp_path)
    assert not diagnostics and "imp:0001" in evidence
    claim = {"kind": "INTERPRETATION", "text": "a.py never imports b.py.", "section": "summary",
             "evidence_ids": ["imp:0001"]}
    assert validate_claim(claim, evidence) is not None
