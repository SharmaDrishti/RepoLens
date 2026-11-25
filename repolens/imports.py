"""Read supported source files and report statically resolvable imports."""

import ast
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from typing import NamedTuple

import subprocess

from .scanner import ScanError, read_text
from .snapshot import Snapshot, open_snapshot

PYTHON_EXTENSIONS = (".py", ".pyi")
JS_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
# Keep quoted strings intact while removing JSON comments and trailing commas.
JSONC_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/')
JSONC_COMMA = re.compile(r'"(?:\\.|[^"\\])*"|,(?=\s*[}\]])')


class Import(NamedTuple):
    name: str
    line: int
    kind: str
    names: tuple[str, ...] = ()


def make_parsers() -> dict:
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_javascript
        import tree_sitter_python
        import tree_sitter_typescript
    except ImportError as error:
        raise ScanError("Install the import reader packages with python -m pip install -e '.[imports]'.") from error

    python = Parser(Language(tree_sitter_python.language()))
    javascript = Parser(Language(tree_sitter_javascript.language()))
    typescript = Parser(Language(tree_sitter_typescript.language_typescript()))
    tsx = Parser(Language(tree_sitter_typescript.language_tsx()))
    return {
        **dict.fromkeys(PYTHON_EXTENSIONS, python),
        **dict.fromkeys(JS_EXTENSIONS[:4], javascript),
        **dict.fromkeys((".ts", ".mts", ".cts"), typescript),
        ".tsx": tsx,
    }


def walk_nodes(root):
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(reversed(node.named_children))


def python_statement(node) -> list[Import]:
    try:
        statement = ast.parse(node.text.decode()).body[0]
    except (SyntaxError, IndexError):
        return [Import(node.text.decode(), node.start_point.row + 1, "unsupported_syntax")]
    line = node.start_point.row + 1
    if isinstance(statement, ast.Import):
        return [Import(alias.name, line, "import") for alias in statement.names]
    if isinstance(statement, ast.ImportFrom):
        name = "." * statement.level + (statement.module or "")
        names = tuple(alias.name for alias in statement.names)
        if not statement.module:
            return [Import(name, line, "import", (member,)) for member in names]
        return [Import(name, line, "import", names)]
    return []


def js_statement(node) -> Import | None:
    kind = {"import_statement": "import", "export_statement": "reexport"}.get(node.type)
    source = node.child_by_field_name("source") if kind else None
    if node.type == "call_expression":
        function = node.child_by_field_name("function")
        if function is not None and function.type == "identifier" and function.text == b"require":
            return Import(node.text.decode(), node.start_point.row + 1, "commonjs_require")
        if function is None or function.type != "import":
            return None
        kind = "dynamic_import"
        arguments = node.child_by_field_name("arguments")
        values = [child for child in arguments.named_children if child.type != "comment"] if arguments else []
        source = values[0] if values else None
    line = node.start_point.row + 1
    if kind == "dynamic_import" and (source is None or source.type != "string"):
        return Import(node.text.decode(), line, "nonliteral_import")
    if kind == "import" and source is None:
        return Import(node.text.decode(), line, "unsupported_syntax")
    if source is None:
        return None
    specifier = source.text.decode()[1:-1]
    if "\\" in specifier:
        return Import(specifier, line, "escaped_specifier")
    return Import(specifier, line, kind)


def main_guard(node) -> bool:
    if node.type != "if_statement" or node.parent.type != "module":
        return False
    condition = node.child_by_field_name("condition")
    if condition is None:
        return False
    try:
        value = ast.parse(condition.text.decode(), mode="eval").body
    except SyntaxError:
        return False
    if not isinstance(value, ast.Compare) or len(value.ops) != 1 or not isinstance(value.ops[0], ast.Eq):
        return False
    for left, right in ((value.left, value.comparators[0]), (value.comparators[0], value.left)):
        if isinstance(left, ast.Name) and left.id == "__name__" and isinstance(right, ast.Constant):
            return right.value == "__main__"
    return False


def normalize(path: str) -> str:
    return posixpath.normpath(path)


def python_candidates(base: str, files: set[str]) -> set[str]:
    return files.intersection(base + suffix for suffix in (".py", "/__init__.py"))


def resolve_python(path: str, item: Import, files: set[str]) -> set[str]:
    module = item.name.lstrip(".")
    level = len(item.name) - len(module)
    if level:
        parent = PurePosixPath(path).parent
        for step in range(level):
            if (parent / "__init__.py").as_posix() not in files:
                return set()
            if step < level - 1:
                parent = parent.parent
        if not module:
            # An explicit relative sibling name can correspond to a submodule.
            return python_candidates((parent / item.names[0]).as_posix(), files) if len(item.names) == 1 else set()
        return python_candidates((parent / module.replace(".", "/")).as_posix(), files)
    if module == "__future__":
        return set()
    name = module.replace(".", "/")
    return python_candidates(name, files) | python_candidates("src/" + name, files)


