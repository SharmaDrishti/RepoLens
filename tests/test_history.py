import os
from pathlib import Path
import subprocess

from repolens import history as history_reader
from repolens.history import read_history
from repolens.imports import read_imports


def git(repo, *args, **kwargs):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, **kwargs).strip()


def commit(repo, day, files):
    for path in files:
        (repo / path).write_text(f"# day {day}\n", encoding="utf-8")
    git(repo, "add", ".")
    date = f"2025-01-{day:02d}T12:00:00+00:00"
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-qm", f"Day {day}", "--allow-empty",
        env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})


def test_history_facts_and_depth(tmp_path):
    git(tmp_path, "init", "-q")
    commit(tmp_path, 1, ["a.py", "b.py", "\nname.py"])
    commit(tmp_path, 2, [])
    commit(tmp_path, 3, ["a.py"])
    commit(tmp_path, 4, ["a.py", "b.py"])
    sha = git(tmp_path, "rev-parse", "HEAD")

    output = tmp_path / "facts.json"
    report = read_imports(str(tmp_path), output, tmp_path / "cache", history_depth=10)
    history = report["history"]
    assert history["sha"] == sha
    assert history["status"] == "complete"
    assert history["commits_analyzed"] == 4
    assert history["files"] == [
        {"path": "a.py", "change_count": 3, "last_changed": "2025-01-04T12:00:00+00:00"},
        {"path": "b.py", "change_count": 2, "last_changed": "2025-01-04T12:00:00+00:00"},
        {"path": "\nname.py", "change_count": 1, "last_changed": "2025-01-01T12:00:00+00:00"},
    ]
    assert {"files": ["a.py", "b.py"], "shared_commits": 2, "strength": 0.666667} in history["pairs"]

    limited = read_history(tmp_path, sha, {"a.py", "b.py"}, 1, False)
    assert limited["status"] == "limited"
    assert limited["window_truncated"] is True
    assert limited["commits_analyzed"] == 1


def test_shallow_boundary_and_deepening(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    git(original, "init", "-q")
    commit(original, 1, ["a.py", "b.py"])
    commit(original, 2, ["a.py"])
    commit(original, 3, ["a.py"])
    checkout = tmp_path / "checkout"
    git(tmp_path, "clone", "-q", "--depth=1", original.as_uri(), str(checkout))
    sha = git(checkout, "rev-parse", "HEAD")

    shallow = read_history(checkout, sha, {"a.py", "b.py"}, 10, False)
    assert shallow["status"] == "limited"
    assert shallow["shallow"] is True
    assert shallow["shallow_boundaries_skipped"] == 1
    assert shallow["files"] == []

    deeper = read_history(checkout, sha, {"a.py", "b.py"}, 2, True)
    assert deeper["diagnostics"] == []
    assert deeper["commits_analyzed"] == 2
    assert deeper["files"] == [
        {"path": "a.py", "change_count": 2, "last_changed": "2025-01-03T12:00:00+00:00"},
    ]
    assert git(checkout, "rev-parse", "HEAD") == sha


def test_history_without_git(tmp_path):
    result = read_history(Path(tmp_path), None, {"main.py"}, 200, False)
    assert result["status"] == "unavailable"
    assert result["files"] == []
    assert result["diagnostics"]


def test_history_normalizes_git_utc_z_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(history_reader, "shallow_boundaries", lambda root: set())
    monkeypatch.setattr(history_reader, "log_records", lambda root, sha, depth: iter([
        ("commit-a", "2025-01-02T12:00:00Z", {"a.py"}),
        ("commit-b", "2025-01-01T13:00:00+01:00", {"a.py", "b.py"}),
    ]))

    result = read_history(tmp_path, "commit-a", {"a.py", "b.py"}, 10, False)

    assert result["files"] == [
        {"path": "a.py", "change_count": 2, "last_changed": "2025-01-02T12:00:00+00:00"},
        {"path": "b.py", "change_count": 1, "last_changed": "2025-01-01T13:00:00+01:00"},
    ]
