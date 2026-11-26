"""Small JSON contracts shared by the coordinator and model adapters."""

from typing import TypedDict

from ..scanner import ScanError


class MechanismCandidate(TypedDict):
    id: str
    description: str
    rationale: str
    entry_points: list[str]
    evidence_ids: list[str]
    limitations: list[str]


class ProjectUnderstanding(TypedDict):
    snapshot_id: str
    repository: str
    commit: str
    purpose: dict
    capabilities: list[dict]
    concepts: list[str]
    candidates: list[MechanismCandidate]
    selected_candidate: str
    unknowns: list[str]


class MechanismSpecification(TypedDict):
    candidate_id: str
    summary: str
    entities: list[str]
    steps: list[dict]
    unknowns: list[str]


class VerificationReport(TypedDict):
    candidate_id: str
    steps: list[dict]
    revision_requests: list[str]


class OrchestrationRun(TypedDict):
    schema_version: int
    snapshot: dict
    provider: dict | None
    limits: dict
    stages: list[dict]
    terminal_status: str
    artifacts: dict
    limitations: list[str]
    telemetry: dict


def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def array(items, maximum=8):
    return {"type": "array", "items": items, "maxItems": maximum}


def choice(*values):
    return {"type": "string", "enum": list(values)}


TEXT = {"type": "string", "maxLength": 1200}
ID = {"type": "string", "maxLength": 300}
IDS = array(ID, 12)
STATUS = choice("supported", "partially_supported", "unsupported", "contradicted", "unresolved")
CLAIM = obj(text=TEXT, classification=choice("documented", "inferred", "unverified"), evidence_ids=IDS)
CANDIDATE = obj(id=ID, description=TEXT, rationale=TEXT, entry_points=IDS, evidence_ids=IDS, limitations=array(TEXT))
UNDERSTANDING = obj(purpose=CLAIM, capabilities=array(CLAIM), concepts=array(TEXT),
                    candidates=array(CANDIDATE, 4), selected_candidate=ID, unknowns=array(TEXT))

STEP = obj(id=ID, text=TEXT,
           kind=choice("written_relationship", "documented_behavior", "test_expectation", "interpretation"),
           evidence_ids=IDS, relationship_id=ID, subject=ID, object=ID, relationship_type=ID,
           scope_kind=ID, scope_path=ID, conditions=array(TEXT, 16), after=IDS)
MECHANISM = obj(candidate_id=ID, summary=TEXT, entities=IDS, steps=array(STEP), unknowns=array(TEXT),
                evidence_requests=array(ID, 3))
VERIFICATION = obj(candidate_id=ID, steps=array(obj(id=ID, status=STATUS, rationale=TEXT, missing_evidence=array(TEXT))),
                   revision_requests=array(TEXT),
                   contradictions=array(obj(id=ID, evidence_ids=IDS, rationale=TEXT), 8),
                   adequacy=array(obj(dimension=choice("entry", "participants", "operation", "conditions",
                                                       "state_changes", "outcome", "uncertainties"),
                                      status=choice("supported", "partial", "unresolved", "not_applicable"),
                                      step_ids=IDS, justification=TEXT), 7))


def validate(value, schema, path="result"):
    kind = schema["type"]
    if kind == "string":
        if not isinstance(value, str) or len(value) > schema.get("maxLength", 1200) or (
            "enum" in schema and value not in schema["enum"]
        ):
            raise ScanError(f"Invalid string at {path}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) > schema["maxItems"]:
            raise ScanError(f"Invalid array at {path}")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    elif kind == "object":
        if not isinstance(value, dict) or value.keys() != schema["properties"].keys():
            raise ScanError(f"Unexpected fields at {path}")
        for key, item in value.items():
            validate(item, schema["properties"][key], f"{path}.{key}")