def parse_jsonc(text: str):
    clean = JSONC_TOKEN.sub(lambda match: match[0] if match[0].startswith('"') else " ", text)
    clean = JSONC_COMMA.sub(lambda match: "" if match[0] == "," else match[0], clean)
    return json.loads(clean)


def js_candidates(base: str, files: set[str]) -> set[str]:
    if base in files:
        return {base}
    suffix = PurePosixPath(base).suffix
    replacements = {".js": (".ts", ".tsx"), ".mjs": (".mts",), ".cjs": (".cts",), ".jsx": (".tsx",)}
    if suffix in JS_EXTENSIONS:
        return files.intersection(base[:-len(suffix)] + ext for ext in replacements.get(suffix, ()))
    return files.intersection(
        candidate for ext in JS_EXTENSIONS for candidate in (base + ext, base + "/index" + ext)
    )


def alias_candidates(name: str, config: dict, folder: PurePosixPath, files: set[str]) -> set[str]:
    base = config.get("baseUrl", ".")
    paths = config.get("paths", {})
    if not isinstance(base, str) or not isinstance(paths, dict):
        return set()
    matches = []
    for pattern, targets in paths.items():
        if pattern.count("*") > 1 or not isinstance(targets, list):
            continue
        prefix, star, suffix = pattern.partition("*")
        if star and name.startswith(prefix) and name.endswith(suffix) and len(name) >= len(prefix) + len(suffix):
            capture = name[len(prefix):len(name) - len(suffix)]
            matches.append((False, len(prefix), capture, targets))
        elif not star and name == pattern:
            matches.append((True, len(pattern), "", targets))
    if not matches:
        return set()
    priority = max(match[:2] for match in matches)
    candidates = set()
    for exact, prefix_length, capture, targets in matches:
        if (exact, prefix_length) == priority:
            for target in targets:
                if isinstance(target, str):
                    resolved = normalize((folder / base / target.replace("*", capture)).as_posix())
                    candidates.update(js_candidates(resolved, files))
    return candidates


def resolve_js(path: str, item: Import, files: set[str], configs: dict) -> set[str]:
    parent = PurePosixPath(path).parent
    if item.name.startswith(("./", "../")):
        return js_candidates(normalize((parent / item.name).as_posix()), files)
    if PurePosixPath(path).suffix not in {".ts", ".tsx", ".mts", ".cts"}:
        return set()
    for directory in (parent, *parent.parents):
        if directory in configs:
            return alias_candidates(item.name, configs[directory], directory, files)
    return set()


def read_project_file(root: Path, path: str) -> str:
    try:
        content = read_text((root / path).read_bytes())
    except OSError as error:
        raise ScanError(f"Could not read {path}: {error.strerror}") from error
    if content is None:
        raise ScanError(f"Could not read {path} as text.")
    return content


def manifest_facts(snapshot: Snapshot, files: set[str], manifests: list[str]) -> tuple[list, dict, list]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    entries, configs, diagnostics = [], {}, []
    relevant = files.intersection(manifests)
    relevant.update(path for path in files if PurePosixPath(path).name == "tsconfig.json")
    for path in sorted(relevant):
        name = PurePosixPath(path).name
        folder = PurePosixPath(path).parent
        if name not in {"package.json", "pyproject.toml", "tsconfig.json"}:
            continue
        try:
            text = "\n".join(snapshot.lines(path))
            data = tomllib.loads(text) if name == "pyproject.toml" else (
                parse_jsonc(text) if name == "tsconfig.json" else json.loads(text)
            )
            if not isinstance(data, dict):
                raise ValueError("expected an object")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostics.append({"path": path, "reason": str(error)})
            continue
        if name == "tsconfig.json":
            options = data.get("compilerOptions", {})
            configs[folder] = options if isinstance(options, dict) else {}
            if "extends" in data:
                diagnostics.append({"path": path, "reason": "Inherited tsconfig options were not read."})
        elif name == "package.json":
            targets = [("main", data.get("main"))]
            bins = data.get("bin")
            targets += [(f"bin.{key}", value) for key, value in bins.items()] if isinstance(bins, dict) else [("bin", bins)]
            for key, value in targets:
                if isinstance(value, str):
                    candidates = js_candidates(normalize((folder / value).as_posix()), files)
                    key_name = key.removeprefix("bin.") if key.startswith("bin.") else key
                    line = manifest_line(text, key_name, value)
                    entries.append({"kind": "package_json", "path": next(iter(candidates)) if len(candidates) == 1 else None,
                                    "target": value, "evidence": {"path": path, "key": key}})
                    if line:
                        entries[-1]["evidence"]["line"] = line
        else:
            project = data.get("project", {})
            scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
            for key, value in scripts.items() if isinstance(scripts, dict) else ():
                if isinstance(value, str):
                    module, separator, _ = value.partition(":")
                    candidates = set()
                    if separator and module:
                        module_path = module.replace(".", "/")
                        candidates = python_candidates((folder / module_path).as_posix(), files)
                        candidates |= python_candidates((folder / "src" / module_path).as_posix(), files)
                    entries.append({"kind": "project_script", "path": next(iter(candidates)) if len(candidates) == 1 else None,
                                    "target": value, "evidence": {"path": path, "key": f"project.scripts.{key}"}})
                    line = manifest_line(text, key, value, toml=True)
                    if line:
                        entries[-1]["evidence"]["line"] = line
    return entries, configs, diagnostics


