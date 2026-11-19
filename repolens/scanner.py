"""Collect file facts from a local directory or cached GitHub checkout."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit


# File filters live together here. Folder counts represent pruned directories.
MAX_BYTES = 1_000_000
IGNORED_FOLDERS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", "vendor"}
MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif", ".bmp", ".ico",
    ".tif", ".tiff", ".heic", ".mp4", ".mov", ".webm", ".avi", ".mkv", ".mpeg",
    ".mpg", ".m4v", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".ttc",
}
LOCK_NAMES = {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "bun.lockb"}
MINIFIED = re.compile(r"\.min\.[^.]+(?:\.map)?$", re.IGNORECASE)
SKIP_REASONS = (
    "binary", "too_large", "ignored_folder", "media", "lock_file", "minified",
    "symlink", "special_file", "unreadable", "scan_output", "git_metadata",
)
MANIFEST_NAMES = {"package.json", "pyproject.toml", "setup.py", "setup.cfg", "Cargo.toml", "go.mod"}
LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".vue": "Vue",
    ".svelte": "Svelte", ".rb": "Ruby", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".swift": "Swift",
    ".c": "C", ".h": "C/C++", ".cc": "C++", ".cpp": "C++", ".hpp": "C++",
    ".cs": "C#", ".php": "PHP", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".ps1": "PowerShell", ".sql": "SQL", ".r": "R",
    ".lua": "Lua", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir",
    ".md": "Markdown", ".rst": "reStructuredText", ".txt": "Text",
    ".toml": "TOML", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".xml": "XML", ".ini": "INI",
}


class ScanError(Exception):
    """An error that can be shown directly in the terminal."""


def clone_github(source: str, cache: Path) -> Path:
    try:
        url = urlsplit(source)
        match = re.fullmatch(r"/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?", url.path)
        valid = (
            url.scheme in {"http", "https"} and url.netloc.lower() == "github.com"
            and match and not url.query and not url.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise ScanError("Use a GitHub repository URL such as https://github.com/owner/repo.")

    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    if repo in {"", ".", ".."}:
        raise ScanError("The GitHub URL needs a repository name.")
    canonical = f"https://github.com/{owner}/{repo}.git"
    key = hashlib.sha256(canonical.lower().encode()).hexdigest()
    checkout = cache / key / repo
    if checkout.is_dir():
        return checkout

    checkout.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=cache) as staging:
        candidate = Path(staging) / repo
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--", canonical, str(candidate)],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
        except FileNotFoundError:
            raise ScanError("Install Git to scan a GitHub URL.") from None
        except subprocess.TimeoutExpired:
            raise ScanError("GitHub took too long to respond. Check your connection and try again.") from None
        if result.returncode:
            error = result.stderr.lower()
            if any(word in error for word in ("resolve", "connect", "timed out", "proxy")):
                raise ScanError("Could not reach GitHub. Check your internet connection and try again.")
            if any(word in error for word in ("not found", "authentication", "username", "403", "401")):
                raise ScanError("GitHub could not open this repository. Check the URL and whether it is private.")
            raise ScanError("Git could not clone this repository.")
        try:
            candidate.rename(checkout)
        except OSError:
            if not checkout.is_dir():
                raise
    return checkout


def git_value(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (result.stdout.strip() or None) if result.returncode == 0 else None


def commit_details(root: Path) -> dict:
    sha = None
    remote_url = None
    shallow = False
    if (root / ".git").exists():
        sha = git_value(root, "rev-parse", "HEAD")
        remote_url = git_value(root, "remote", "get-url", "origin")
        shallow = git_value(root, "rev-parse", "--is-shallow-repository") == "true"
    return {
        "sha": sha,
        "short": sha[:7] if sha else None,
        "remote_url": remote_url,
        "pinned": sha is not None,
        "shallow": shallow,
    }


def file_skip_reason(path: Path, output: Path) -> str | None:
    name = path.name.lower()
    if path == output:
        return "scan_output"
    if path.is_symlink():
        return "symlink"
    if name == ".git":
        return "git_metadata"
    if not path.is_file():
        return "special_file"
    if name in LOCK_NAMES or name.endswith(".lock"):
        return "lock_file"
    if MINIFIED.search(name):
        return "minified"
    if path.suffix.lower() in MEDIA_EXTENSIONS:
        return "media"
    return None


def read_text(data: bytes) -> str | None:
    # BOMs identify UTF-16/32 without mistaking their zero bytes for binary.
    encoding = "utf-8-sig"
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encoding = "utf-32"
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    try:
        content = data.decode(encoding)
    except UnicodeDecodeError:
        return None
    if re.search(r"[\x00-\x08\x0e-\x1f\x7f]", content):
        return None
    return content


def inspect_file(path: Path, root: Path, output: Path) -> tuple[dict | None, str | None]:
    try:
        reason = file_skip_reason(path, output)
        if reason:
            return None, reason
        if path.stat().st_size > MAX_BYTES:
            return None, "too_large"
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except OSError:
        return None, "unreadable"
    if len(data) > MAX_BYTES:
        return None, "too_large"
    content = read_text(data)
    if content is None:
        return None, "binary"
    return {
        "path": path.relative_to(root).as_posix(),
        "size": len(data),
        "language": LANGUAGES.get(path.suffix.lower(), "Unknown"),
        "lines": len(content.splitlines()),
    }, None


def scan(source: str, output: Path, cache: Path) -> dict:
    local = Path(source).expanduser()
    if local.is_dir():
        root = local.resolve()
    elif "://" in source or source.lower().startswith(("github.com/", "git@")):
        root = clone_github(source, cache)
    else:
        raise ScanError(f"Folder not found: {source}")

    output = output.resolve()
    skipped = dict.fromkeys(SKIP_REASONS, 0)
    files = []
    languages = {}
    manifests = []

    def count_unreadable(_error: OSError) -> None:
        skipped["unreadable"] += 1

    for directory, folders, names in os.walk(root, onerror=count_unreadable):
        for folder in folders[:]:
            if folder.lower() in IGNORED_FOLDERS:
                skipped["ignored_folder"] += 1
            elif (Path(directory) / folder).is_symlink():
                skipped["symlink"] += 1
            else:
                continue
            folders.remove(folder)
        for name in names:
            path = Path(directory) / name
            entry, reason = inspect_file(path, root, output)
            # Even a large or unreadable manifest can be an entry-point clue.
            if name in MANIFEST_NAMES and reason in {None, "too_large", "unreadable", "binary"}:
                manifests.append(path.relative_to(root).as_posix())
            if reason:
                skipped[reason] += 1
                continue
            files.append(entry)
            language = entry["language"]
            languages[language] = languages.get(language, 0) + entry["lines"]

    if not files:
        raise ScanError("This repository is empty or has no scannable text files.")
    return {
        "repo": root.name,
        "source": source,
        "commit": commit_details(root),
        "languages": dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        "manifests": sorted(manifests),
        "files": sorted(files, key=lambda entry: entry["path"]),
        "skipped": skipped,
    }
