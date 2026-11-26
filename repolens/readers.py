"""Collect purpose, use cases, and getting-started facts without running repo code."""

import json
from pathlib import Path
import re
import subprocess

from .checker import SHA
from .reader_language import plain_is_grounded, purpose_plain
from .reader_sources import (
    DOC_TYPES, READMES, Passage, english_status, exact_passage, ordered_docs, passages,
    validate_excerpt,
)
from .scanner import ScanError
from .snapshot import Snapshot, open_snapshot

INSTALL = re.compile(r"^(?:(?:python[\d.]* -m )?pip[3]? install|(?:npm|pnpm|uv|brew|cargo|go|gem) (?:install|add)|yarn add|\./install\.sh)\b")
RUN = re.compile(r"^(?:python[\d.]* |node |npx |[\w-]+ (?:--app |run\b|start\b)|[./][\w.-]+)")
CODE = {"python", "py", "js", "javascript", "typescript", "ts", "jsx", "tsx"}
AUDIENCE = re.compile(r"\b(?:developers?|maintainers?|researchers?|designers?|data scientists?|students?|beginners?|programmers?)\b", re.I)
IDENTITY = re.compile(
    r"\b(?:is (?:an?|the) |convert |for (?:creating|building|running) |framework|toolkit|cli tool|"
    r"data pipeline|library|this (?:example|project) shows how)\b", re.I,
)
PROBLEM = re.compile(r"\b(?:created (?:to|since)|designed to|aims to|makes? it (?:easier|easy)|solves?|avoids?)\b", re.I)
USAGE = re.compile(r"\b(?:for creating|for building|accepts .+ returns)\b", re.I)
GOTCHA = re.compile(r"\b(?:make sure .*\bnot\b|do not|if another program|warning|known limitations)\b", re.I)
CASE_WORDING = (
    ("nesting of commands", "Group related commands"),
    ("automatic help page generation", "Make help screens automatically"),
    ("lazy loading of subcommands", "Load smaller commands only when needed"),
    ("create a small but complete application", "Build a small complete app"),
    ("returns the message", "Show a message in the browser"),
    ("adding custom management commands", "Add commands for managing your project"),
    ("forms to submit tasks", "Use forms to submit tasks"),
    ("process an iterable of inputs with limited concurrency", "Limit how many tasks run at a time"),
    ("processing inputs that arrive in batches", "Process inputs in batches"),
    ("fires the push straight to telegram", "Send notifications to Telegram"),
)
CATEGORIES = (
    ("web framework", r"\bweb (?:application )?framework\b|\bframework for building .{0,30}web applications\b"),
    ("data pipeline", r"\bdata pipeline\b|\betl (?:tool|framework)\b"),
    ("ml", r"\bmachine learning (?:tool|library|framework)\b"),
    ("game", r"\bis (?:an? )?(?:[\w-]+ ){0,3}game\b"),
    ("devops", r"\bdevops (?:tool|platform)\b"),
    ("cli tool", r"\bis (?:an? )?(?:(?:small|simple|fast) )?(?:cli|command.line) (?:tool|utility|application)\b"),
    ("library", r"\b(?:python package|javascript library|library|toolkit)\b"),
    ("other", r"\bconvert\b.+\bpaths\b"),
)


class Evidence:
    def __init__(self, prefix: str, repo: str, commit: dict):
        self.prefix = prefix
        self.repo = repo
        self.commit = commit
        self.by_passage = {}

    def ids(self, parts: list[Passage]) -> list[str]:
        identifiers = []
        for part in parts:
            key = (part.path, part.line, part.raw)
            if key not in self.by_passage:
                identifier = f"{self.prefix}:{len(self.by_passage) + 1:03d}"
                self.by_passage[key] = part.evidence(identifier, self.commit)
            identifiers.append(self.by_passage[key]["id"])
        return identifiers

    def shape(self, fields: dict) -> dict:
        return {"repo": self.repo, "commit": self.commit, **fields, "evidence": list(self.by_passage.values())}


