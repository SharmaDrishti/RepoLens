"""Opt-in read-only packet smoke test on cached, pinned public repositories.

The query and verdicts are test controls. This does not measure model discovery.
Run from the workspace with PYTHONPATH=. python tests/mechanism_eval.py <directory>.
"""

import json
from pathlib import Path
import sys
from tempfile import gettempdir

from repolens.mechanisms.evidence import condition_text
from repolens.mechanisms.orchestrator import Limits, run_mechanisms

CASES = [
    ("p-limit", "sindresorhus/p-limit", "a8a6fbec4e0e866d6d779b10889bb4f5567e70eb",
     "enqueue concurrency activeCount resumeNext queue", "index.js"),
    ("flask", "pallets/flask", "49943b5a94413a530761350f04e896f76e8d620e",
     "request dispatch routing url adapter match response", "src/flask/app.py"),
]


def mock_model(query, target):
    def respond(role, payload, max_tokens, timeout):
        candidate_id = "controlled-query"
        packet = payload["source"]
        if role.name == "understanding":
            snapshot = payload["snapshot"]
            source = next(key for key, evidence in packet["evidence"].items()
                          if evidence["type"] == "documentation")
            return {"snapshot_id": snapshot["id"], "repository": snapshot["repo"],
                    "commit": snapshot["commit"]["sha"],
                    "purpose": {"text": "Purpose is not assessed by this test.",
                                "classification": "unverified", "evidence_ids": []},
                    "capabilities": [], "concepts": [], "unknowns": [],
                    "candidates": [{"id": candidate_id, "description": query, "rationale": "Evaluator-supplied probe",
                                    "entry_points": [], "evidence_ids": [source], "limitations": ["Mock selection"]}],
                    "selected_candidate": candidate_id}
        if role.name == "investigator":
            matching = [item for item in packet["relationships"].values()
                        if item["type"] == "calls" and item["conditions"] and item["location"]["path"] == target]
            if not matching:
                return {"candidate_id": candidate_id, "summary": "No matching call found", "entities": [],
                        "steps": [], "unknowns": ["Probe did not retrieve a conditional call in the target file."]}
            record = matching[0]
            claim = {"id": "measured-call", "kind": "written_relationship",
                     "text": f"Source contains the call expression {record['target_text']}; runtime dispatch is unobserved.",
                     "evidence_ids": record["evidence_ids"], "relationship_id": record["id"],
                     "subject": record["subject"], "object": record["object"] or "",
                     "relationship_type": record["type"], "scope_kind": record["scope"]["kind"],
                     "scope_path": record["scope"]["path"] or "",
                     "conditions": [condition_text(c) for c in record["conditions"]], "after": []}
            adversarial = {**claim, "id": "invalid-order", "after": ["measured-call"]}
            return {"candidate_id": candidate_id, "summary": "Controlled evidence plumbing probe",
                    "entities": [record["subject"]], "steps": [claim, adversarial],
                    "unknowns": ["The call target and runtime order require independent evidence."]}
        return {"candidate_id": candidate_id, "revision_requests": [],
                "steps": [{"id": step["id"], "status": "supported", "rationale": "Programmed verdict",
                           "missing_evidence": []} for step in payload["draft"]["steps"]]}
    return respond


def main(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name, repo, sha, query, target in CASES:
        output = directory / f"{name}-mock.json"
        run, trace = run_mechanisms("https://github.com/" + repo, output, Path(gettempdir()) / "repolens-cache",
                                    expected_commit=sha, provider="mock", model="controlled-query",
                                    invoke=mock_model(query, target), limits=Limits(revisions=0))
        run["evaluation"] = "Evaluator supplied the query; model replies and semantic verdicts are programmed."
        output.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
        (directory / f"{name}-mock.trace.json").write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        rows = run["artifacts"].get("verification", {}).get("steps", [])
        print(name, run["terminal_status"], [(row["step"]["text"], row["deterministic_errors"]) for row in rows])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
