import json
import subprocess
import sys

from repolens.writer import assemble_report


def fact(text, *identifiers, **fields):
    return {"kind": "FACT", "text": text, "evidence_ids": list(identifiers), "section": "summary", **fields}


def test_checker_retries_invalid_claims_once_and_keeps_only_supported_claims(tmp_path):
    (tmp_path / "main.py").write_text("import helper\n")
    (tmp_path / "helper.py").write_text("pass\n")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Test evidence")
    sha = git("rev-parse", "HEAD")
    facts = {
        "source": str(tmp_path), "repo": "example",
        "commit": {"sha": sha, "pinned": True, "remote_url": "git@github.com:example/project.git"},
        "entry_points": [],
        "edges": [
            {"from": "main.py", "to": "helper.py", "line": 1, "kind": "import", "id": "imp:0001"},
            {"from": "main.py", "to": "missing.py", "line": 1, "kind": "import", "id": "imp:0002"},
            {"from": "main.py", "to": "helper.py", "line": 2, "kind": "import", "id": "imp:0003"},
        ],
    }
    true = fact("main.py imports helper.py.", "imp:0001")
    false = fact("main.py imports invented.py.", "imp:0001")
    notes = {
        "kind": "INTERPRETATION", "text": "The helper looks like a place to explore next.",
        "evidence_ids": ["imp:0001"], "section": "reading_path",
    }
    attempts = []

    def draft(payload, reasons):
        assert [item["id"] for item in payload["evidence"]] == ["imp:0001"]
        attempts.append(reasons)
        if reasons:
            assert len(reasons) == 6
            assert false["text"] in {item["text"] for item in reasons}
            return {"claims": [false, notes]}
        return {"claims": [
            true, false, fact("Invented edge.", "imp:0099"),
            fact("Missing target.", "imp:0002"), fact("Invalid line.", "imp:0003"),
            fact("Missing evidence ID."), fact(true["text"], "imp:0001", line=2),
        ]}

    report = assemble_report(facts, tmp_path, draft)
    assert len(attempts) == 2
    assert [claim["verification"] for claim in report["claims"]] == ["verified", "interpretation"]
    assert len(report["rejected_claims"]) == 7
    assert report["rejected_claims"][-1]["attempt"] == 2
    assert report["claims"][0]["evidence"][0]["url"] == (
        f"https://github.com/example/project/blob/{sha}/main.py#L1"
    )
    assert report["sections"]["summary"] == ["claim:0001"]
    assert len(report["evidence_diagnostics"]) == 2

    (tmp_path / "main.py").write_text("import another\n")
    changed = assemble_report(facts, tmp_path, draft)
    assert changed["claims"] == []
    assert len(attempts) == 2


def test_report_cli_handles_facts_without_evidence_and_needs_no_credentials(tmp_path):
    facts = tmp_path / "facts.json"
    out = tmp_path / "report.json"
    facts.write_text(json.dumps({
        "repo": "empty", "source": str(tmp_path),
        "commit": {"pinned": False, "sha": None},
        "edges": [], "entry_points": [],
    }))
    subprocess.run(
        [sys.executable, "-m", "repolens", "report", str(facts), "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(out.read_text())["claims"] == []


def test_gemini_adapter_sends_structured_facts_and_keeps_checker_in_control(monkeypatch):
    from io import BytesIO

    from repolens import providers
    from repolens.checker import check_draft

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    model_claim = fact("main.py imports invented.py.", "imp:0001")
    payload = {"evidence": [{"id": "imp:0001", "fact_text": "main.py imports helper.py."}]}
    reasons = [{"reason": "Use the exact fact text."}]

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/gemini-test:generateContent")
        assert request.headers["X-goog-api-key"] == "test-key"
        assert timeout == 60
        body = json.loads(request.data)
        assert body["generationConfig"]["responseJsonSchema"] == providers.CLAIM_SCHEMA
        assert json.loads(body["contents"][0]["parts"][0]["text"]) == {
            "facts": payload, "rejections": reasons,
        }
        return BytesIO(json.dumps({"candidates": [{
            "finishReason": "STOP",
            "content": {"parts": [
                {"thought": True, "text": "ignore internal text"},
                {"text": json.dumps({"claims": [model_claim]})},
            ]},
        }]}).encode())

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)
    draft = providers.gemini_writer("gemini-test")(payload, reasons)
    accepted, rejected = check_draft(draft, {"imp:0001": payload["evidence"][0]})
    assert accepted == []
    assert "must match" in rejected[0]["reason"]
