"""Measure file changes along the scanned commit's first-parent history."""

from collections import Counter
from datetime import datetime
from itertools import combinations
import os
from pathlib import Path
import re
import subprocess

from .scanner import ScanError

DEFAULT_DEPTH = 200
PAIR_FILE_LIMIT = 100


def run_git(root: Path, *args: str, timeout: int = 30) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ScanError(str(error)) from error
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ScanError(message or f"git {args[0]} exited with status {result.returncode}.")
    return result.stdout


def log_records(root: Path, sha: str, depth: int):
    raw = run_git(
        root, "log", "--first-parent", "--diff-merges=first-parent", "--root",
        "--no-renames", "--no-show-signature", "--no-notes", "--no-color",
        "--format=%x00%x00%H%x00%cI", "--name-only", "-z",
        f"--max-count={depth}", sha, "--",
    )
    # Git separates paths with one NUL and our commit headers with at least two.
    for record in re.split(rb"\x00{2,}", raw):
        if not record:
            continue
        commit, timestamp, *paths = record.rstrip(b"\x00").split(b"\x00")
        if paths:
            paths[0] = paths[0].removeprefix(b"\n")
        yield commit.decode(), timestamp.decode(), {os.fsdecode(path) for path in paths if path}


def shallow_boundaries(root: Path) -> set[str]:
    if run_git(root, "rev-parse", "--is-shallow-repository").strip() != b"true":
        return set()
    path = os.fsdecode(run_git(root, "rev-parse", "--git-path", "shallow").removesuffix(b"\n"))
    return set((root / path).read_text(encoding="ascii").splitlines())


def read_history(root: Path, sha: str | None, files: set[str], depth: int, allow_fetch: bool) -> dict:
    result = {
        "status": "unavailable", "sha": sha, "requested_depth": depth,
        "traversal": "first_parent",
        "commits_seen": 0, "commits_analyzed": 0, "shallow": False,
        "window_truncated": False, "shallow_boundaries_skipped": 0,
        "pair_file_limit": PAIR_FILE_LIMIT, "pair_commits_skipped": 0,
        "files": [], "pairs": [], "diagnostics": [],
    }
    if sha is None:
        result["diagnostics"].append("No Git commit is available for this folder.")
        return result

    boundaries = shallow_boundaries(root)
    if allow_fetch and boundaries and len(list(log_records(root, sha, depth + 1))) <= depth:
        try:
            # Fetch the scanned SHA so the analysis stays on that version.
            run_git(root, "fetch", "--no-tags", "--no-write-fetch-head", f"--depth={depth + 1}",
                    "origin", sha, timeout=120)
        except ScanError as error:
            result["diagnostics"].append(str(error))
        boundaries = shallow_boundaries(root)

    records = list(log_records(root, sha, depth + 1))
    result["status"] = "limited" if boundaries or len(records) > depth else "complete"
    result["shallow"] = bool(boundaries)
    result["window_truncated"] = len(records) > depth
    changes = Counter()
    pair_changes = Counter()
    pairs = Counter()
    last_changed = {}
    for commit, timestamp, paths in records[:depth]:
        result["commits_seen"] += 1
        if commit in boundaries:
            # Without its parent Git presents this snapshot as a root commit.
            result["shallow_boundaries_skipped"] += 1
            continue
        result["commits_analyzed"] += 1
        touched = sorted(files & paths)
        changes.update(touched)
        date = datetime.fromisoformat(timestamp)
        for path in touched:
            if path not in last_changed or date > last_changed[path][0]:
                last_changed[path] = (date, timestamp)
        if len(touched) > PAIR_FILE_LIMIT:
            result["pair_commits_skipped"] += 1
            continue
        pair_changes.update(touched)
        pairs.update(combinations(touched, 2))

    result["files"] = [
        {"path": path, "change_count": count, "last_changed": last_changed[path][1]}
        for path, count in sorted(changes.items(), key=lambda item: (-item[1], item[0]))
    ]
    result["pairs"] = [
        {
            "files": [left, right], "shared_commits": count,
            "strength": round(count / (pair_changes[left] + pair_changes[right] - count), 6),
        }
        for (left, right), count in sorted(pairs.items(), key=lambda item: (-item[1], item[0]))
    ]
    return result
