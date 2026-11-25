"""Exercise both behavior shapes and verify that bad transitions fail closed."""

from copy import deepcopy
from io import BytesIO
import json
import subprocess
import sys
from urllib.error import HTTPError

import pytest

from repolens import behavior, providers
from repolens.behavior import checked_scenarios, generate_behavior
from repolens.scanner import ScanError


def scenario(identifier, choice, initial, steps, facts=("example",)):
    return {"id": identifier, "choice": choice, "initial_state": list(map(str, initial)),
            "steps": [
                {"id": f"{identifier}:{index}", "event": event, "state": list(map(str, state)),
                 "caption": caption, "fact_ids": list(facts)}
                for index, (event, state, caption) in enumerate(steps)
            ]}


def capacity_scenarios(facts=("example",)):
    initial = (2, 1, 2, 0)
    return [
        scenario("hold", "2", initial, [
            ("settle", (2, 0, 2, 1), "One task settles and the waiting task starts."),
        ], facts),
        scenario("raise", "3", initial, [
            ("limit", (3, 0, 3, 0), "Raising the limit opens a slot."),
        ], facts),
        scenario("lower", "1", initial, [
            ("limit", (1, 1, 2, 0), "Both active tasks continue."),
            ("settle", (1, 1, 1, 1), "One active task still fills the limit."),
            ("settle", (1, 0, 1, 2), "The remaining slot opens for the waiting task."),
        ], facts),
    ]


def request_scenarios(facts=("example",)):
    initial = ("GET", "", "", "", "")
    return [
        scenario("home", "/", initial, [
            ("submit", ("GET", "/", "", "", ""), "Request the home page."),
            ("match", ("GET", "/", "matched", "", ""), "The home rule matches."),
            ("dispatch", ("GET", "/", "matched", "hello_world", ""), "Call the bound function."),
            ("respond", ("GET", "/", "matched", "hello_world", "Hello, World!"), "Show the greeting."),
        ], facts),
        scenario("missing", "/missing", initial, [
            ("submit", ("GET", "/missing", "", "", ""), "Request another path."),
            ("match", ("GET", "/missing", "unmatched", "", ""), "No rule matches this path."),
            ("respond", ("GET", "/missing", "unmatched", "", "404 Not Found"), "Show the not-found outcome."),
        ], facts),
    ]


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    (root / "README.md").write_text("# Demo\n\nA library with a small example.\n", encoding="utf-8")
    (root / "demo.py").write_text("def example():\n    return 1\n", encoding="utf-8")
    (root / "test_demo.py").write_text("def test_example():\n    assert example() == 1\n", encoding="utf-8")
    for args in (("init", "-q"), ("add", "."),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Fixture")):
        subprocess.run(["git", "-C", str(root), *args], check=True)
    return root


@pytest.mark.parametrize("statuses,delays,exit_code", [
    ([503, 503, 200], [1, 2], 0),
    ([503, 503, 503], [1, 2], 1),
    ([403], [], 1),
])
def test_cli_handles_provider_errors(repository, tmp_path, monkeypatch, statuses, delays, exit_code):
    output = tmp_path / "behavior.json"
    responses = iter(statuses)
    waits = []
    monkeypatch.setattr(behavior, "sleep", waits.append)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-not-a-key")
    monkeypatch.setattr(sys, "argv", ["repolens", "behavior", str(repository),
                                    "--question", "What does the example return?",
                                    "--focus", "demo.py:1-2", "--focus", "test_demo.py:1-2",
                                    "--out", str(output)])
    refs = ["focus:demo.py:1-2", "focus:test_demo.py:1-2"]

    def transport(request, timeout):
        status = next(responses)
        if status != 200:
            raise HTTPError(request.full_url, status, "Fixture error", None, None)
        body = json.loads(request.data)
        payload = json.loads(body["contents"][0]["parts"][0]["text"])["facts"]
        assert payload["evidence"][refs[0]]["excerpt"] == "def example():\n    return 1"
        result = {"family": "none", "example": "Call example.", "assumptions": [],
                  "unknowns": ["There is no variable behavior to compare."], "scenarios": [],
                  "facts": [{"id": "example", "assertion": "The example returns one.",
                             "conditions": [], "evidence_ids": refs}]}
        return BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(result)}]}}]}).encode())

    monkeypatch.setattr(providers, "urlopen", transport)
    from repolens.__main__ import main

    assert main() == exit_code
    assert waits == delays
    assert next(responses, None) is None
    if exit_code:
        assert not output.exists()
        return
    record = json.loads(output.read_text())
    assert record["semantic_review"] == "pending"
    assert record["project"]["commit"]["pinned"]
    assert [entry["role"] for entry in record["facts"]["example"]["evidence"]] == ["source", "test_expectation"]
    assert record["scenarios"] == []
    assert "fixture-not-a-key" not in output.read_text()


