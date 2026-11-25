from repolens.mechanisms.adequacy import assess_adequacy
from repolens.mechanisms.evidence import RepositoryEvidence
from repolens.snapshot import open_snapshot


def test_peripheral_claims_and_missing_guard_do_not_establish_adequacy():
    packet = {
        "candidate_evidence_ids": [],
        "navigation": {"central": {"depth": 0}},
        "relationships": {"central": {"evidence_ids": ["src:guard"], "conditions": [{}]}},
    }
    rows = [
        {"step": {"id": "setup", "relationship_id": "elsewhere", "evidence_ids": ["src:setup"]},
         "disposition": "accepted_with_classification"},
        {"step": {"id": "guard", "relationship_id": "central", "evidence_ids": ["src:guard"]},
         "disposition": "excluded"},
    ]
    dimensions = [{"dimension": name, "status": "supported", "step_ids": ["setup"],
                   "justification": "Programmed overclaim."} for name in ("entry", "operation", "outcome")]
    dimensions.append({"dimension": "conditions", "status": "supported",
                       "step_ids": ["guard"], "justification": "Programmed overclaim."})
    result = assess_adequacy("test", rows, packet, dimensions)
    assert result["disposition"] == "incomplete"
    assert {row["status"] for row in result["dimensions"]} == {"unresolved"}
    assert assess_adequacy("test", [], packet, [])["disposition"] == "unresolved"


def test_retrieval_follows_guarded_helper_cycle_and_cross_file_hint(tmp_path):
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "api.py").write_text("def process(flag):\n    return flag\n")
    (tmp_path / "api.py").write_text("from helper import normalize\n"
                                    "def process(flag):\n    if flag:\n        return normalize(flag)\n"
                                    "    return unknown(flag)\n")
    (tmp_path / "helper.py").write_text("def normalize(flag):\n    return reform(flag)\n"
                                       "def reform(flag):\n    return normalize(flag)\n")
    snapshot = open_snapshot(str(tmp_path), tmp_path / "out.json", tmp_path / "cache")
    evidence = RepositoryEvidence(snapshot)
    packet = evidence.packet("process", investigation=True)
    route = [packet["relationships"][ref] for ref in packet["navigation"]]
    assert any(row["location"]["path"] == "helper.py" for row in route)
    assert any(row["target_text"] == "normalize" and row["conditions"] and
               row["resolution"] == "unresolved" for row in route)
    assert any(row["target_text"] == "unknown" and not row["object"] for row in route)
    assert any(row["via"] == "unresolved_import_name" for row in packet["navigation"].values())
    assert len(route) <= 22
    assert all(row["location"]["path"] != "examples/api.py" for row in route)


def test_pure_transformation_can_be_adequate_without_a_guard():
    step = {"id": "transform", "relationship_id": "return", "evidence_ids": ["src:return"], "conditions": []}
    packet = {"navigation": {"return": {"depth": 0}},
              "relationships": {"return": {"evidence_ids": ["src:return"], "conditions": []}}}
    assessment = assess_adequacy("transform", [{"step": step, "disposition": "accepted_with_classification"}], packet, [
        {"dimension": "entry", "status": "not_applicable", "step_ids": [],
         "justification": "The candidate is a local expression without a public entry."},
        *({"dimension": name, "status": "supported", "step_ids": ["transform"],
           "justification": "The expression states the transformation and returns it."} for name in ("operation", "outcome")),
    ])
    assert assessment["disposition"] == "adequate"


def test_expansion_accepts_only_packet_ids_and_adds_pinned_evidence(tmp_path):
    from repolens.mechanisms.orchestrator import expand_packet

    (tmp_path / "api.py").write_text("def process(flag):\n    return helper(flag)\n"
                                    "def helper(flag):\n    return not flag\n")
    snapshot = open_snapshot(str(tmp_path), tmp_path / "out.json", tmp_path / "cache")
    evidence = RepositoryEvidence(snapshot)
    identifier = next(key for key, entity in evidence.entities.items() if entity["name"] == "process")
    packet = {"evidence": {}, "relationships": {}, "navigation": {}, "entities": {identifier: evidence.entities[identifier]}}
    candidate = {"description": "process", "rationale": "", "entry_points": [], "evidence_ids": []}
    assert expand_packet(evidence, packet, candidate, ["../../secret"]) == []
    added = expand_packet(evidence, packet, candidate, [identifier])
    assert added and all(evidence.check_reference(ref, packet) is None for ref in added)
    assert any(record["location"]["line"] == 4 for record in packet["relationships"].values())


def test_prose_candidate_uses_cited_callable_and_follows_its_returned_helper(tmp_path):
    (tmp_path / "index.js").write_text(
        "export default function makeReader() {\n"
        "  const collect = input => {\n"
        "    if (input) {\n"
        "      return missing(input);\n"
        "    }\n"
        "  };\n"
        "  return collect;\n"
        "}\n"
    )
    (tmp_path / "README.md").write_text("Use the example:\n\n```js\nconst reader = makeReader();\n```\n")
    snapshot = open_snapshot(str(tmp_path), tmp_path / "out.json", tmp_path / "cache")
    evidence = RepositoryEvidence(snapshot)
    evidence.packet("example")
    reference = next(key for key, record in evidence.records.items()
                     if record["type"] == "documentation" and "makeReader(" in record["excerpt"])
    without = evidence.packet("Selecting a document transformation.", investigation=True)
    assert not without["navigation"]
    packet = evidence.packet("Selecting a document transformation.", required_refs=[reference], investigation=True)
    guarded = next(relation for relation in packet["relationships"].values()
                   if relation["target_text"] == "missing")
    assert packet["navigation"][guarded["id"]]["via"] == "returned_local_name"
    assert guarded["conditions"] and guarded["object"] is None
    assert evidence.check_reference(packet["navigation"][guarded["id"]]["window_id"], packet) is None
