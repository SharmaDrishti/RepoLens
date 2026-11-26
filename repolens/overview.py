"""Find Python commands declared in supported hook configuration."""

import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess

from .checker import SHA, source_lines, source_url

HOOK_FILES = (".claude/settings.json", ".claude/settings.local.json", "hooks.snippet.json")


def hook_commands(config: dict):
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        for group in groups if isinstance(groups, list) else ():
            commands = group.get("hooks", []) if isinstance(group, dict) else []
            for item in commands if isinstance(commands, list) else ():
                if isinstance(item, dict) and item.get("type") == "command":
                    command = item.get("command")
                    if isinstance(command, str):
                        yield event, command


def configuration_overview(root: Path, files: set[str], commit: dict, *, line_reader=None) -> dict:
    root = root.resolve()
    sha = commit.get("sha") if commit.get("pinned") else None
    if sha and not SHA.fullmatch(sha):
        return {}
    result = {}
    hooks = []
    for path in (path for path in HOOK_FILES if path in files):
        try:
            lines = line_reader(path) if line_reader is not None else source_lines(root, path, sha)
            config = json.loads("\n".join(lines))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
        if not isinstance(config, dict):
            continue
        for event, command in hook_commands(config):
            try:
                args = shlex.split(command)
            except ValueError:
                continue
            if len(args) < 2 or not re.fullmatch(r"python(?:[23](?:\.\d+)?)?", PurePosixPath(args[0]).name):
                continue
            script = PurePosixPath(args[1])
            if script.suffix != ".py" or not all(re.fullmatch(r"[\w-]+", arg) for arg in args[2:]):
                continue
            matches = ([name for name in files if PurePosixPath(name).name == script.name]
                       if script.is_absolute() else [name for name in files if name == script.as_posix()])
            encoded = json.dumps(command, ensure_ascii=False)
            line_matches = [i for i, value in enumerate(lines, 1) if re.search(r'"command"\s*:\s*' + re.escape(encoded), value)]
            if len(matches) != 1 or len(line_matches) != 1:
                continue
            line = line_matches[0]
            hooks.append({
                "event": event, "script": matches[0], "arguments": args[2:],
                "template": path == "hooks.snippet.json",
                "evidence": {"path": path, "line": line, "snippet": lines[line - 1].strip()[:240],
                             "url": source_url(commit, path, line)},
            })
            if len(hooks) == 6:
                break
        if len(hooks) == 6:
            break
    if hooks:
        result["hooks"] = hooks
    return result