def interpretation(text: str, parts: list[Passage], evidence: Evidence) -> dict | None:
    if plain_is_grounded(text, [part.text for part in parts]):
        return {"kind": "INTERPRETATION", "text": text, "evidence_ids": evidence.ids(parts)}
    return None


def statement(parts: list[Passage], evidence: Evidence, plain: str | None = None) -> dict:
    if not parts:
        return {"text": "unknown", "evidence_ids": [], "plain": None}
    return {
        "text": parts[0].text, "evidence_ids": evidence.ids(parts),
        "plain": interpretation(plain or purpose_plain(parts[0].text), parts, evidence),
    }


def group(items: list[dict], missing: str = "unknown") -> dict:
    return {"status": "known" if items else missing, "items": items}


def classify(text: str) -> str | None:
    return next((kind for kind, pattern in CATEGORIES if re.search(pattern, text, re.I)), None)


def first_prose(parts: list[Passage], pattern) -> Passage | None:
    return next((p for p in parts if p.language is None and 20 <= len(p.text) <= 700 and pattern.search(p.text)), None)


def read_purpose(prose: list[Passage], manifests: dict, readmes: list[dict], evidence: Evidence) -> dict:
    lead = re.compile(r"\b(?:watches?|runs?|tracks?|provides?|sends?|combines?)\b", re.I)
    intro = []
    readme_paths = {item["source"] for item in readmes if item["status"] == "supported"}
    finished = set()
    for part in prose:
        if part.path not in readme_paths or part.path in finished:
            continue
        if part.language is not None or part.line > 45:
            finished.add(part.path)
            continue
        if not part.text.startswith(("-", "*", "+")) and (IDENTITY.search(part.text) or lead.search(part.text)):
            intro.append(part)
    identity = first_prose(intro, re.compile(r".")) or next(
        (part for part in manifests.get("description", []) if len(part.text) >= 15), None
    ) or first_prose(prose, IDENTITY)
    categories = {}
    for part in [item for item in (identity, *manifests.get("description", [])) if item]:
        value = classify(part.text)
        if value:
            categories.setdefault(value, part)
    # A framework or toolkit can also be described as a library.
    if len(categories) > 1 and "library" in categories:
        categories.pop("library")
    if len(categories) > 1 and "other" in categories:
        categories.pop("other")
    conflict = len(categories) > 1
    scope = [part for part in prose if part.language is None and len(part.text) <= 700]
    audience = first_prose(scope, re.compile(r"\b(?:developers?|programmers?|researchers?|students?|beginners?)\b", re.I))
    problem = first_prose(scope, PROBLEM)
    terms = []
    if identity:
        for term in ("WSGI", "web application framework", "command line interface", "backslash", "ETL"):
            if term.lower() in identity.text.lower():
                plain = {
                    "web application framework": "Tool for building websites.",
                    "command line interface": "Programs people run by typing commands.",
                }.get(term)
                terms.append({"text": term, "evidence_ids": evidence.ids([identity]),
                              "plain": interpretation(plain, [identity], evidence) if plain else None})
    category, category_part = next(iter(categories.items()), ("unknown", None))
    what = statement([identity] if identity else [], evidence)
    if conflict:
        what = {"text": "unknown", "evidence_ids": evidence.ids(list(categories.values())), "plain": None}
    roles = []
    if identity and "with as little code as necessary" in identity.text.lower():
        roles.append({"text": identity.text, "evidence_ids": evidence.ids([identity]),
                      "plain": interpretation("People who write code.", [identity], evidence)})
    elif audience:
        role = AUDIENCE.search(audience.text)[0]
        wording = "People who write code." if role.lower().startswith("developer") else role.capitalize()
        roles.append({"text": role, "evidence_ids": evidence.ids([audience]),
                      "plain": interpretation(wording, [audience], evidence)})
    problem_plain = None
    if problem and "scale up to complex applications" in problem.text:
        problem_plain = "It is designed to make it easy to get started and build more complex websites later."
    if problem and "writing command line tools quick and fun" in problem.text:
        problem_plain = "It aims to make writing programs people run by typing commands quicker."
    return evidence.shape({
        "what_it_is": what,
        "category": {"value": "unknown" if conflict else category,
                     "evidence_ids": evidence.ids(list(categories.values())),
                     "plain": interpretation(purpose_plain(category_part.text), [category_part], evidence)
                     if category_part and not conflict else None},
        "who_uses_it": group(roles),
        "problem_it_solves": statement([problem] if problem else [], evidence, problem_plain),
        "key_terms": group(terms),
        "readmes": readmes,
        "conflicts": [{"field": "category", "evidence_ids": evidence.ids(list(categories.values()))}] if conflict else [],
    })


