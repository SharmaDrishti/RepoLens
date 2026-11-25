"""Assess coverage separately from the gate that accepts individual claims."""


def assess_adequacy(candidate_id, rows, packet, dimensions):
    accepted = {row["step"]["id"]: row["step"] for row in rows
                if row["disposition"] == "accepted_with_classification"}
    graph = packet.get("navigation", {})
    anchored = set(packet.get("candidate_evidence_ids", []))
    for ref, navigation in graph.items():
        anchored.update(packet["relationships"][ref]["evidence_ids"])
        if navigation.get("window_id"):
            anchored.add(navigation["window_id"])
    results = []
    required = {"entry", "operation", "outcome"}
    if any(packet["relationships"][ref]["conditions"] for ref in graph):
        required.add("conditions")
    supplied = {row["dimension"]: row for row in dimensions}
    for name in dict.fromkeys([*sorted(required), *supplied]):
        row = supplied.get(name)
        if not row:
            results.append({"dimension": name, "status": "unresolved", "step_ids": [], "evidence_ids": [],
                            "justification": "No coverage assessment was supplied."})
            continue
        ids = row["step_ids"]
        eligible = [accepted[ref] for ref in ids if ref in accepted
                    and (accepted[ref]["relationship_id"] in graph or anchored.intersection(accepted[ref]["evidence_ids"]))
                    and (name != "conditions" or not accepted[ref]["relationship_id"] or accepted[ref].get("conditions"))]
        status = row["status"]
        if status in {"supported", "partial"} and (not ids or len(eligible) != len(ids)):
            status = "partial" if eligible else "unresolved"
        if status == "not_applicable" and (name in {"operation", "outcome"} or (name == "conditions" and name in required)):
            status = "unresolved"
        justification = row["justification"].strip() or "No justification supplied."
        if not row["justification"].strip():
            status = "unresolved"
        results.append({"dimension": name, "status": status, "step_ids": [step["id"] for step in eligible],
                        "evidence_ids": sorted({ref for step in eligible for ref in step["evidence_ids"]}),
                        "justification": justification,
                        **({"limitation": "Assessment lacked accepted claims tied to the selected evidence."}
                           if status != row["status"] else {})})
    complete = bool(accepted) and all(row["status"] in {"supported", "not_applicable"} for row in results)
    return {"schema_version": 1, "candidate_id": candidate_id,
            "disposition": "adequate" if complete else "incomplete" if accepted else "unresolved",
            "dimensions": results, "method": "Independent semantic coverage review with accepted-evidence checks."}
