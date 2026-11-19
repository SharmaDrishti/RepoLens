"""Validate report claims and attach evidence from the scanned source."""

from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote

from .scanner import ScanError, read_text

MAX_EVIDENCE = 40
MAX_CLAIMS = 12
SECTIONS = ("summary", "architecture", "reading_path")
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
GITHUB_ORIGIN = re.compile(
    r"(?:https?://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?"
)
EDGE_VERBS = {"import": "imports", "reexport": "re-exports from", "dynamic_import": "dynamically imports"}


def source_lines(root: Path, path: str, sha: str | None) -> list[str]:
    relative = PurePosixPath(path)
    candidate = root / relative
    if relative.is_absolute() or ".." in relative.parts or not candidate.resolve().is_relative_to(root):
        raise ValueError(f"Invalid evidence path: {path}")
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError(f"Evidence file is missing: {path}")
    data = candidate.read_bytes()
    if sha:
        blob = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", f"{sha}:{path}"],
            capture_output=True, timeout=10,
        )
        if blob.returncode or blob.stdout != data:
            raise ValueError(f"Evidence file does not match the scanned commit: {path}")
    text = read_text(data)
    if text is None:
        raise ValueError(f"Evidence file is not readable text: {path}")
    # Python and JavaScript grammars number lines by LF in the parsed bytes.
    return text.split("\n") if text else []


def candidate_evidence(facts: dict):
    guide = facts.get("reading_guide", {})
    flow = (guide.get("flow") or {}).get("edge_ids", [])
    recommendations = [
        item["evidence"]["edge_id"] for item in guide.get("recommendations", [])
        if "edge_id" in item["evidence"]
    ]
    by_id = {edge["id"]: edge for edge in facts["edges"]}
    for identifier in dict.fromkeys([*flow, *recommendations, *by_id]):
        if identifier not in by_id:
            continue
        edge = by_id[identifier]
        if edge["kind"] in EDGE_VERBS:
            text = f"{edge['from']} {EDGE_VERBS[edge['kind']]} {edge['to']}."
            yield identifier, text, edge["from"], edge["line"], edge["to"]

    for index, entry in enumerate(facts["entry_points"], 1):
        evidence = entry["evidence"]
        if entry["path"] and "line" in evidence:
            kind = entry["kind"]
            if kind == "python_main_module":
                text = f"{entry['path']} is a Python __main__.py entry point."
            elif kind == "python_main_guard":
                text = f'{entry["path"]} has a Python if __name__ == "__main__" guard.'
            else:
                continue
            yield f"entry:{index:04d}", text, evidence["path"], evidence["line"], entry["path"]


def build_evidence(facts: dict, root: Path) -> tuple[dict, list]:
    commit = facts["commit"]
    sha = commit["sha"] if commit["pinned"] else None
    if commit["pinned"] and (not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ScanError("The facts file has an invalid pinned commit SHA.")
    origin = GITHUB_ORIGIN.fullmatch(commit.get("remote_url") or "")
    evidence, diagnostics, files = {}, [], {}
    for identifier, text, path, line, target in candidate_evidence(facts):
        try:
            for name in (path, target):
                if name not in files:
                    try:
                        files[name] = source_lines(root, name, sha)
                    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                        files[name] = error
                if isinstance(files[name], Exception):
                    raise files[name]
            lines = files[path]
            if type(line) is not int or line < 1 or line > len(lines) or not lines[line - 1].strip():
                raise ValueError(f"Invalid evidence line: {path}:{line}")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            diagnostics.append({"evidence_id": identifier, "reason": str(error)})
            continue
        url = f"https://github.com/{origin[1]}/blob/{sha}/{quote(path)}#L{line}" if origin and sha else None
        evidence[identifier] = {
            "id": identifier, "fact_text": text, "path": path, "line": line,
            "snippet": lines[line - 1].strip()[:240], "url": url,
        }
        if len(evidence) == MAX_EVIDENCE:
            break
    return evidence, diagnostics


def validate_claim(claim, evidence: dict) -> str | None:
    required = {"kind", "text", "evidence_ids", "section"}
    if not isinstance(claim, dict) or set(claim) != required:
        return "Each claim must have kind, text, evidence_ids, and section."
    kind, text, ids, section = (claim[key] for key in ("kind", "text", "evidence_ids", "section"))
    if kind not in ("FACT", "INTERPRETATION") or section not in SECTIONS:
        return "Invalid claim kind or section."
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        return "Claim text must be between 1 and 600 characters."
    if not isinstance(ids, list) or not 1 <= len(ids) <= 4:
        return "Provide one to four evidence IDs."
    if any(not isinstance(item, str) or item not in evidence for item in ids):
        return "The claim references an unknown or unavailable evidence ID."
    if kind == "FACT" and (len(ids) != 1 or text != evidence[ids[0]]["fact_text"]):
        return "A FACT needs one evidence ID and must match its measured fact text exactly."
    return None


def check_draft(draft, evidence: dict) -> tuple[list, list]:
    if not isinstance(draft, dict) or set(draft) != {"claims"} or not isinstance(draft["claims"], list):
        return [], [{"reason": "Return an object containing a claims array."}]
    accepted, rejected = [], []
    for index, claim in enumerate(draft["claims"]):
        reason = "Too many claims." if index >= MAX_CLAIMS else validate_claim(claim, evidence)
        if reason:
            text = claim.get("text") if isinstance(claim, dict) else None
            rejected.append({"index": index, "reason": reason,
                             "text": text[:600] if isinstance(text, str) else None})
            if index >= MAX_CLAIMS:
                break
        else:
            accepted.append(claim)
    return accepted, rejected
