"""Embed a checked report and optional measured map in the offline HTML template."""

from importlib.resources import files
import hashlib
import json
from pathlib import Path
import re

from .checker import build_evidence
from .knowledge import Knowledge, validate_knowledge
from .scanner import ScanError, source_root

MARKER = "__REPOLENS_DATA__"
MAP_LIMIT = 16


def page_map(report: dict, facts: dict | None) -> list[dict]:
    guide = report.get("reading_guide") or {}
    flow = guide.get("flow") or {}
    path = flow.get("files", [])
    path_edges = [
        {"id": identifier, "from": source, "to": target}
        for identifier, source, target in zip(flow.get("edge_ids", []), path, path[1:])
    ]
    if facts is None:
        return path_edges
    measured = {edge["id"]: edge for edge in facts["edges"]}
    for edge in path_edges:
        actual = measured.get(edge["id"], {})
        if (actual.get("from"), actual.get("to")) != (edge["from"], edge["to"]):
            raise ScanError("The reading guide path does not match the supplied facts.")
    included = set(path)
    included.update(item["path"] for item in guide.get("recommendations", []))
    edges = dict.fromkeys(edge["id"] for edge in path_edges)
    connections = {(edge["from"], edge["to"]) for edge in path_edges}
    candidates = [edge for edge in measured.values() if edge["from"] != edge["to"]]
    if not included and candidates:
        included.add(candidates[0]["from"])
    for _ in range(MAP_LIMIT):
        previous = len(edges)
        for edge in candidates:
            if len(edges) >= MAP_LIMIT:
                break
            connection = (edge["from"], edge["to"])
            if connection in connections:
                continue
            endpoints = set(connection)
            if endpoints & included and len(included | endpoints) <= MAP_LIMIT:
                included.update(endpoints)
                edges[edge["id"]] = None
                connections.add(connection)
        if len(edges) in (previous, MAP_LIMIT):
            break
    return [measured[identifier] for identifier in edges]


def write_page(report_path: Path, output: Path, cache: Path, facts_path: Path | None = None) -> None:
    if output.resolve() in {path.resolve() for path in (report_path, facts_path) if path is not None}:
        raise ScanError("Choose an output path different from the input JSON files.")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path else None
    except ValueError as error:
        raise ScanError(f"Invalid page input: {error}") from error
    render_page(report, output, cache, facts)


def render_page(report: dict, output: Path, cache: Path, facts: dict | None = None, *,
                knowledge: Knowledge | None = None, story: dict | None = None) -> None:
    try:
        if not isinstance(report, dict) or not {"repo", "commit", "claims"} <= report.keys():
            raise ValueError("expected a checked RepoLens report")
        evidence = {
            item["id"]: item for claim in report["claims"] for item in claim["evidence"]
            if "id" in item
        }
        if facts is not None:
            if (facts["repo"], facts["source"], facts["commit"]["sha"]) != (
                report["repo"], report["source"], report["commit"]["sha"]
            ):
                raise ValueError("report and facts must refer to the same repo and commit")
        edges = page_map(report, facts)
        if knowledge is not None:
            validate_knowledge(knowledge)
            for edge in edges:
                item = knowledge["evidence"].get(edge["id"])
                if item and edge["id"] not in evidence:
                    evidence[edge["id"]] = {"id": item["id"], "path": item["path"], "line": item["line"],
                                            "snippet": item["excerpt"], "url": item["url"]}
        missing = [edge["id"] for edge in edges if edge["id"] not in evidence]
        if facts is not None and missing and knowledge is None:
            try:
                root = source_root(facts["source"], cache)
                measured, diagnostics = build_evidence(facts, root, edge_ids=missing)
            except (OSError, ScanError) as error:
                measured, diagnostics = {}, [{"evidence_id": "import map", "reason": str(error)}]
            evidence.update(measured)
            if diagnostics:
                report["evidence_diagnostics"] = [*report.get("evidence_diagnostics", []), *diagnostics]
        payload = {"report": report, "edges": edges, "evidence": evidence,
                   "history": (facts or {}).get("history")}
        if knowledge is not None:
            payload["knowledge"] = knowledge
        if story is not None:
            payload["story"] = story
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ScanError(f"Invalid page input: {error}") from error
    try:
        template = files("repolens").joinpath("page_template.html").read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ScanError("The offline template is missing. Run npm install and npm run build in web/.") from error
    if template.count(MARKER) != 1:
        raise ScanError("The offline template does not contain exactly one report placeholder.")
    verify_template(template)
    # Escape HTML-significant characters even though the data is in a JSON script.
    embedded = json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    output.write_text(template.replace(MARKER, embedded, 1), encoding="utf-8")


def verify_template(template: str) -> None:
    web = Path(__file__).resolve().parent.parent / "web"
    if not (web / "inline.mjs").is_file():
        return
    paths = sorted([*web.joinpath("src").rglob("*"), *(web / name for name in (
        "index.html", "inline.mjs", "package.json", "tsconfig.json", "vite.config.ts",
    ))])
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.relative_to(web).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    if re.search(r"<!-- repolens-frontend:" + digest.hexdigest() + r" -->", template) is None:
        raise ScanError("The offline template is stale. Run npm run build in web/.")
