"""Open a repository once and share its inventory and provenance."""

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import subprocess

from .checker import source_lines
from .scanner import read_text, scan_root, source_root


@dataclass
class Snapshot:
    root: Path
    inventory: dict
    identity: dict
    _lines: dict = field(default_factory=dict, repr=False)

    def lines(self, path: str) -> list[str]:
        if path not in self._lines:
            commit = self.inventory["commit"]
            self._lines[path] = source_lines(self.root, path, commit["sha"] if commit["pinned"] else None)
        value = self._lines[path]
        if isinstance(value, Exception):
            raise value
        return value


def git_bytes(root: Path, *args: str) -> bytes | None:
    try:
        run = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return run.stdout if run.returncode == 0 else None


def open_snapshot(source: str, output: Path, cache: Path) -> Snapshot:
    local = Path(source).expanduser().is_dir()
    cache_info = {"reused": False}
    root = source_root(source, cache, cache_info=cache_info).resolve()
    has_git = (root / ".git").exists()
    status = git_bytes(root, "status", "--porcelain=v1", "--untracked-files=all") if has_git else None
    inventory_paths = git_bytes(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard") if has_git else None
    allowed = {os.fsdecode(path) for path in inventory_paths.split(b"\0") if path} if inventory_paths is not None else None
    inventory = scan_root(root, source, output, allowed=allowed)
    commit = inventory["commit"]
    after = git_bytes(root, "status", "--porcelain=v1", "--untracked-files=all") if has_git else None
    head = git_bytes(root, "rev-parse", "HEAD") if has_git else None
    if not has_git:
        working_tree = "unversioned"
    elif status is None or after is None or head is None:
        working_tree = "unknown"
    elif status or after or head.decode().strip() != commit["sha"]:
        working_tree = "dirty"
    else:
        working_tree = "clean"
    commit["pinned"] = bool(commit["sha"] and working_tree == "clean")
    paths = [item["path"] for item in inventory["files"]]
    digest = hashlib.sha256()
    digest.update(json.dumps([source, commit["sha"], working_tree]).encode())
    captured = {}
    if not commit["pinned"]:
        for path in paths:
            digest.update(json.dumps(path).encode())
            try:
                candidate = root / path
                if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
                    raise ValueError(f"Invalid snapshot path: {path}")
                with candidate.open("rb") as stream:
                    data = stream.read(1_000_001)
                content = read_text(data)
                if content is None or len(data) > 1_000_000:
                    raise ValueError(f"File changed or is not readable text: {path}")
                captured[path] = content.split("\n") if content else []
                digest.update(hashlib.sha256(data).digest())
            except (OSError, ValueError) as error:
                captured[path] = error
                digest.update(b"unavailable")
    identity = {
        "id": "snapshot:" + digest.hexdigest(),
        "repo": inventory["repo"], "source": source, "commit": commit,
        "working_tree": working_tree, "content": "commit" if commit["pinned"] else "working_tree",
        "cache": {"mode": "local" if local else "reused" if cache_info["reused"] else "cloned",
                  "remote_freshness": "not_checked" if not local else "not_applicable"},
        "files": inventory["files"], "languages": inventory["languages"], "manifests": inventory["manifests"],
        "documentation": [path for path in paths if path.lower().startswith(("readme", "docs/", "doc/"))
                          or Path(path).suffix.lower() in {".md", ".rst"}],
        "configuration": [path for path in paths if path in inventory["manifests"]
                          or path.startswith((".claude/", ".github/", "config/"))
                          or Path(path).name in {"hooks.snippet.json", "tsconfig.json"}
                          or Path(path).suffix.lower() in {".toml", ".ini", ".cfg", ".yaml", ".yml"}],
        "skipped": inventory["skipped"],
    }
    return Snapshot(root, inventory, identity, captured)