def read_use_cases(prose: list[Passage], evidence: Evidence) -> dict:
    outputs = []
    seen = set()
    candidates = []
    for part in prose:
        if part.language is not None or not 25 <= len(part.text) <= 700:
            continue
        scenario = part.text.lstrip("-* ").strip()
        wording = next((wording for term, wording in CASE_WORDING if term in scenario.lower()), None)
        if wording or (len(scenario) <= 250 and USAGE.search(scenario)):
            candidates.append((part, scenario, wording))
    for part, scenario, wording in sorted(candidates, key=lambda item: item[2] is None):
        if wording is None and len(outputs) >= 3:
            break
        title = " ".join(re.split(r"[:.!?]", scenario, maxsplit=1)[0].split()[:9])
        if not title:
            continue
        plain_title = wording or purpose_plain(scenario)
        plain_scenario = (wording + ".") if wording else purpose_plain(scenario)
        title_check = interpretation(plain_title, [part], evidence)
        scenario_check = interpretation(plain_scenario, [part], evidence)
        if not title_check or not scenario_check or plain_title.casefold() in seen:
            continue
        seen.add(plain_title.casefold())
        role = AUDIENCE.search(scenario)
        outputs.append({
            "id": f"use-case:{len(outputs) + 1:03d}", "kind": "INTERPRETATION",
            "title": title, "who": role[0] if role else "unknown", "scenario": scenario,
            "evidence_ids": evidence.ids([part]),
            "plain": {"kind": "INTERPRETATION", "title": title_check["text"],
                      "who": role[0].lower() if role else "unknown", "scenario": scenario_check["text"],
                      "evidence_ids": evidence.ids([part])},
        })
        if len(outputs) == 4:
            break
    return evidence.shape({"status": "known" if outputs else "unknown", "use_cases": outputs})


def manifest_passages(path: str, lines: list[str]) -> dict:
    result = {"description": [], "requirements": [], "entry_points": []}
    if path == "pyproject.toml":
        section = ""
        for index, line in enumerate(lines):
            header = re.fullmatch(r"\s*\[([^]]+)\]\s*", line)
            if header:
                section = header[1]
            key = re.match(r'\s*([\w-]+)\s*=\s*(["\'])(.*?)\2\s*(?:#.*)?$', line)
            if not key:
                continue
            field = {"description": "description", "requires-python": "requirements"}.get(key[1]) if section == "project" else (
                "entry_points" if section == "project.scripts" else None
            )
            if field:
                raw = exact_passage(path, lines, index)
                text = key[3] if field == "description" else line.strip()
                result[field].append(Passage(path, raw.line, raw.raw, text))
                if field == "requirements":
                    result[field][-1] = Passage(path, raw.line, raw.raw, "Python " + key[3])
    else:
        try:
            data = json.loads("\n".join(lines))
        except ValueError:
            return result
        if not isinstance(data, dict):
            return result
        values = [("description", "description", data.get("description"))]
        engines = data.get("engines")
        if isinstance(engines, dict):
            values.extend(("requirements", key, value) for key, value in engines.items())
        bins = data.get("bin")
        if isinstance(bins, dict):
            values.extend(("entry_points", key, value) for key, value in bins.items())
        elif isinstance(bins, str):
            values.append(("entry_points", "bin", bins))
        for field, key, value in values:
            if not isinstance(value, str):
                continue
            pattern = re.compile(re.escape(json.dumps(key)) + r"\s*:\s*" + re.escape(json.dumps(value)))
            matches = [i for i, line in enumerate(lines) if pattern.search(line)]
            if len(matches) == 1:
                raw = exact_passage(path, lines, matches[0])
                text = value if field == "description" else key + " " + value
                result[field].append(Passage(path, raw.line, raw.raw, text))
    return result


