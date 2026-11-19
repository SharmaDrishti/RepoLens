import json
from pathlib import Path
import subprocess
import sys

import pytest

from repolens.scanner import ScanError, clone_github, scan


def test_cli_writes_scan_report(tmp_path):
    repo = tmp_path / "example"
    repo.mkdir()
    (repo / "main.py").write_bytes(b"one\r\ntwo\r\n")
    (repo / "empty.js").touch()
    (repo / "notes.txt").write_bytes("A note\n".encode("utf-16"))
    output = repo / "scan.json"
    output.write_text("old report")

    result = subprocess.run(
        [sys.executable, "-m", "repolens", "scan", str(repo), "--out", str(output)],
        capture_output=True, text=True, check=True,
    )

    report = json.loads(output.read_text())
    assert set(report) == {"repo", "source", "commit", "languages", "manifests", "files", "skipped"}
    assert report["repo"] == "example"
    assert report["source"] == str(repo)
    assert report["commit"] == {
        "sha": None, "short": None, "remote_url": None, "pinned": False, "shallow": False,
    }
    assert report["manifests"] == []
    assert report["languages"] == {"Python": 2, "Text": 1, "JavaScript": 0}
    assert report["files"] == [
        {"path": "empty.js", "size": 0, "language": "JavaScript", "lines": 0},
        {"path": "main.py", "size": 10, "language": "Python", "lines": 2},
        {"path": "notes.txt", "size": 16, "language": "Text", "lines": 1},
    ]
    assert report["skipped"]["scan_output"] == 1
    assert "Python (2 lines)" in result.stdout


def test_scan_reports_git_commit_and_manifests(tmp_path):
    repo = tmp_path / "example"
    repo.mkdir()
    nested = repo / "frontend"
    nested.mkdir()
    (nested / "package.json").write_text("{}\n")
    (repo / "pyproject.toml").write_text("[project]\n")
    (repo / "unrelated.json").write_text("{}\n")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    origin = "https://github.com/example/project.git"
    git("init", "-q")
    git("remote", "add", "origin", origin)
    git("add", ".")
    git("-c", "user.name=RepoLens Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", "Add manifests")
    sha = git("rev-parse", "HEAD")
    output = tmp_path / "scan.json"
    cache = tmp_path / "cache"

    report = scan(str(repo), output, cache)
    assert report["commit"] == {
        "sha": sha, "short": sha[:7], "remote_url": origin, "pinned": True, "shallow": False,
    }
    assert report["manifests"] == ["frontend/package.json", "pyproject.toml"]

    shallow_repo = tmp_path / "shallow"
    git("clone", "-q", "--depth", "1", repo.as_uri(), str(shallow_repo))
    shallow_report = scan(str(shallow_repo), output, cache)
    assert shallow_report["commit"]["sha"] == sha
    assert shallow_report["commit"]["shallow"] is True


def test_scan_counts_skips(tmp_path):
    repo = tmp_path / "example"
    repo.mkdir()
    folders = [".git", "node_modules", ".venv", "dist", "build", "__pycache__", "vendor"]
    for name in folders:
        folder = repo / name
        folder.mkdir()
        (folder / "ignored.py").write_text("ignored\n")
    for name in ("icon.svg", "clip.mp4", "face.woff2", "uv.lock", "package-lock.json", "app.min.js"):
        (repo / name).touch()
    (repo / "binary.dat").write_bytes(b"\x00\xff")
    (repo / "large.txt").write_bytes(b"x" * 1_000_001)
    (repo / "keep.py").write_text("pass\n")
    (repo / "linked.py").symlink_to(repo / "keep.py")

    report = scan(str(repo), tmp_path / "scan.json", tmp_path / "cache")

    assert [entry["path"] for entry in report["files"]] == ["keep.py"]
    assert {reason: count for reason, count in report["skipped"].items() if count} == {
        "ignored_folder": len(folders), "media": 3, "lock_file": 2,
        "minified": 1, "binary": 1, "too_large": 1, "symlink": 1,
    }


def test_clone_reuses_checkout(tmp_path, monkeypatch):
    calls = []

    def fake_git(command, **kwargs):
        calls.append(command)
        Path(command[-1]).mkdir()
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_git)
    url = "https://github.com/example/project"
    checkout = clone_github(url, tmp_path / "cache")
    assert clone_github(url + ".git", tmp_path / "cache") == checkout
    assert checkout.is_dir()
    assert len(calls) == 1
    assert calls[0][:4] == ["git", "clone", "--depth", "1"]


def test_friendly_errors(tmp_path):
    with pytest.raises(ScanError, match="GitHub repository URL"):
        scan("https://example.com/owner/repo", tmp_path / "scan.json", tmp_path / "cache")
    with pytest.raises(ScanError, match="empty"):
        scan(str(tmp_path), tmp_path / "scan.json", tmp_path / "cache")
