import hashlib
import json

import pytest

from live_mechanism_eval import score


def test_scoring_uses_reviewed_denominator_and_preserves_unknowns(tmp_path):
    artifact, ledger = tmp_path / "run.json", tmp_path / "review.json"
    rows = [
        {"step": {"id": "one"}, "disposition": "accepted_with_classification",
         "semantic": {"status": "supported"}, "deterministic_errors": []},
        {"step": {"id": "two"}, "disposition": "excluded",
         "semantic": {"status": "supported"}, "deterministic_errors": ["Invalid order"]},
        {"step": {"id": "three"}, "disposition": "excluded",
         "semantic": {"status": "unresolved"}, "deterministic_errors": []},
    ]
    artifact.write_text(json.dumps({
        "snapshot": {"commit": {"sha": "sha"}}, "artifacts": {"verification": {"steps": rows}},
        "telemetry": {"execution": "injected", "attempts_with_reported_usage": 0},
        "stages": [], "terminal_status": "partial",
    }))
    ledger.write_text(json.dumps({
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "commit": "sha",
        "claims": [{"id": identifier, "verdict": verdict, "notes": "Review", "references": ["file:1"]}
                   for identifier, verdict in [("one", "supported"), ("two", "unestablished"), ("three", None)]],
        "selection_quality": None, "retrieval_relevant": None, "retrieval_reviewed": None,
    }))
    result = score(artifact, ledger)
    assert result["supported"] == [1, 2]
    assert result["excluded_among_unsupported"] == [1, 1]
    assert result["generated_steps"] == 3
    assert result["reviewer_gate_disagreements"] == 1
    artifact.write_text(artifact.read_text() + "\n")
    with pytest.raises(ValueError, match="different artifact"):
        score(artifact, ledger)
