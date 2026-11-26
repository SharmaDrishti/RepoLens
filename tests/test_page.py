import json
import re

import pytest

from repolens.page import write_page
from repolens.scanner import ScanError


def test_page_embeds_escaped_report_and_import_path(tmp_path):
    report = tmp_path / "report.json"
    output = tmp_path / "report.html"
    name = "</script><script>alert(1)</script>"
    report.write_text(json.dumps({
        "repo": name, "commit": {"pinned": False}, "claims": [],
        "reading_guide": {"flow": {"files": ["a.py", "b.py"], "edge_ids": ["imp:0001"]}},
    }), encoding="utf-8")
    write_page(report, output, tmp_path / "cache")

    html = output.read_text(encoding="utf-8")
    assert name not in html
    assert "__REPOLENS_DATA__" not in html
    assert not re.search(r"<script[^>]+src=|<link[^>]+rel=\"stylesheet\"", html)
    payload = json.loads(re.search(r'id="repolens-data">(.*?)</script>', html).group(1))
    assert payload["report"]["repo"] == name
    assert payload["edges"] == [{"id": "imp:0001", "from": "a.py", "to": "b.py"}]


def test_page_refuses_to_overwrite_input(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("{}")
    with pytest.raises(ScanError, match="different from the input"):
        write_page(path, path, tmp_path / "cache")
    assert path.read_text() == "{}"


def test_page_maps_measured_imports_without_ranking_and_includes_excerpts(tmp_path):
    (tmp_path / "a.py").write_text("import b\n")
    (tmp_path / "b.py").write_text("import c\n")
    (tmp_path / "c.py").write_text("pass\n")
    report_path = tmp_path / "report.json"
    facts_path = tmp_path / "facts.json"
    output = tmp_path / "report.html"
    report = {
        "repo": "example", "source": str(tmp_path),
        "commit": {"sha": None, "pinned": False}, "claims": [],
    }
    report_path.write_text(json.dumps(report))
    facts_path.write_text(json.dumps({
        **report, "edges": [
            {"id": "ab", "from": "a.py", "to": "b.py", "line": 1, "kind": "import"},
            {"id": "ab-again", "from": "a.py", "to": "b.py", "line": 1, "kind": "import"},
            {"id": "bc", "from": "b.py", "to": "c.py", "line": 1, "kind": "import"},
        ],
    }))

    write_page(report_path, output, tmp_path / "cache", facts_path)

    html = output.read_text(encoding="utf-8")
    payload = json.loads(re.search(r'id="repolens-data">(.*?)</script>', html).group(1))
    assert [edge["id"] for edge in payload["edges"]] == ["ab", "bc"]
    assert payload["evidence"]["ab"]["snippet"] == "import b"
    assert payload["evidence"]["bc"]["snippet"] == "import c"
    assert payload["evidence"]["bc"]["url"] is None
    assert "reading_guide" not in payload["report"]


def test_build_cli_generates_checked_report_without_api_key(tmp_path):
    import os
    import subprocess
    import sys

    project = tmp_path / "example"
    project.mkdir()
    (project / "__main__.py").write_text("import helper\n")
    (project / "helper.py").write_text("def run():\n    pass\n")
    (project / "README.md").write_text(
        "# Example\n\nThis example shows how a command can hand work to a separate helper file.\n"
    )
    (project / "hooks.snippet.json").write_text(json.dumps({
        "hooks": {"UserPromptSubmit": [{"hooks": [
            {"type": "command", "command": "python3 helper.py record"},
        ]}]},
    }, indent=2))
    output = tmp_path / "offline.html"

    result = subprocess.run(
        [sys.executable, "-m", "repolens", "build", str(project), "--no-ai", "--out", str(output)],
        capture_output=True, text=True, check=True,
        env={key: value for key, value in os.environ.items() if key not in {"GEMINI_API_KEY", "ANTHROPIC_API_KEY"}},
    )
    assert "Offline page saved" in result.stdout
    payload = json.loads(re.search(r'id="repolens-data">(.*?)</script>', output.read_text()).group(1))
    report = payload["report"]
    assert report["repo"] == "example"
    assert report["reading_guide"]["flow"]["files"] == ["__main__.py", "helper.py"]
    assert report["claims"][0]["verification"] == "verified"
    assert report["claims"][0]["evidence"][0]["snippet"] == "import helper"
    assert report["overview"]["description"]["line"] == 3
    hook, = report["overview"]["hooks"]
    assert (hook["event"], hook["script"], hook["arguments"], hook["template"]) == (
        "UserPromptSubmit", "helper.py", ["record"], True,
    )
    assert hook["evidence"]["path"] == "hooks.snippet.json"
    assert not (tmp_path / "facts.json").exists()
