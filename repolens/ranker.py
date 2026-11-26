"""Choose a reading order and a bounded path through verified imports."""

from collections import defaultdict

MAX_RECOMMENDATIONS = 5
MAX_FLOW_EDGES = 4


def entry_priority(entry: dict) -> tuple:
    kind = entry["kind"]
    key = entry["evidence"].get("key", "")
    if kind == "package_json" and key.split(".")[0] == "bin":
        priority = 0
    else:
        priority = {"project_script": 0, "python_main_module": 1,
                    "package_json": 2, "python_main_guard": 3}.get(kind, 4)
    return priority, entry["evidence"]["path"].count("/"), entry["path"], entry["evidence"]["path"], key


def entry_reason(entry: dict) -> str:
    kind = entry["kind"]
    key = entry["evidence"].get("key", "")
    if kind == "package_json":
        return f"package.json names this file in its {key} entry."
    if kind == "project_script":
        if entry.get("scope", {}).get("kind") == "example":
            return f"The example's pyproject.toml points to this file in {key}."
        return f"pyproject.toml points to this file in {key}."
    if kind == "python_main_module":
        return "This is a __main__.py file, a Python entry point for a package or runnable directory."
    return 'This file has an if __name__ == "__main__" block for code run as a script.'


def import_path(start: str, outgoing: dict, incoming: dict) -> list[dict]:
    visited = {start}
    steps = []
    source = start
    for _ in range(MAX_FLOW_EDGES):
        options = outgoing.get(source, {})
        targets = options.keys() - visited
        if not targets:
            break
        # Prefer a file with nearby imports to follow, then a widely imported file.
        target = min(targets, key=lambda path: (
            -len(outgoing.get(path, {}).keys() - visited - {path}),
            -len(incoming.get(path, {})),
            path,
        ))
        steps.append(options[target])
        visited.add(target)
        source = target
    return steps


def build_reading_guide(facts: dict) -> dict:
    outgoing, incoming = defaultdict(dict), defaultdict(dict)
    for edge in facts["edges"]:
        source, target = edge["from"], edge["to"]
        if source != target:
            outgoing[source].setdefault(target, edge)
            incoming[target].setdefault(source, edge)

    entries = sorted((entry for entry in facts["entry_points"] if entry["path"]), key=entry_priority)
    entry_by_path = {}
    for entry in entries:
        entry_by_path.setdefault(entry["path"], entry)
    start = entries[0]["path"] if entries else None
    steps = import_path(start, outgoing, incoming) if start else []
    flow = None
    if steps:
        flow = {
            "kind": "import_path",
            "files": [start, *(edge["to"] for edge in steps)],
            "edge_ids": [edge["id"] for edge in steps],
            "entry_evidence": entries[0]["evidence"],
            "entry_scope": entries[0].get("scope", {"kind": "unknown", "path": None}),
        }

    recommendations = {}
    if start:
        recommendations[start] = {"reason": entry_reason(entries[0]), "evidence": entries[0]["evidence"]}
    for edge in steps:
        recommendations[edge["to"]] = {
            "reason": f"Read this next to follow the import from {edge['from']}.",
            "evidence": {"edge_id": edge["id"], "path": edge["from"], "line": edge["line"]},
        }
    for path, entry in entry_by_path.items():
        recommendations.setdefault(path, {"reason": entry_reason(entry), "evidence": entry["evidence"]})

    for path in sorted(incoming, key=lambda path: (-len(incoming[path]), path)):
        if len(recommendations) >= MAX_RECOMMENDATIONS:
            break
        example = incoming[path][min(incoming[path])]
        count = len(incoming[path])
        noun = "file imports" if count == 1 else "files import"
        recommendations.setdefault(path, {
            "reason": f"{count} repo {noun} this file, including {example['from']}.",
            "evidence": {"edge_id": example["id"], "path": example["from"], "line": example["line"]},
        })

    history = facts.get("history", {})
    analyzed = history.get("commits_analyzed", 0)
    change_counts = {item["path"]: item["change_count"] for item in history.get("files", [])}
    reading_order = []
    for path, item in list(recommendations.items())[:MAX_RECOMMENDATIONS]:
        recommendation = {"path": path, **item}
        count = change_counts.get(path, 0)
        if count >= 3 and count * 4 >= analyzed:
            recommendation["history_note"] = f"Changed in {count} of {analyzed} analyzed commits."
        reading_order.append(recommendation)
    return {"recommendations": reading_order, "flow": flow}
