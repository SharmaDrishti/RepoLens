"""Build and validate the versioned repository knowledge exchanged with the page."""

from pathlib import PurePosixPath
import subprocess
from typing import Literal, TypedDict

from .checker import source_url
from .scanner import ScanError
from .snapshot import Snapshot

EvidenceType = Literal["source_code", "import_relationship", "documentation", "configuration",
                       "example", "test_assertion", "interpretation"]


class EvidenceRecord(TypedDict):
    id: str
    type: EvidenceType
    snapshot_id: str
    path: str
    line: int
    end_line: int
    excerpt: str
    url: str | None
    scope: dict
    limitations: list[str]


class Knowledge(TypedDict):
    schema_version: int
    snapshot: dict
    context: dict
    relationships: dict
    developer: dict
    metrics: dict
    evidence: dict[str, EvidenceRecord]
    limitations: list[str]


CONTEXT_FILES = {
    "purpose.json": "purpose",
    "usecases.json": "use_cases",
    "getstarted.json": "getting_started",
}
EVIDENCE_TYPES = {"source_code", "import_relationship", "documentation", "configuration",
                  "example", "test_assertion", "interpretation"}


def validate_knowledge(model: Knowledge) -> None:
    if (not isinstance(model, dict) or set(model) != set(Knowledge.__annotations__)
            or type(model.get("schema_version")) is not int or model["schema_version"] != 1):
        raise ScanError("Invalid knowledge model version or fields.")
    if any(not isinstance(model[key], dict) for key in ("snapshot", "context", "relationships", "developer", "metrics", "evidence")):
        raise ScanError("Invalid knowledge model sections.")
    snapshot = model["snapshot"]
    if (not isinstance(snapshot.get("id"), str) or not isinstance(snapshot.get("files"), list)
            or not isinstance(snapshot.get("commit"), dict) or not isinstance(model["limitations"], list)
            or set(model["context"]) != set(CONTEXT_FILES.values())):
        raise ScanError("Invalid snapshot, context, or limitations.")
    tree = snapshot.get("working_tree")
    if (tree not in {"clean", "dirty", "unversioned", "unknown"} or
            snapshot["commit"].get("pinned") != (tree == "clean") or
            snapshot.get("content") != ("commit" if tree == "clean" else "working_tree") or
            any(not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in snapshot["files"])):
        raise ScanError("Invalid snapshot provenance or file inventory.")
    if any(not isinstance(group, dict) for group in model["context"].values()):
        raise ScanError("Invalid context groups.")
    context = model["context"]
    for field in ("what_it_is", "who_uses_it", "problem_it_solves"):
        if not isinstance(context["purpose"].get(field), dict):
            raise ScanError(f"Invalid purpose field: {field}.")
    if not isinstance(context["use_cases"].get("use_cases"), list):
        raise ScanError("Invalid use-case collection.")
    for field in ("requirements", "install", "first_run", "entry_points", "expected_output", "gotchas"):
        group = context["getting_started"].get(field)
        if not isinstance(group, dict) or not isinstance(group.get("items"), list):
            raise ScanError(f"Invalid getting-started group: {field}.")
    imports = model["relationships"].get("imports")
    graph = model["developer"].get("import_graph")
    if (not isinstance(imports, list) or not isinstance(graph, dict) or
            any(not isinstance(edge, dict) or not isinstance(edge.get("id"), str) for edge in imports) or
            graph.get("edge_ids") != [edge["id"] for edge in imports]):
        raise ScanError("Invalid import graph references.")
    paths = {item["path"] for item in snapshot["files"]}
    records = model["evidence"]
    for identifier, record in records.items():
        if (not isinstance(record, dict) or set(record) != set(EvidenceRecord.__annotations__)
                or record["id"] != identifier or record["snapshot_id"] != snapshot["id"]
                or record["type"] not in EVIDENCE_TYPES or record["path"] not in paths
                or type(record["line"]) is not int or type(record["end_line"]) is not int
                or not 1 <= record["line"] <= record["end_line"]
                or not isinstance(record["excerpt"], str)
                or len(record["excerpt"].split("\n")) != record["end_line"] - record["line"] + 1
                or not isinstance(record["scope"], dict) or not isinstance(record["limitations"], list)
                or record["url"] != source_url(snapshot["commit"], record["path"], record["line"], record["end_line"])):
            raise ScanError(f"Invalid knowledge evidence: {identifier}.")

    def references(node):
        if isinstance(node, dict):
            if "evidence_ids" in node:
                ids = node["evidence_ids"]
                if not isinstance(ids, list) or any(not isinstance(value, str) or value not in records for value in ids):
                    raise ScanError("Knowledge references missing evidence.")
            for item in node.values():
                references(item)
        elif isinstance(node, list):
            for item in node:
                references(item)

    for section in ("context", "relationships", "developer"):
        references(model[section])