def setup_item(kind: str, part: Passage, evidence: Evidence, text: str | None = None) -> dict:
    value = part.text if text is None else text
    # Literal commands and examples keep their exact contents. They need no rewrite.
    plain = None if kind in {"command", "entry_declaration", "code_example", "expected_output"} else (
        interpretation(purpose_plain(value), [part], evidence)
    )
    return {"kind": kind, "text": value, "evidence_ids": evidence.ids([part]), "plain": plain,
            "source_section": part.section or None}


def command_blocks(part: Passage):
    """Split prompt-led commands from output without changing command arguments."""
    lines = part.raw
    index = 0
    while index < len(lines):
        line = lines[index].lstrip()
        prompted = line.startswith("$ ")
        value = line[2:] if prompted else line
        if not (INSTALL.match(value) or RUN.match(value)) or (not prompted and any(x.startswith("$ ") for x in (s.lstrip() for s in lines))):
            index += 1
            continue
        start = index
        command = [value]
        while command[-1].rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            command.append(lines[index])
        command_part = Passage(part.path, part.line + start, lines[start:index + 1], "\n".join(command), part.section)
        output = None
        if prompted and index + 1 < len(lines) and not lines[index + 1].lstrip().startswith("$ "):
            end = index + 1
            while end < len(lines) and not lines[end].lstrip().startswith("$ "):
                end += 1
            raw = lines[index + 1:end]
            if any(line.strip() for line in raw):
                output = Passage(part.path, part.line + index + 1, raw, "\n".join(raw), part.section)
            index = end - 1
        yield command_part, output
        index += 1


def read_getting_started(parts: list[Passage], manifests: dict, evidence: Evidence) -> dict:
    install, first_run, expected, gotchas = [], [], [], []
    example = None
    seen = set()
    source_for_install = None
    source_for_run = None
    for part in parts:
        section = part.section.lower()
        in_start = any(word in section for word in ("quickstart", "example", "usage", "minimal", "getting started", "install"))
        in_start |= any(word in part.path.lower() for word in ("quickstart", "installation", "getting-started"))
        if part.language in CODE and in_start and example is None and len(part.raw) <= 60:
            example = part
        if part.language is None or part.language in CODE or part.language.startswith("{") or len(part.raw) > 150:
            continue
        for command, output in command_blocks(part):
            text = command.text
            if INSTALL.match(text):
                if source_for_install is None:
                    source_for_install = part.path
                if part.path == source_for_install and text not in seen and len(install) < 4:
                    install.append(setup_item("command", command, evidence))
                    seen.add(text)
            elif not first_run and in_start and " -m venv " not in text:
                first_run.append(setup_item("command", command, evidence))
                source_for_run = part.path
                if output:
                    expected.append(setup_item("expected_output", output, evidence))
    if example:
        if source_for_run is None or source_for_run == example.path:
            first_run.insert(0, setup_item("code_example", example, evidence))
    example_source = source_for_run or (example.path if example else None)
    for part in parts:
        if (part.path == example_source and part.language is None and len(part.raw) <= 6
                and GOTCHA.search(part.text) and len(gotchas) < 3):
            gotchas.append(setup_item("note", part, evidence))

    requirements = manifests.get("requirements", [])
    python_versions = {}
    for part in requirements:
        version = re.fullmatch(r"Python\s*>=\s*(\d+(?:\.\d+)+)", part.text)
        if version:
            python_versions[version[1]] = part
    for part in parts:
        if part.language is not None or "installation" not in part.path.lower():
            continue
        version = re.search(r"\bsupports Python (\d+(?:\.\d+)+) and newer\b", part.text, re.I)
        if version:
            python_versions.setdefault(version[1], part)

    conflicts = []
    requirement_group = group([setup_item("requirement", item, evidence) for item in requirements])
    if len(python_versions) == 1 and not requirements:
        requirement_group = group([setup_item("requirement", next(iter(python_versions.values())), evidence)])
    elif len(python_versions) > 1:
        ids = evidence.ids(list(python_versions.values()))
        requirement_group = {"status": "unknown", "items": [], "evidence_ids": ids}
        conflicts.append({"field": "requirements", "evidence_ids": ids})
    return evidence.shape({
        "requirements": requirement_group,
        "install": group(install, "not_documented"),
        "first_run": group(first_run, "not_documented"),
        "entry_points": group([setup_item("entry_declaration", item, evidence) for item in manifests.get("entry_points", [])]),
        "expected_output": group(expected, "not_documented"),
        "gotchas": group(gotchas, "not_documented"),
        "conflicts": conflicts,
    })


