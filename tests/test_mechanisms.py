import json
from pathlib import Path
import subprocess

import pytest

from repolens.mechanisms.evidence import condition_text
from repolens.mechanisms.orchestrator import Limits, run_mechanisms


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "example"
    root.mkdir()
    (root / "README.md").write_text("Example is a Python tool for processing files.\n\n"
                                   "The processor checks a flag before it collects a file.\n")
    (root / "process.py").write_text("import other\n\n"
                                    "def collect():\n    return 'file'\n\n"
                                    "def process(flag):\n    if flag:\n        return collect()\n")
    (root / "other.py").write_text("def something():\n    return None\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "Fixture"], check=True)
    return root


class Responses:
    def __init__(self, fault=None, *, revise=False):
        self.roles = []
        self.fault = fault
        self.revise = revise

    def __call__(self, role, payload, max_tokens, timeout):
        self.roles.append(role.name)
        assert role.instructions and max_tokens <= 2200 and timeout == 60
        if role.name == "understanding":
            snapshot = payload["snapshot"]
            ref = next(key for key, item in payload["source"]["evidence"].items()
                       if item["type"] == "documentation")
            claim = {"text": "Processes files", "classification": "documented", "evidence_ids": [ref]}
            return {"snapshot_id": snapshot["id"], "repository": snapshot["repo"],
                    "commit": snapshot["commit"]["sha"], "purpose": claim, "capabilities": [claim],
                    "concepts": ["processing"], "unknowns": [], "selected_candidate": "file-processing",
                    "candidates": [{"id": "file-processing", "description": "process collect file flag",
                                    "rationale": "Central capability", "evidence_ids": [ref],
                                    "entry_points": [], "limitations": []}]}
        if role.name == "investigator":
            packet = payload["source"]
            fault = None if self.revise and payload["revision_requests"] else self.fault
            relationship = next(item for item in packet["relationships"].values()
                                if item["type"] == ("imports" if fault == "import" else "calls"))
            step = {"id": "step:1", "kind": "written_relationship", "text": "A call is written under a flag guard.",
                    "relationship_id": relationship["id"], "relationship_type": relationship["type"],
                    "subject": relationship["subject"], "object": relationship["object"] or "",
                    "scope_kind": relationship["scope"]["kind"], "scope_path": relationship["scope"]["path"],
                    "conditions": [condition_text(cond) for cond in relationship["conditions"]],
                    "evidence_ids": relationship["evidence_ids"], "after": []}
            if fault == "reverse":
                step["subject"], step["object"] = step["object"], step["subject"]
            elif fault == "condition":
                step["conditions"] = []
            elif fault == "symbol":
                step["object"] = "entity:missing"
            elif fault == "wrong_file":
                step["object"] = "file:other.py"
            elif fault == "order":
                step["after"] = ["step:earlier"]
            elif fault == "citation":
                step["evidence_ids"] = payload["candidate"]["evidence_ids"]
            elif fault == "unavailable":
                step["evidence_ids"] = ["source:missing"]
            elif fault == "contradiction":
                step["text"] = "The call always runs even if the flag is false."
            return {"candidate_id": payload["candidate"]["id"], "summary": "File processing draft",
                    "entities": [relationship["subject"]], "steps": [step], "unknowns": ["runtime not observed"]}
        assert role.name == "verification"
        assert "revision_requests" not in payload
        draft = payload["draft"]
        step = draft["steps"][0]
        status = "contradicted" if "always" in step["text"] else "supported"
        return {"candidate_id": draft["candidate_id"],
                "steps": [{"id": step["id"], "status": status,
                           "rationale": "Review of source and guard.", "missing_evidence": []}],
                "revision_requests": ["Preserve guard."] if status == "contradicted" else []}


def execute(project, model=None, **options):
    return run_mechanisms(str(project), project.parent / "mechanisms.json", project.parent / "cache",
                          invoke=model, **options)


def test_uses_distinct_roles_and_serializes_evidence(project):
    model = Responses()
    run, trace = execute(project, model)
    assert run["terminal_status"] == "supported"
    assert model.roles == ["understanding", "investigator", "verification"]
    assert len(trace["attempts"]) == 3 and "input" not in run["stages"][0]
    step = run["artifacts"]["mechanism"]["steps"][0]
    assert step["conditions"]
    assert all(run["artifacts"]["evidence"][ref]["snapshot_id"] == run["snapshot"]["id"] for ref in step["evidence_ids"])
    assert json.loads(json.dumps(run)) == run


@pytest.mark.parametrize("fault", ["reverse", "import", "condition", "symbol", "wrong_file", "order", "citation", "unavailable"])
def test_mechanical_gate_overrides_agreeable_reviewer(project, fault):
    run, _ = execute(project, Responses(fault), limits=Limits(revisions=0))
    assert run["terminal_status"] == "unresolved"
    assert "mechanism" not in run["artifacts"]
    step = run["artifacts"]["verification"]["steps"][0]
    assert step["semantic"]["status"] == "supported"
    assert step["deterministic_errors"]


def test_semantic_contradiction_triggers_one_revision(project):
    model = Responses("contradiction", revise=True)
    run, trace = execute(project, model)
    assert model.roles == ["understanding", "investigator", "verification", "investigator", "verification"]
    assert trace["attempts"][2]["output"]["steps"][0]["status"] == "contradicted"
    assert run["terminal_status"] == "supported"


def test_deterministic_mode_dirty_checkout_and_no_provider(project):
    model = Responses()
    run, trace = execute(project, model, no_ai=True)
    assert run["terminal_status"] == "deterministic_only"
    assert all(stage["status"] == "skipped" for stage in run["stages"])
    assert not trace["attempts"] and not model.roles
    (project / "process.py").write_text("def collect():\n    return 2\n")
    run, _ = execute(project, model)
    assert run["terminal_status"] == "unresolved" and "clean" in run["reason"]
    assert not model.roles


def test_provider_failure_is_sanitized_and_budget_limits_calls(project):
    def failing(*args):
        raise RuntimeError("private-provider-token")
    run, trace = execute(project, failing)
    assert run["terminal_status"] == "failed"
    assert "private-provider-token" not in json.dumps([run, trace])
    model = Responses("reverse")
    run, _ = execute(project, model, limits=Limits(max_calls=3))
    assert run["terminal_status"] == "unresolved" and len(model.roles) == 3


def test_expected_commit_rejects_mismatch(project):
    from repolens.scanner import ScanError
    with pytest.raises(ScanError, match="requested pinned commit"):
        execute(project, Responses(), expected_commit="f" * 40)


def test_unavailable_mechanism_stops_before_review(project):
    model = Responses()
    def empty(role, payload, cap, timeout):
        result = model(role, payload, cap, timeout)
        if role.name == "investigator":
            result.update(steps=[], unknowns=["The relevant implementation is unavailable."])
        return result

    run, _ = execute(project, empty)
    assert run["terminal_status"] == "unresolved"
    assert model.roles == ["understanding", "investigator"]
    assert run["artifacts"]["verification"]["unknowns"]


def test_missing_credentials_are_actionable(project, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    run, trace = execute(project)
    assert run["terminal_status"] == "failed"
    assert "GEMINI_API_KEY" in run["reason"]
    assert not trace["attempts"]


@pytest.mark.parametrize("oversized_investigator_reply", [False, True])
def test_gemini_adapter_invokes_three_distinct_structured_roles(project, monkeypatch, oversized_investigator_reply):
    from io import BytesIO
    from repolens import providers

    model = Responses()
    from repolens.mechanisms.orchestrator import INVESTIGATE, REVIEW, ROLES
    schemas = []

    def transport(request, timeout):
        body = json.loads(request.data)
        role = ROLES[len(schemas)]
        assert body["systemInstruction"]["parts"][0]["text"] == role.instructions
        schema = body["generationConfig"]["responseJsonSchema"]
        schemas.append(schema)
        if role in (INVESTIGATE, REVIEW):
            assert '"maxItems"' not in json.dumps(schema)
            assert '"maxItems"' in json.dumps(role.schema)
            assert schema == providers.without_array_bounds(role.schema)
        else:
            assert schema == role.schema
        data = json.loads(body["contents"][0]["parts"][0]["text"])["facts"]
        output = model(role, data, body["generationConfig"]["maxOutputTokens"], timeout)
        if role is INVESTIGATE and oversized_investigator_reply:
            output["steps"] *= 9
        return BytesIO(json.dumps({"candidates": [{"finishReason": "STOP",
                                                   "content": {"parts": [{"text": json.dumps(output)}]}}],
                                   "modelVersion": "gemini-test-revision",
                                   "usageMetadata": {"promptTokenCount": 123, "candidatesTokenCount": 45,
                                                     "thoughtsTokenCount": 2, "totalTokenCount": 170,
                                                     "ignored": "synthetic-api-key"}}).encode())

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-api-key")
    monkeypatch.setattr(providers, "urlopen", transport)
    run, trace = execute(project)
    if oversized_investigator_reply:
        assert run["terminal_status"] == "failed"
        assert run["reason"] == "Invalid array at result.steps"
        assert len(schemas) == 2
        return
    assert run["terminal_status"] == "supported"
    assert len(schemas) == 3 and "synthetic-api-key" not in json.dumps([run, trace])
    assert run["telemetry"]["provider_responses"] == 3
    assert run["telemetry"]["attempts_with_reported_usage"] == 3
    assert all(stage["usage"] == {"input_tokens": 123, "output_tokens": 45, "total_tokens": 170,
                                  "thinking_tokens": 2} for stage in run["stages"])
    assert all(stage["provider_model"] == "gemini-test-revision" and stage["latency_ms"] >= 0
               and stage["started_at"] <= stage["finished_at"] for stage in run["stages"])


def test_cross_snapshot_citation_is_rejected_through_run(project, monkeypatch):
    from repolens.mechanisms.evidence import RepositoryEvidence

    original = RepositoryEvidence.packet
    def foreign(self, *args, **kwargs):
        packet = original(self, *args, **kwargs)
        if kwargs.get("investigation"):
            for ref, record in packet["evidence"].items():
                if record["type"] == "source_code":
                    packet["evidence"][ref] = {**record, "snapshot_id": "snapshot:foreign"}
        return packet

    monkeypatch.setattr(RepositoryEvidence, "packet", foreign)
    run, _ = execute(project, Responses(), limits=Limits(revisions=0))
    assert run["terminal_status"] == "unresolved"
    step = run["artifacts"]["verification"]["steps"][0]
    assert any("not supplied for this snapshot" in error for error in step["deterministic_errors"])


def test_review_must_cover_every_claim(project):
    model = Responses()
    def incomplete(role, payload, cap, timeout):
        result = model(role, payload, cap, timeout)
        if role.name == "verification":
            result["steps"] = []
        return result

    run, _ = execute(project, incomplete)
    assert run["terminal_status"] == "failed"
    assert "exactly once" in run["reason"]
    assert "mechanism" not in run["artifacts"]


def test_understanding_uses_snapshot_identity_and_preserves_entry_hypotheses(project, monkeypatch):
    from repolens.mechanisms.evidence import RepositoryEvidence

    original_packet = RepositoryEvidence.packet
    def known_file(self, *args, **kwargs):
        packet = original_packet(self, *args, **kwargs)
        # The captured Flask packet already contained the equivalent file entity.
        packet["entities"]["file:process.py"] = self.entities["file:process.py"]
        return packet

    monkeypatch.setattr(RepositoryEvidence, "packet", known_file)
    model = Responses()

    def return_path(role, payload, cap, timeout):
        result = model(role, payload, cap, timeout)
        if role.name == "understanding":
            result["repository"] = payload["snapshot"]["source"]
            result["candidates"][0]["entry_points"] = ["process.py", "pLimit(concurrency)"]
        elif role.name == "investigator":
            assert payload["candidate"]["entry_points"] == ["file:process.py"]
            assert payload["candidate"]["unresolved_entry_hypotheses"] == ["pLimit(concurrency)"]
        return result

    run, trace = execute(project, return_path)
    assert run["terminal_status"] == "supported"
    assert run["artifacts"]["understanding"]["repository"] == project.name
    assert trace["attempts"][0]["output"]["candidates"][0]["entry_points"] == ["process.py", "pLimit(concurrency)"]


def test_reported_github_identity_alias_requires_the_same_snapshot_and_commit():
    from repolens.mechanisms.orchestrator import understanding_fields
    from repolens.scanner import ScanError

    url = "https://github.com/sindresorhus/p-limit"
    identity = {"repo": "p-limit", "id": "snapshot:fixture", "source": url,
                "commit": {"sha": "a" * 40, "remote_url": url + ".git"}}
    output = {"repository": url, "snapshot_id": identity["id"], "commit": "a" * 40}
    assert understanding_fields(output, identity) == {}
    with pytest.raises(ScanError, match="pinned repository"):
        understanding_fields({**output, "commit": "b" * 40}, identity)
    with pytest.raises(ScanError, match="pinned repository"):
        understanding_fields({**output, "repository": url + "-different"}, identity)


@pytest.mark.parametrize(("status", "retried"), [(503, True), (429, False), (401, False), (404, False), (400, False)])
def test_provider_errors_record_safe_status_and_retry_only_transient(project, monkeypatch, status, retried):
    from repolens.mechanisms import orchestrator
    from repolens.providers import http_failure

    delays = []
    monkeypatch.setattr(orchestrator, "sleep", delays.append)
    model = Responses()
    def invoke(role, payload, cap, timeout):
        if role.name == "understanding":
            raise http_failure(status)
        return model(role, payload, cap, timeout)

    run, trace = execute(project, invoke, limits=Limits(max_calls=2))
    assert run["terminal_status"] == "failed"
    assert len(trace["attempts"]) == 1 + retried
    assert trace["attempts"][0]["diagnostic"]["http_status"] == status
    assert bool(delays) == retried


def test_gemini_http_diagnostic_drops_response_body_and_url(project, monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    from repolens import providers

    def transport(request, timeout):
        raise HTTPError("https://example.invalid/private-value", 429, "private-value", {}, BytesIO(b"private-value"))

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-api-key")
    monkeypatch.setattr(providers, "urlopen", transport)
    run, trace = execute(project)
    assert len(trace["attempts"]) == 1
    assert trace["attempts"][0]["diagnostic"] == {
        "category": "rate_limit_or_quota", "http_status": 429, "transient": False,
    }
    assert "private-value" not in json.dumps([run, trace])


def test_omitted_evidence_prefix_only_binds_to_unique_supplied_id(project):
    from copy import deepcopy
    from repolens.mechanisms.orchestrator import bind_evidence_ids, UNDERSTAND

    model = Responses()
    def invoke(role, payload, cap, timeout):
        result = model(role, payload, cap, timeout)
        if role is UNDERSTAND:
            from repolens.mechanisms.orchestrator import understanding_fields
            packet = payload["source"]
            value = deepcopy(understanding_fields(result, payload["snapshot"]))
            ref = "881e99c5f0092080634a7db8"
            value["capabilities"][0]["evidence_ids"] = [ref]
            bound = {**packet, "evidence": {"context:" + ref: {}}}
            assert bind_evidence_ids(value, bound)["capabilities"][0]["evidence_ids"] == ["context:" + ref]
            ambiguous = deepcopy(bound)
            ambiguous["evidence"]["source:" + ref] = {}
            assert bind_evidence_ids(value, ambiguous)["capabilities"][0]["evidence_ids"] == [ref]
            assert value["capabilities"][0]["evidence_ids"] == [ref]
        return result

    run, _ = execute(project, invoke)
    assert run["terminal_status"] == "supported"


def test_gemini_investigator_400_records_schema_details_without_leaking(monkeypatch):
    from io import BytesIO
    from urllib.error import HTTPError
    from repolens import providers
    from repolens.mechanisms.contracts import MECHANISM

    attempts = []
    def transport(request, timeout):
        attempts.append(json.loads(request.data)["generationConfig"]["responseJsonSchema"])
        body = {"error": {"status": "INVALID_ARGUMENT", "message": "Schema has too many states. private-value",
                          "details": [{"@type": "type.googleapis.com/google.rpc.BadRequest",
                                       "fieldViolations": [
                                           {"field": "generationConfig.responseJsonSchema.properties.steps.maxItems",
                                            "description": "private-value"},
                                           {"field": "generationConfig.private_value"},
                                       ]}]}}
        raise HTTPError("https://example.invalid/private-value", 400, "private-value", {},
                        BytesIO(json.dumps(body).encode()))

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-api-key")
    monkeypatch.setattr(providers, "urlopen", transport)
    with pytest.raises(providers.ProviderError) as caught:
        providers.gemini_writer("example-model", schema=MECHANISM)({"synthetic": True}, [])
    assert attempts == [MECHANISM]
    assert caught.value.diagnostic() == {
        "category": "invalid_request", "http_status": 400, "transient": False,
        "api_status": "INVALID_ARGUMENT", "request_issue": "structured_output_complexity",
        "fields": ["generationConfig.responseJsonSchema.properties.steps.maxItems"],
    }
    assert "private-value" not in str(caught.value)


def test_revision_preserves_accepted_claim_and_stops_repeated_invalid_reply(project):
    model = Responses()
    calls = []

    def invoke(role, payload, cap, timeout):
        calls.append(role.name)
        if role.name == "verification":
            return {"candidate_id": payload["draft"]["candidate_id"], "revision_requests": [],
                    "steps": [{"id": step["id"], "status": "supported", "rationale": "Control",
                               "missing_evidence": []} for step in payload["draft"]["steps"]]}
        reply = model(role, payload, cap, timeout)
        if role.name != "investigator":
            return reply
        valid = reply["steps"][0]
        invalid = {**valid, "id": "bad-class", "kind": "documented_behavior"}
        if payload["revision_requests"]:
            feedback = payload["revision_requests"][0]
            assert feedback["preserve_accepted_claims"] == [valid]
            assert feedback["adequacy_gaps"]
            assert feedback["rejected_claims"][0]["id"] == "bad-class"
            assert "matching evidence" in feedback["rejected_claims"][0]["action"]
            reply["steps"] = [invalid]
        else:
            reply["steps"] = [valid, invalid]
        return reply

    run, _ = execute(project, invoke)
    assert calls == ["understanding", "investigator", "verification", "investigator"]
    assert run["terminal_status"] == "partial"
    assert [step["id"] for step in run["artifacts"]["mechanism"]["steps"]] == ["step:1"]
    assert run["artifacts"]["adequacy"]["disposition"] == "incomplete"
    assert run["artifacts"]["verification"]["revision_status"] == "no_material_change"


def test_revision_corrects_mixed_evidence_kind_and_preserves_step_id(project):
    model = Responses()

    def invoke(role, payload, cap, timeout):
        result = model(role, payload, cap, timeout)
        if role.name == "investigator" and not payload["revision_requests"]:
            result["steps"][0]["kind"] = "documented_behavior"
        if role.name == "verification":
            assert "structural_diagnostics" in payload
        return result

    run, _ = execute(project, invoke)
    assert run["terminal_status"] == "supported"
    assert run["artifacts"]["mechanism"]["steps"][0]["id"] == "step:1"
    assert run["artifacts"]["verification"]["revision_history"][1]["changes"] == [
        {"id": "step:1", "status": "corrected"}]
    assert run["artifacts"]["adequacy"]["disposition"] == "incomplete"