def file_scope(path: str) -> dict:
    parts = PurePosixPath(path).parts
    for index, part in enumerate(parts[:-1]):
        kind = {"examples": "example", "example": "example", "demos": "example",
                "tests": "test", "test": "test"}.get(part.lower())
        if kind:
            end = min(index + 2, len(parts) - 1)
            return {"kind": kind, "path": "/".join(parts[:end])}
    return {"kind": "repository", "path": "."}


def build_knowledge(snapshot: Snapshot, exports: dict, facts: dict) -> Knowledge:
    records: dict[str, EvidenceRecord] = {}
    limitations = [
        "Analysis is limited to scanned files and supported readers.",
        "Import relationships are static. Playback is a navigation aid.",
        "Interpretations receive vocabulary and citation checks, not semantic verification.",
    ]
    status = snapshot.identity["working_tree"]
    if status != "clean":
        limitations.append(f"Working tree status: {status}. Source links are unpinned.")
    if snapshot.identity["cache"]["remote_freshness"] == "not_checked":
        limitations.append("Remote freshness was not checked; inspect the recorded commit.")
    if facts.get("diagnostics"):
        limitations.append("Some source files or configurations could not be fully analyzed.")
    if facts.get("unresolved_imports"):
        limitations.append("Some imports could not be resolved to repository files.")
    if facts.get("history", {}).get("status") in {"limited", "unavailable"}:
        limitations.append("Git history has limited coverage or was unavailable.")

    def add(identifier, kind, path, start, end, excerpt, scope, notes):
        records[identifier] = {
            "id": identifier, "type": kind, "snapshot_id": snapshot.identity["id"],
            "path": path, "line": start, "end_line": end, "excerpt": excerpt,
            "url": source_url(snapshot.inventory["commit"], path, start, end),
            "scope": scope, "limitations": notes,
        }

    def add_line(identifier, kind, path, line, scope, notes) -> list[str]:
        if type(line) is not int or line < 1:
            return []
        try:
            lines = snapshot.lines(path)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return []
        if line > len(lines):
            return []
        add(identifier, kind, path, line, line, lines[line - 1], scope, notes)
        return [identifier]

    context = {}
    for name, key in CONTEXT_FILES.items():
        data = exports[name]
        context[key] = {field: value for field, value in data.items() if field not in {"repo", "commit", "evidence"}}
        for item in data["evidence"]:
            path = item["source"]
            scope = file_scope(path)
            kind = ("configuration" if path in snapshot.identity["manifests"] else
                    "example" if scope["kind"] == "example" else
                    "documentation" if path in snapshot.identity["documentation"] else "source_code")
            add(item["id"], kind, path, item["line"], item["end_line"], item["text"], scope,
                ["Documented content or a source excerpt; this does not establish runtime behavior."])

    imports = []
    for edge in facts["edges"]:
        refs = add_line(edge["id"], "import_relationship", edge["from"], edge["line"],
                        file_scope(edge["from"]), ["Static import resolution; execution order is unknown."])
        imports.append({**edge, "evidence_ids": refs})
    hooks = []
    for index, hook in enumerate(facts.get("overview", {}).get("hooks", []), 1):
        citation = hook["evidence"]
        refs = add_line(f"config:{index:04d}", "configuration", citation["path"], citation["line"],
                        file_scope(citation["path"]), ["Declared hook; installation and execution were not observed."])
        hooks.append({**hook, "evidence_ids": refs})
    entries = []
    for index, entry in enumerate(facts["entry_points"], 1):
        citation = entry["evidence"]
        refs = add_line(f"entry:{index:04d}", "source_code" if "key" not in citation else "configuration",
                        citation["path"], citation.get("line"), entry["scope"],
                        ["Declaration applies only to the recorded scope."])
        entries.append({**entry, "evidence_ids": refs})
    inventory = snapshot.inventory
    model: Knowledge = {
        "schema_version": 1, "snapshot": snapshot.identity, "context": context,
        "relationships": {"imports": imports, "configuration": hooks, "unresolved_imports": facts["unresolved_imports"]},
        "developer": {"reading_guide": facts["reading_guide"], "entry_declarations": entries,
                      "diagnostics": facts["diagnostics"], "history": facts.get("history"),
                      "import_graph": {"relationship_type": "imports", "edge_ids": [edge["id"] for edge in imports]}},
        "metrics": {"files": len(inventory["files"]), "language_lines": inventory["languages"],
                    "resolved_imports": len(imports), "unresolved_imports": len(facts["unresolved_imports"])},
        "evidence": records, "limitations": limitations,
    }
    validate_knowledge(model)
    return model