def manifest_line(text: str, key: str, value: str, *, toml: bool = False) -> int | None:
    section = None
    matches = []
    for index, line in enumerate(text.split("\n"), 1):
        if toml:
            header = re.fullmatch(r"\s*\[([^]]+)\]\s*(?:#.*)?", line)
            if header:
                section = header[1]
            pattern = r"^\s*" + re.escape(key) + r"\s*=\s*(['\"])" + re.escape(value) + r"\1"
            match = section == "project.scripts" and re.search(pattern, line)
        else:
            match = re.search(re.escape(json.dumps(key)) + r"\s*:\s*" + re.escape(json.dumps(value)), line)
        if match:
            matches.append(index)
    return matches[0] if len(matches) == 1 else None


def read_imports(source: str, output: Path, cache: Path, *, history_depth: int | None = None) -> dict:
    return imports_from_snapshot(open_snapshot(source, output, cache), history_depth=history_depth)


def entry_scope(entry: dict) -> dict:
    evidence_path = entry["evidence"]["path"]
    paths = [PurePosixPath(evidence_path), PurePosixPath(entry["path"] or evidence_path)]
    for path in paths:
        for index, part in enumerate(path.parts[:-1]):
            kind = {"examples": "example", "example": "example", "demos": "example",
                    "tests": "test", "test": "test"}.get(part.lower())
            if kind:
                end = min(index + 2, len(path.parts) - 1)
                return {"kind": kind, "path": PurePosixPath(*path.parts[:end]).as_posix()}
    if entry["kind"] == "python_main_guard":
        return {"kind": "script", "path": entry["path"]}
    if entry["kind"] == "python_main_module":
        return {"kind": "package", "path": paths[1].parent.as_posix()}
    if entry["kind"] in {"project_script", "package_json"}:
        return {"kind": "package", "path": paths[0].parent.as_posix()}
    return {"kind": "unknown", "path": None}


def imports_from_snapshot(snapshot: Snapshot, *, history_depth: int | None = None,
                          trees: dict | None = None) -> dict:
    from .overview import configuration_overview

    parsers = make_parsers()
    root, report = snapshot.root, snapshot.inventory
    source = report["source"]
    files = {entry["path"] for entry in report["files"]}
    entry_points, configs, diagnostics = manifest_facts(snapshot, files, report["manifests"])
    edges, unresolved = [], []
    for path in sorted(files):
        suffix = PurePosixPath(path).suffix.lower()
        parser = parsers.get(suffix)
        if parser is None:
            continue
        python = suffix in PYTHON_EXTENSIONS
        try:
            tree = parser.parse("\n".join(snapshot.lines(path)).encode())
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostics.append({"path": path, "reason": str(error)})
            continue
        if tree.root_node.has_error:
            diagnostics.append({"path": path, "reason": "Tree-sitter found syntax errors."})
        if trees is not None:
            trees[path] = tree
        if PurePosixPath(path).name == "__main__.py":
            entry_points.append({"kind": "python_main_module", "path": path, "evidence": {"path": path, "line": 1}})
        for node in walk_nodes(tree.root_node):
            if node.has_error:
                continue
            if python:
                if main_guard(node):
                    entry_points.append({"kind": "python_main_guard", "path": path,
                                         "evidence": {"path": path, "line": node.start_point.row + 1}})
                if node.type not in {"import_statement", "import_from_statement", "future_import_statement"}:
                    continue
                items = python_statement(node)
            else:
                item = js_statement(node)
                items = [item] if item else []
            for item in items:
                candidates = set()
                if item.kind in {"import", "reexport", "dynamic_import"}:
                    candidates = resolve_python(path, item, files) if python else resolve_js(path, item, files, configs)
                specifier = item.name
                if python and item.name and not item.name.strip(".") and item.names:
                    specifier += item.names[0]
                record = {"from": path, "specifier": specifier, "line": item.line, "kind": item.kind}
                if len(candidates) == 1:
                    edges.append({**record, "to": next(iter(candidates))})
                else:
                    reason = "ambiguous" if candidates else "not_resolved"
                    unresolved.append({**record, "reason": reason})
    facts = {
        "repo": report["repo"], "source": source, "commit": report["commit"],
        "edges": [{"id": f"imp:{index:04d}", **edge} for index, edge in enumerate(edges, 1)],
        "entry_points": [{**entry, "scope": entry_scope(entry)} for entry in entry_points],
        "unresolved_imports": unresolved, "diagnostics": diagnostics,
        "overview": configuration_overview(root, files, report["commit"], line_reader=snapshot.lines),
    }
    if history_depth is not None:
        from .history import read_history

        local = snapshot.identity["cache"]["mode"] == "local"
        facts["history"] = read_history(root, report["commit"]["sha"], files, history_depth, not local)
    return facts
