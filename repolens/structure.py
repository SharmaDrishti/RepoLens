"""Collect scoped source relationships without inferring execution or mechanisms."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Literal, TypedDict

from .checker import source_url
from .imports import imports_from_snapshot, walk_nodes
from .knowledge import file_scope
from .scanner import ScanError
from .snapshot import Snapshot, open_snapshot


class Location(TypedDict):
    path: str
    line: int
    end_line: int


class Entity(TypedDict):
    id: str
    kind: str
    name: str
    parent: str | None
    scope: dict
    location: Location


class Relationship(TypedDict):
    id: str
    subject: str
    object: str | None
    type: str
    target_text: str | None
    location: Location
    evidence_ids: list[str]
    scope: dict
    conditions: list[dict]
    resolution: str
    classification: str
    limitations: list[str]


class StructureEvidence(TypedDict):
    id: str
    snapshot_id: str
    type: Literal["source_code", "import_relationship", "configuration"]
    location: Location
    excerpt: str
    url: str | None


DECLARATIONS = {
    "function_definition": "function", "function_declaration": "function",
    "generator_function_declaration": "function", "method_definition": "method",
    "class_definition": "class", "class_declaration": "class",
}
CALLS = {"call", "call_expression"}
SOURCE_RELATIONSHIPS = CALLS | {"return_statement", "raise_statement", "throw_statement", "decorator"}
CONTEXT_TYPES = {
    "if_statement": "branch", "conditional_expression": "branch", "ternary_expression": "branch",
    "elif_clause": "branch", "while_statement": "loop", "for_statement": "loop",
    "for_in_statement": "loop", "do_statement": "loop", "except_clause": "exception_handler",
    "catch_clause": "exception_handler", "try_statement": "exception_region",
    "finally_clause": "finally", "case_clause": "match_arm", "switch_case": "match_arm",
    "boolean_operator": "short_circuit_expression",
}
STATIC_ONLY = "Written source relationship. Runtime execution and ordering are unknown."


def node_text(node) -> str:
    return node.text.decode("utf-8") if node is not None else ""


def declaration(node):
    kind = DECLARATIONS.get(node.type)
    name = node.child_by_field_name("name") if kind else None
    if node.type == "variable_declarator":
        value = node.child_by_field_name("value")
        if value and value.type in {"arrow_function", "function_expression", "generator_function"}:
            kind, name = "function", node.child_by_field_name("name")
    if name is None or name.type not in {"identifier", "property_identifier", "private_property_identifier"}:
        return None
    return kind, name


def source_location(path: str, node, *, end_node=None) -> Location:
    end = (end_node or node).end_point
    return {"path": path, "line": node.start_point.row + 1,
            "end_line": max(node.start_point.row + 1, end.row + (end.column != 0))}


def enclosing_context(node, owner):
    result = []
    child = node
    parent = node.parent
    while parent is not None and (owner is None or parent.id != owner.id):
        kind = CONTEXT_TYPES.get(parent.type)
        if parent.type == "binary_expression" and any(token.type in {"&&", "||", "??"} for token in parent.children):
            kind = "short_circuit_expression"
        if kind:
            field = next((parent.field_name_for_child(i) for i, candidate in enumerate(parent.children)
                          if candidate.id == child.id), None)
            condition = parent.child_by_field_name("condition")
            if kind == "loop" and parent.type in {"for_statement", "for_in_statement"}:
                condition = condition or parent.child_by_field_name("right")
            if kind == "short_circuit_expression":
                condition = parent.child_by_field_name("left")
            result.append({"kind": kind, "region": field or child.type,
                           "line": parent.start_point.row + 1, "expression": node_text(condition) or None})
        child, parent = parent, parent.parent
    return list(reversed(result))


def anchored_id(prefix: str, *parts) -> str:
    raw = json.dumps(parts, ensure_ascii=True, sort_keys=True).encode()
    return prefix + ":" + hashlib.sha256(raw).hexdigest()[:24]


class Structure:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot
        self.entities: dict[str, Entity] = {}
        self.relationships: list[Relationship] = []
        self.evidence: dict[str, StructureEvidence] = {}

    def add(self, subject, target, kind, location, *, column=0, conditions=None, target_text=None,
            resolution="resolved", classification="established_static", evidence_type="source_code",
            notes=None, relationship_id=None):
        path, line, end = (location[key] for key in ("path", "line", "end_line"))
        lines = self.snapshot.lines(path)
        if not 1 <= line <= end <= len(lines):
            return
        identifier = relationship_id or anchored_id("rel", subject, target, kind, path, line, end, column, target_text)
        evidence_id = anchored_id("src", evidence_type, path, line, end, column)
        self.evidence[evidence_id] = {
            "id": evidence_id, "snapshot_id": self.snapshot.identity["id"], "type": evidence_type,
            "location": location, "excerpt": "\n".join(lines[line-1:end]),
            "url": source_url(self.snapshot.inventory["commit"], path, line, end),
        }
        self.relationships.append({
            "id": identifier, "subject": subject, "object": target, "type": kind,
            "target_text": target_text, "location": location, "evidence_ids": [evidence_id],
            "scope": self.entities[subject]["scope"], "conditions": conditions or [],
            "resolution": resolution, "classification": classification,
            "limitations": notes or [STATIC_ONLY],
        })


def source_entities(graph: Structure, path: str, tree) -> None:
    if tree.root_node.has_error:
        # A damaged declaration can change lexical ownership for otherwise valid nodes.
        return
    nodes = list(walk_nodes(tree.root_node))
    file_id = "file:" + path
    definitions = {}
    candidate_names = set()
    ordinals = defaultdict(int)

    def owner(node):
        current = node.parent
        while current is not None and current.id not in definitions:
            current = current.parent
        return (definitions[current.id], current) if current is not None else (file_id, None)

    candidates = defaultdict(list)
    for node in nodes:
        if node.has_error or (item := declaration(node)) is None:
            continue
        kind, name_node = item
        name = node_text(name_node)
        parent_id, parent_node = owner(node)
        if parent_node is not None and graph.entities[parent_id]["kind"] == "class" and kind == "function":
            kind = "method"
        key = (parent_id, kind, name)
        ordinals[key] += 1
        identifier = anchored_id("entity", *key, ordinals[key])
        definitions[node.id] = identifier
        location = source_location(path, node, end_node=name_node)
        graph.entities[identifier] = {"id": identifier, "kind": kind, "name": name, "parent": parent_id,
                                      "scope": file_scope(path), "location": location}
        graph.add(parent_id, identifier, "defines", location, column=node.start_point.column,
                  conditions=enclosing_context(node, parent_node))
        container = node.parent
        if container is not None and container.type == "export_statement":
            container = container.parent
        if kind == "function" and container == tree.root_node:
            candidates[name].append(identifier)
            candidate_names.add(name_node.id)

    # Any other reference of the name can hide a binding, assignment, alias or re-export.
    # Resolve only unique module declarations whose occurrences are declarations or bare calls.
    blocked = set()
    for node in nodes:
        if node.type not in {"identifier", "shorthand_property_identifier", "shorthand_property_identifier_pattern"}:
            continue
        name = node_text(node)
        if name not in candidates or node.id in candidate_names:
            continue
        parent = node.parent
        if parent is not None and parent.type in CALLS and parent.child_by_field_name("function") == node:
            continue
        if parent is not None and parent.type == "attribute" and parent.child_by_field_name("attribute") == node:
            continue
        blocked.add(name)
    dynamic_names = any(
        node.type == "wildcard_import" or
        (node.type in CALLS and node_text(node.child_by_field_name("function")) in {"exec", "eval"})
        for node in nodes
    )
    for node in nodes:
        if node.type not in SOURCE_RELATIONSHIPS or node.has_error:
            continue
        parent_id, bound = owner(node)
        conditions = enclosing_context(node, bound)
        location = source_location(path, node)
        if node.type in CALLS:
            callee = node.child_by_field_name("function")
            if callee is None or callee.type == "import":
                continue
            target = node_text(callee)
            options = candidates.get(target, [])
            resolved = (callee.type == "identifier" and len(options) == 1
                        and not dynamic_names and target not in blocked)
            graph.add(parent_id, options[0] if resolved else None, "calls", location,
                      column=node.start_point.column, conditions=conditions, target_text=target,
                      resolution="static_candidate" if resolved else "unresolved",
                      classification="established_static" if resolved else "unresolved",
                      notes=([STATIC_ONLY, "Unique bare same-module candidate. Runtime binding was not observed."]
                             if resolved else [STATIC_ONLY, "Call target was not resolved."]))
        elif node.type in {"return_statement", "raise_statement", "throw_statement"}:
            graph.add(parent_id, None, "returns" if node.type == "return_statement" else "raises",
                      location, column=node.start_point.column, conditions=conditions,
                      target_text=node_text(node), resolution="source_expression")
        elif node.type == "decorator" and node.parent is not None:
            definition = definitions.get(node.parent.id) or next(
                (definitions[child.id] for child in node.parent.named_children if child.id in definitions), None,
            )
            if definition is not None:
                graph.add(definition, None, "declares_decorator", location, column=node.start_point.column,
                          target_text=node_text(node), conditions=conditions,
                          resolution="source_expression",
                          notes=["Decorator syntax is present; registration semantics are unknown."])


def structure_from_snapshot(snapshot: Snapshot, *, analysis: dict | None = None) -> dict:
    trees = {}
    facts = imports_from_snapshot(snapshot, trees=trees)
    if analysis is not None:
        analysis.update(facts)
    graph = Structure(snapshot)
    for item in snapshot.inventory["files"]:
        path = item["path"]
        identifier = "file:" + path
        graph.entities[identifier] = {
            "id": identifier, "kind": "module" if path in trees else "file", "name": path,
            "parent": None, "scope": file_scope(path),
            "location": {"path": path, "line": 1, "end_line": 1},
        }
    for path, tree in trees.items():
        source_entities(graph, path, tree)
    for edge in facts["edges"]:
        path, line = edge["from"], edge["line"]
        graph.add("file:" + path, "file:" + edge["to"], "imports",
                  {"path": path, "line": line, "end_line": line}, target_text=edge["specifier"],
                  evidence_type="import_relationship", relationship_id=edge["id"])
    for hook in facts.get("overview", {}).get("hooks", []):
        citation = hook["evidence"]
        path, line = citation["path"], citation["line"]
        identifier = anchored_id("hook", path, hook["event"], line)
        location = {"path": path, "line": line, "end_line": line}
        graph.entities[identifier] = {"id": identifier, "kind": "configuration_declaration",
                                      "name": hook["event"], "parent": "file:" + path,
                                      "scope": {"kind": "hook_template" if hook["template"] else "hook_settings",
                                                "path": path},
                                      "location": location}
        graph.add(identifier, "file:" + hook["script"], "declares_hook", location,
                  target_text=" ".join(hook["arguments"]), classification="declared_configuration",
                  resolution="matched_repository_path", evidence_type="configuration",
                  notes=["A repository file matches the declared script name. Hook matchers, installation, and execution are unverified."])
    for entry in facts["entry_points"]:
        citation = entry["evidence"]
        path, line = citation["path"], citation.get("line")
        if line is None or "key" not in citation:
            continue
        location = {"path": path, "line": line, "end_line": line}
        identifier = anchored_id("entry", path, citation["key"])
        graph.entities[identifier] = {
            "id": identifier, "kind": "configuration_declaration", "name": citation["key"],
            "parent": "file:" + path, "scope": entry["scope"], "location": location,
        }
        target = "file:" + entry["path"] if entry["path"] else None
        graph.add(identifier, target, "declares_entry", location, target_text=entry.get("target"),
                  classification="declared_configuration", evidence_type="configuration",
                  resolution="matched_repository_path" if target else "unresolved",
                  notes=["A named entry declared by this manifest within its recorded scope."])
    result = {
        "schema_version": 1, "snapshot": snapshot.identity, "entities": graph.entities,
        "relationships": graph.relationships, "evidence": graph.evidence,
        "entry_declarations": facts["entry_points"], "diagnostics": facts["diagnostics"],
        "limitations": [STATIC_ONLY, "Bare call resolution is limited to conservative same-module declarations.",
                        "Observed mechanisms, registration semantics, and execution order are outside checkpoint 2A."],
    }
    validate_structure(result)
    return result


def validate_structure(data: dict) -> None:
    """Check export integrity. Assertion verification is a separate responsibility."""
    entities, evidence = data["entities"], data["evidence"]
    seen = set()
    for relationship in data["relationships"]:
        identifier = relationship["id"]
        source = entities.get(relationship["subject"])
        target_id = relationship["object"]
        target = entities.get(target_id)
        refs = relationship["evidence_ids"]
        if (identifier in seen or source is None or (target_id is not None and target is None)
                or (relationship["type"] == "defines" and (target is None or target["parent"] != source["id"]))
                or relationship["scope"] != source["scope"] or not refs):
            raise ScanError(f"Invalid structure relationship: {identifier}")
        expected_type = {"imports": "import_relationship", "declares_hook": "configuration",
                         "declares_entry": "configuration"}.get(relationship["type"], "source_code")
        for ref in refs:
            record = evidence.get(ref)
            if (record is None or record["snapshot_id"] != data["snapshot"]["id"]
                    or record["location"] != relationship["location"] or record["type"] != expected_type):
                raise ScanError(f"Invalid structure evidence: {ref}")
        seen.add(identifier)


def write_structure(source: str, output: Path, cache: Path) -> None:
    data = structure_from_snapshot(open_snapshot(source, output, cache))
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
