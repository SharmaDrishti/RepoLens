"""Compare bounded revisions without losing already verified claims."""


def accepted_rows(rows):
    return {row["step"]["id"]: row for row in rows if row["disposition"] == "accepted_with_classification"}


def claim_content(step):
    return {key: value for key, value in step.items() if key != "id"}


def revision_feedback(result):
    return [{
        "preserve_accepted_claims": [row["step"] for row in accepted_rows(result["steps"]).values()],
        "adequacy_gaps": [row for row in result["adequacy"]["dimensions"]
                          if row["status"] not in {"supported", "not_applicable"}],
        "rejected_claims": [
            {"id": row["step"]["id"], "step": row["step"], "checks": row["deterministic_errors"],
             "review": row["semantic"],
             "populated_typed_fields": [field for field in (
                 "relationship_id", "subject", "object", "relationship_type", "scope_kind", "scope_path", "conditions", "after"
             ) if row["step"].get(field)],
             "action": "Correct with matching evidence and fields, or omit.",
             "contract": ("Written relationships must copy the measured relationship and its condition JSON exactly. "
                          "Other kinds must leave all typed fields and conditions empty. "
                          "Documented behavior requires documentation; test expectations require test source. "
                          "Leave after empty. Narrow each claim to what its citations establish.")}
            for row in result["steps"] if row["disposition"] == "excluded"
        ],
        "review_requests": result["revision_requests"],
    }]


def merge_rows(previous, proposed, contradictions, evidence, packet):
    old = {row["step"]["id"]: row for row in previous}
    retained = accepted_rows(previous)
    superseded = {}
    for finding in contradictions:
        ref = finding["id"]
        if ref not in retained or not finding["rationale"].strip():
            continue
        citations = set(finding["evidence_ids"])
        previous_refs = set(retained[ref]["step"]["evidence_ids"])
        if citations - previous_refs and all(not evidence.check_reference(key, packet) for key in citations):
            superseded[ref] = finding
            del retained[ref]
    changes = [{"id": ref, "status": "superseded", "finding": finding}
               for ref, finding in superseded.items()]
    contradicted_content = [claim_content(old[ref]["step"]) for ref in superseded]
    rejected = []
    for row in proposed:
        step = row["step"]
        ref = step["id"]
        if ref in retained:
            if step != retained[ref]["step"]:
                changes.append({"id": ref, "status": "rejected", "reason": "An accepted identifier is already retained."})
            continue
        if any(claim_content(step) == claim_content(kept["step"]) for kept in retained.values()):
            changes.append({"id": ref, "status": "rejected", "reason": "Duplicates a retained claim under a different identifier."})
            continue
        if row["disposition"] == "excluded":
            rejected.append(row)
            changes.append({"id": ref, "status": "rejected", "review": row["semantic"]["status"]})
        else:
            if claim_content(step) in contradicted_content:
                rejected.append({**row, "disposition": "excluded", "deterministic_errors": [
                    "The unchanged claim was superseded by an evidence-backed contradiction."]})
                changes.append({"id": ref, "status": "rejected"})
                continue
            retained[ref] = row
            changes.append({"id": ref, "status": "corrected" if ref in old else "added"})
    changed_ids = {item["id"] for item in changes}
    changes.extend({"id": ref, "status": "unchanged"} for ref in retained if ref not in changed_ids)
    return [*retained.values(), *rejected], changes


def carry_coverage(previous, rows, dimensions):
    """Carry forward supported dimensions only if the supporting claims are unchanged."""
    current = {row["dimension"]: row for row in dimensions}
    old = accepted_rows(previous["steps"])
    kept = accepted_rows(rows)
    for row in previous["adequacy"]["dimensions"]:
        if (row["status"] in {"supported", "not_applicable"}
                and current.get(row["dimension"], {}).get("status") != "supported"
                and all(ref in kept and kept[ref]["step"] == old[ref]["step"] for ref in row["step_ids"])):
            current[row["dimension"]] = row
    return list(current.values())
