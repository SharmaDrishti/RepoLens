"""Bounded read-only evidence retrieval and mechanical assertion checks."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from ..checker import source_url
from ..knowledge import build_knowledge
from ..ranker import build_reading_guide
from ..readers import context_from_snapshot
from ..snapshot import Snapshot
from ..structure import structure_from_snapshot
from .connected import connected_relationships


def terms(text):
    return set(re.findall(r"[a-z][a-z0-9]{2,}", re.sub(r"([a-z])([A-Z])", r"\1 \2", text).lower())) - {
        "the", "and", "for", "from", "with", "when", "that", "this", "how", "does", "into", "has", "using",
    }


def condition_text(item):
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def is_test_source(path):
    file = Path(path)
    return file.suffix in {".py", ".js", ".ts"} and (
        set(file.parts[:-1]) & {"test", "tests"}
        or re.search(r"(^test(?:[_.-]|$)|[_.-](?:test|spec)$|_test$)", file.stem)
    )


class RepositoryEvidence:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot
        facts = {}
        self.structure = structure_from_snapshot(snapshot, analysis=facts)
        facts["reading_guide"] = build_reading_guide(facts)
        self.facts = facts
        self.knowledge = build_knowledge(snapshot, context_from_snapshot(snapshot), facts)
        self.records = {**self.knowledge["evidence"], **self.structure["evidence"]}
        self.entities = self.structure["entities"]
        self.relationships = {item["id"]: item for item in self.structure["relationships"]}
        self.paths = {item["path"] for item in snapshot.identity["files"]}
        self._snippets = None

    def baseline(self):
        return {"metrics": self.knowledge["metrics"], "context": self.knowledge["context"],
                "entry_declarations": self.knowledge["developer"]["entry_declarations"],
                "relationships": dict(Counter(item["type"] for item in self.relationships.values())),
                "resolutions": dict(Counter(item["resolution"] for item in self.relationships.values())),
                "entities": len(self.entities), "limitations": self.structure["limitations"],
                "diagnostics": self.structure["diagnostics"]}

    def _documents(self):
        if self._snippets is not None:
            return self._snippets
        result = []
        snapshot = self.snapshot.identity
        tests = [path for path in sorted(self.paths) if is_test_source(path)]
        files = [(kind, path) for kind, paths in (
            ("documentation", snapshot["documentation"]),
            ("configuration", snapshot["manifests"]), ("test_source", tests),
        ) for path in paths]
        for kind, path in files[:400]:
            try:
                lines = self.snapshot.lines(path)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                continue
            for start in range(0, min(len(lines), 1200), 10):
                end = min(start + 12, len(lines))
                excerpt = "\n".join(lines[start:end])
                if not excerpt.strip() or len(excerpt) > 1800:
                    continue
                loc = {"path": path, "line": start + 1, "end_line": end}
                digest = hashlib.sha256(f"{kind}:{path}:{start}".encode()).hexdigest()[:24]
                ref = "context:" + digest
                record = {"id": ref, "type": kind, "snapshot_id": snapshot["id"], "location": loc,
                          "excerpt": excerpt, "url": source_url(snapshot["commit"], path, start + 1, end)}
                result.append((terms(path + " " + excerpt), record))
        self._snippets = result
        return result

    def packet(self, query="", entry_points=(), required_refs=(), *, investigation=False, requested=()):
        anchor_query = query
        if investigation:
            query += " " + " ".join(self.records[ref]["excerpt"][:600] for ref in required_refs if ref in self.records)
        words = terms(query) - terms(self.snapshot.identity["repo"])
        words.update(word.lower() for word in re.findall(r"[a-z][a-z0-9_]{2,}", query, re.I))
        if not words:
            words = terms(" ".join(item["text"] for item in [
                self.knowledge["context"]["purpose"]["what_it_is"],
                self.knowledge["context"]["purpose"]["problem_it_solves"],
            ]))
        packet = {"evidence": {}, "entities": {}, "relationships": {}}

        def add(record):
            ref = record["id"]
            packet["evidence"][ref] = record
            self.records[ref] = record

        def entity(identifier):
            if identifier in self.entities:
                packet["entities"][identifier] = self.entities[identifier]

        for ref in required_refs:
            if ref in self.records:
                add(self.records[ref])
        if not investigation:
            for record in list(self.knowledge["evidence"].values()):
                if record["type"] != "import_relationship" and len(record["excerpt"]) <= 1800:
                    add(record)
                    if len(packet["evidence"]) >= 28:
                        break
        for identifier in entry_points:
            entity(identifier)
        ranked = sorted(self._documents(), key=lambda item: (
            -len(words & item[0]), not item[1]["location"]["path"].lower().startswith("readme"),
        ))
        counts = Counter()
        for keys, record in ranked:
            kind = record["type"]
            if not words & keys or counts[kind] >= ({"documentation": 9, "configuration": 3, "test_source": 5}[kind]):
                continue
            if not investigation and kind == "test_source":
                continue
            add(record)
            counts[kind] += 1

        def relation_score(item):
            loc = item["location"]
            subject = self.entities[item["subject"]]
            score = len(words & terms(subject["name"] + " " + (item["target_text"] or ""))) * 4
            score += len(words & terms(loc["path"]))
            score += 10 if item["subject"] in entry_points else 0
            return score - (2 if item["type"] == "imports" else 0)

        def include(item):
            refs = [self.records[ref] for ref in item["evidence_ids"]]
            if any(len(record["excerpt"]) > 1800 for record in refs):
                return False
            packet["relationships"][item["id"]] = item
            entity(item["subject"])
            entity(item["object"])
            for record in refs:
                add(record)
            return True

        if investigation:
            packet["navigation"] = {}
            connected = connected_relationships(self, anchor_query, terms(anchor_query), entry_points, requested=requested)
            if not connected:
                # A candidate may describe a behavior in prose while its cited
                # example spells the corresponding source symbol exactly.
                citations = " ".join(self.records[ref]["excerpt"][:600] for ref in required_refs
                                     if ref in self.records and self.records[ref]["type"] == "documentation")
                names = {name.lower() for name in re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", citations)}
                if names:
                    connected = connected_relationships(self, "", names, ())
            for item, depth, via in connected:
                if not include(item):
                    continue
                packet["navigation"][item["id"]] = {"depth": depth, "via": via}
                loc = item["location"]
                lines = self.snapshot.lines(loc["path"])
                start = max(1, loc["line"] - 4)
                end = min(len(lines), max(loc["end_line"] + 3, loc["line"] + 4))
                excerpt = "\n".join(lines[start - 1:end])
                if len(excerpt) <= 950 and len(packet["evidence"]) < 68:
                    ref = "window:" + hashlib.sha256(f"{loc['path']}:{start}:{end}".encode()).hexdigest()[:24]
                    add({"id": ref, "type": "source_code", "snapshot_id": self.snapshot.identity["id"],
                         "location": {**loc, "line": start, "end_line": end}, "excerpt": excerpt,
                         "url": source_url(self.snapshot.inventory["commit"], loc["path"], start, end)})
                    packet["navigation"][item["id"]]["window_id"] = ref

        ranked = sorted(self.relationships.values(), key=relation_score, reverse=True)
        per_file = Counter()
        for item in ranked:
            if relation_score(item) <= 0:
                break
            if not investigation and item["type"] != "defines":
                continue
            path = item["location"]["path"]
            if per_file[path] >= (8 if investigation else 4):
                continue
            if item["id"] in packet["relationships"] or not include(item):
                continue
            per_file[path] += 1
            if len(packet["relationships"]) >= (26 if investigation else 14):
                break
        return packet

    def check_reference(self, ref, packet):
        record = packet["evidence"].get(ref)
        if not record or record["snapshot_id"] != self.snapshot.identity["id"]:
            return "Evidence was not supplied for this snapshot."
        loc = record.get("location", record)
        start, end = loc["line"], loc["end_line"]
        if loc["path"] not in self.paths:
            return "Evidence file is outside the snapshot inventory."
        try:
            lines = self.snapshot.lines(loc["path"])
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return "Evidence source is unavailable."
        if not 1 <= start <= end <= len(lines) or "\n".join(lines[start - 1:end]) != record["excerpt"]:
            return "Evidence excerpt does not match its source range."
        return None

    def check_step(self, step, packet):
        errors = []
        refs = set(step["evidence_ids"])
        if not refs:
            errors.append("Step has no evidence.")
        for ref in sorted(refs):
            error = self.check_reference(ref, packet)
            if error:
                errors.append(f"{ref}: {error}")
        if step["after"]:
            errors.append("Execution-order claims are unsupported by the current graph.")
        if step["kind"] == "written_relationship":
            claim = packet["relationships"].get(step["relationship_id"])
            if not claim or claim["type"] in {"imports", "defines", "declares_entry", "declares_hook"}:
                errors.append("No admissible behavioral source relationship matches this ID.")
            else:
                for field in ("subject", "object"):
                    if (claim[field] or "") != step[field]:
                        errors.append(f"Relationship {field} does not match measured direction or identity.")
                if claim["type"] != step["relationship_type"]:
                    errors.append("Relationship type does not match source.")
                if (claim["scope"]["kind"], claim["scope"]["path"] or "") != (step["scope_kind"], step["scope_path"]):
                    errors.append("Relationship scope does not match source.")
                if [condition_text(item) for item in claim["conditions"]] != step["conditions"]:
                    errors.append("Conditional context was changed or omitted.")
                if refs != set(claim["evidence_ids"]):
                    errors.append("Citation is not the measured relationship evidence.")
        else:
            if any(step[key] for key in ("relationship_id", "subject", "object", "relationship_type", "scope_kind", "scope_path", "conditions")):
                errors.append("This evidence category cannot assert a typed source relationship.")
            expected = {"documented_behavior": "documentation", "test_expectation": "test_source"}.get(step["kind"])
            if expected and not any(packet["evidence"].get(ref, {}).get("type") == expected for ref in refs):
                errors.append(f"This claim requires {expected} evidence.")
        return errors
