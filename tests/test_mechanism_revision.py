from repolens.mechanisms.adequacy import assess_adequacy
from repolens.mechanisms.revision import carry_coverage, merge_rows


class Evidence:
    def check_reference(self, ref, packet):
        return None if ref in packet["evidence"] else "missing"


def row(ref, source, relation):
    return {"step": {"id": ref, "text": ref, "relationship_id": relation,
                     "evidence_ids": [source], "conditions": []},
            "semantic": {"status": "supported"}, "disposition": "accepted_with_classification",
            "deterministic_errors": []}


def dimension(name, ref):
    return {"dimension": name, "status": "supported", "step_ids": [ref], "justification": "Checked coverage."}


def test_routing_contradiction_requires_different_pinned_source_and_retires_old_claim():
    old = row("route", "src:entry", "route")
    replacement = row("route", "src:guard", "new_route")
    finding = {"id": "route", "evidence_ids": ["src:guard"], "rationale": "The route has a conflicting guard."}
    assert merge_rows([old], [replacement], [finding], Evidence(), {"evidence": {}})[0] == [old]
    rows, changes = merge_rows([old], [replacement], [finding], Evidence(), {"evidence": {"src:guard": {}}})
    assert rows == [replacement]
    assert [change["status"] for change in changes] == ["superseded", "corrected"]


def test_transformation_addition_covers_missing_outcome_but_irrelevant_claim_does_not():
    prior = row("transform", "src:apply", "apply")
    previous = {"steps": [prior], "adequacy": {"dimensions": [
        dimension("entry", "transform"), dimension("operation", "transform")]}}
    packet = {"evidence": {}, "navigation": {"apply": {}, "return": {}},
              "relationships": {"apply": {"evidence_ids": ["src:apply"], "conditions": []},
                                "return": {"evidence_ids": ["src:result"], "conditions": []}}}
    unrelated = row("logger", "src:log", "log")
    for additional, expected in ((unrelated, "incomplete"), (row("result", "src:result", "return"), "adequate")):
        rows, changes = merge_rows([prior], [additional], [], Evidence(), packet)
        dimensions = carry_coverage(previous, rows, [dimension("outcome", additional["step"]["id"])])
        assert assess_adequacy("example", rows, packet, dimensions)["disposition"] == expected
        assert {item["status"] for item in changes} == {"added", "unchanged"}