def collect_context(source: str, output: Path, cache: Path) -> dict:
    return context_from_snapshot(open_snapshot(source, output / "purpose.json", cache))


def context_from_snapshot(snapshot: Snapshot) -> dict:
    scan = snapshot.inventory
    files = {item["path"] for item in scan["files"]}
    commit = scan["commit"]
    sha = commit.get("sha") if commit.get("pinned") else None
    if commit.get("pinned") and (not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ScanError("Invalid scanned commit SHA.")
    sources = {}

    def load(path):
        if path in sources:
            return sources[path]
        try:
            sources[path] = snapshot.lines(path)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            sources[path] = []
        return sources[path]

    readmes = sorted((path for path in files if path.lower() in READMES),
                     key=lambda path: (path.lower() != "readme.md", path.lower(), path))
    readme_info = []
    readme_parts = []
    for path in readmes:
        lines = load(path)
        parts = list(passages(path, lines))
        status = english_status(parts) if lines else "unavailable"
        readme_info.append({"source": path, "status": status})
        if status == "supported":
            readme_parts.extend(parts)
    manifests = {"description": [], "requirements": [], "entry_points": []}
    for name in ("pyproject.toml", "package.json"):
        if name in files:
            for field, values in manifest_passages(name, load(name)).items():
                manifests[field].extend(values)
    docs = [part for path in ordered_docs(files) for part in passages(path, load(path))]
    example_paths = sorted(path for path in files if path.lower().startswith(("examples/", "example/"))
                           and Path(path).suffix.lower() in DOC_TYPES)
    examples = [part for path in example_paths[:30] for part in passages(path, load(path))]
    # Search committed source text for explicit CLI descriptions and named tests.
    fallback = []
    for path in sorted(files):
        lower = path.lower()
        if not lower.endswith(".py") or not ("test" in lower or "cli" in lower or "__main__" in lower):
            continue
        if len(fallback) >= 30:
            break
        lines = load(path)
        for index, line in enumerate(lines):
            if re.search(r"\bdef test_\w+|\bArgumentParser\(description\s*=", line):
                raw = exact_passage(path, lines, index)
                fallback.append(raw)
                if len(fallback) >= 30:
                    break
    results = {
        "purpose.json": read_purpose([*readme_parts, *manifests["description"], *docs, *examples, *fallback],
                                     manifests, readme_info, Evidence("pur", scan["repo"], commit)),
        "usecases.json": read_use_cases([*readme_parts, *examples, *docs, *fallback],
                                        Evidence("use", scan["repo"], commit)),
        "getstarted.json": read_getting_started([*readme_parts, *docs], manifests,
                                               Evidence("get", scan["repo"], commit)),
    }
    for result in results.values():
        for record in result["evidence"]:
            if not validate_excerpt(record, sources[record["source"]]):
                raise ScanError(f"Invalid reader evidence: {record['source']}:{record['line']}")
    return results


def write_context(source: str, output: Path, cache: Path) -> None:
    results = collect_context(source, output, cache)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in results.items():
        (output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