@pytest.mark.parametrize("family,make_scenarios", [("capacity", capacity_scenarios), ("request", request_scenarios)])
def test_scenarios_require_consistent_transitions_and_checked_facts(family, make_scenarios):
    scenarios = make_scenarios()
    facts = {"example": {}}
    assert len(checked_scenarios(family, scenarios, facts)) == len(scenarios)
    invalid = deepcopy(scenarios)
    if family == "capacity":
        invalid[-1]["steps"][1]["state"] = ["1", "0", "2", "1"]
    else:
        invalid[-1]["steps"].insert(2, {"id": "invalid", "event": "dispatch",
                                       "state": ["GET", "/missing", "unmatched", "hello_world", ""],
                                       "caption": "Wrong handler.", "fact_ids": ["example"]})
        invalid[-1]["steps"][-1]["state"][3] = "hello_world"
    with pytest.raises(ScanError, match="Capacity transition|Request must follow"):
        checked_scenarios(family, invalid, facts)
    scenarios[0]["steps"][0]["fact_ids"] = ["missing"]
    with pytest.raises(ScanError, match="checked fact references"):
        checked_scenarios(family, scenarios, facts)


def test_draft_with_an_unknown_citation_does_not_write_record(repository, tmp_path):
    output = tmp_path / "behavior.json"

    def invoke(payload):
        return {"family": "none", "example": "Call example.", "assumptions": [],
                "unknowns": ["No comparison."], "scenarios": [],
                "facts": [{"id": "example", "assertion": "The example returns one.",
                           "conditions": [], "evidence_ids": ["not-supplied"]}]}

    with pytest.raises(ScanError, match="invalid pinned excerpt"):
        generate_behavior(str(repository), output, tmp_path, question="What is returned?", invoke=invoke)
    assert not output.exists()


def test_capacity_choices_can_end_at_the_same_counts_after_different_paths():
    scenarios = capacity_scenarios()
    for item in scenarios:
        limit, _, running, settled = map(int, item["steps"][-1]["state"])
        for offset in range(1, running + 1):
            item["steps"].append({
                "id": f"{item['id']}:finish:{offset}", "event": "settle",
                "state": list(map(str, (limit, 0, running - offset, settled + offset))),
                "caption": "One more task settles.", "fact_ids": ["example"],
            })
    checked = checked_scenarios("capacity", scenarios, {"example": {}})
    assert all(item["steps"][-1]["state"]["settled"] == 3 for item in checked)


def test_openrouter_behavior_records_serving_model(repository, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-not-a-key")
    output = tmp_path / "behavior.json"
    served_model = "fixture/example:free"

    def transport(request, timeout):
        assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
        assert request.get_header("Authorization") == "Bearer fixture-not-a-key"
        body = json.loads(request.data)
        assert body["model"] == "openrouter/free"
        assert body["max_tokens"] == 10_000
        assert body["provider"] == {"require_parameters": True}
        assert body["response_format"]["json_schema"]["strict"] is True
        payload = json.loads(body["messages"][1]["content"])["facts"]
        assert "focus:demo.py:1-2" in payload["evidence"]
        reply = {"family": "none", "example": "Call example.", "assumptions": [],
                 "unknowns": ["No comparison is documented."], "scenarios": [],
                 "facts": [{"id": "example", "assertion": "The example returns one.",
                            "conditions": [], "evidence_ids": ["focus:demo.py:1-2"]}]}
        result = {"model": served_model, "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(reply)}},
        ]}
        return BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(providers, "urlopen", transport)
    record = generate_behavior(str(repository), output, tmp_path, question="What is returned?",
                               provider="openrouter", focus=["demo.py:1-2"])
    assert record["generation"]["model"] == served_model
    assert record["generation"]["provider"] == "openrouter"
    assert "fixture-not-a-key" not in output.read_text()


def test_openrouter_rejects_paid_models_and_detects_errors_inside_http_200(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-not-a-key")
    with pytest.raises(ScanError, match="ending in :free"):
        providers.openrouter_writer("fixture/paid")

    def transport(request, timeout):
        return BytesIO(b'{"error":{"code":503,"message":"details to omit"}}')

    monkeypatch.setattr(providers, "urlopen", transport)
    with pytest.raises(providers.ProviderError, match=r"^service_error \(HTTP 503\)$"):
        providers.openrouter_writer("fixture/example:free")({}, [])
