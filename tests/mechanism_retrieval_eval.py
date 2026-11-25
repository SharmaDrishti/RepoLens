"""Compare evidence packets for candidates from saved model traces without calling an API."""

import json
from pathlib import Path
import sys
from tempfile import gettempdir

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repolens.mechanisms.adequacy import assess_adequacy
from repolens.mechanisms.evidence import RepositoryEvidence
from repolens.snapshot import open_snapshot


def compare(trace_path, output):
    trace = json.loads(trace_path.read_text())
    initial = next(row for row in trace["attempts"] if row["role"] == "understanding")
    attempt = next(row for row in trace["attempts"] if row["role"] == "investigator")
    candidate = attempt["input"]["candidate"]
    before = attempt["input"]["source"]
    identity = initial["input"]["snapshot"]
    snapshot = open_snapshot(identity["source"], output, Path(gettempdir()) / "repolens-cache")
    if snapshot.identity["id"] != identity["id"] or not snapshot.identity["commit"]["pinned"]:
        raise ValueError("Captured trace and current pinned snapshot differ")
    engine = RepositoryEvidence(snapshot)
    engine.packet()
    after = engine.packet(candidate["description"] + " " + candidate["rationale"], candidate["entry_points"],
                          candidate["evidence_ids"], investigation=True)
    after["candidate_evidence_ids"] = candidate["evidence_ids"]
    missing = [ref for ref in candidate["evidence_ids"] if ref not in after["evidence"]]
    if missing:
        raise ValueError("Candidate evidence was not reproduced")
    for ref in after["evidence"]:
        if error := engine.check_reference(ref, after):
            raise ValueError(f"{ref}: {error}")

    original = trace_path.with_name(trace_path.name.replace(".trace.json", ".json"))
    original_rows = json.loads(original.read_text())["artifacts"].get("verification", {}).get("steps", [])
    assessment = assess_adequacy(candidate["id"], original_rows, after, [])
    result = {"commit": identity["commit"]["sha"], "candidate": candidate,
              "mode": "captured_candidate_no_model_calls", "before": before, "after": after,
              "historical_claims_reassessed": assessment}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output.name, "relations", len(before["relationships"]), "→", len(after["relationships"]),
          "connected", len(after["navigation"]), "evidence", len(before["evidence"]), "→", len(after["evidence"]),
          "JSON bytes", len(json.dumps(before).encode()), "→", len(json.dumps(after).encode()))


if __name__ == "__main__":
    compare(Path(sys.argv[1]), Path(sys.argv[2]))
