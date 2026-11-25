"""Opt-in pinned live evaluation and independent review scoring."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

CASES = {
    "p-limit": ("sindresorhus/p-limit", "a8a6fbec4e0e866d6d779b10889bb4f5567e70eb"),
    "flask": ("pallets/flask", "49943b5a94413a530761350f04e896f76e8d620e"),
}
HOLDOUT = {"itsdangerous": ("pallets/itsdangerous", "672971d66a2ef9f85151e53283113f33d642dabd")}
VERDICTS = {"supported", "insufficient", "incorrect", "unestablished"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(directory, provider, model, no_ai, holdout=False):
    directory.mkdir(parents=True, exist_ok=False)
    # A new directory keeps the original artifacts intact for later comparison.
    status = subprocess.run(["git", "status", "--short"], check=True, capture_output=True, text=True)
    (directory / "git-status.txt").write_text(status.stdout, encoding="utf-8")
    failures = 0
    for label, (repo, commit) in {**CASES, **(HOLDOUT if holdout else {})}.items():
        artifact = directory / f"{label}.json"
        mode = ["--no-ai"] if no_ai else ["--provider", provider] + (["--model", model] if model else [])
        command = [sys.executable, "-m", "repolens", "mechanisms", "https://github.com/" + repo,
                   "--expect-commit", commit, "--max-calls", "3", "--max-output-tokens", "6600",
                   "--max-input-bytes", "150000", "--timeout", "60", "--no-revision",
                   "--out", str(artifact), "--trace-out", str(directory / f"{label}.trace.json"), *mode]
        failures += subprocess.run(command, check=False).returncode != 0
        if not artifact.exists():
            continue
        data = read(artifact)
        rows = data["artifacts"].get("verification", {}).get("steps", [])
        write(directory / f"{label}.review.json", {
            "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "commit": commit, "selection_quality": None, "selection_notes": "",
            "retrieval_relevant": None, "retrieval_reviewed": None,
            "claims": [{"id": row["step"]["id"], "verdict": None, "notes": "", "references": []} for row in rows],
        })
    return int(bool(failures))


def score(artifact, ledger):
    data, review = read(artifact), read(ledger)
    if review["artifact_sha256"] != hashlib.sha256(artifact.read_bytes()).hexdigest():
        raise ValueError("Review ledger is for a different artifact.")
    rows = {row["step"]["id"]: row for row in data["artifacts"].get("verification", {}).get("steps", [])}
    claims = review["claims"]
    if len(claims) != len(rows) or {row["id"] for row in claims} != rows.keys():
        raise ValueError("The ledger must list each emitted step exactly once.")
    if review["commit"] != data["snapshot"]["commit"]["sha"]:
        raise ValueError("Review commit does not match the artifact.")
    if review["selection_quality"] not in (None, "central", "useful_but_secondary", "poor", "unestablished"):
        raise ValueError("Invalid selection rating.")
    relevant, total = review["retrieval_relevant"], review["retrieval_reviewed"]
    if (relevant, total) != (None, None) and not (
        type(relevant) is int and type(total) is int and 0 <= relevant <= total
    ):
        raise ValueError("Invalid retrieval review counts.")
    reviewed = []
    for row in claims:
        verdict = row["verdict"]
        if verdict is None:
            continue
        if verdict not in VERDICTS or not row["notes"].strip() or not row["references"]:
            raise ValueError("A verdict requires a supported label, references and review notes.")
        reviewed.append(row)
    unsupported = [row for row in reviewed if row["verdict"] != "supported"]
    rejected = lambda item: rows[item["id"]]["disposition"] == "excluded"
    return {
        "execution": data["telemetry"]["execution"], "terminal_status": data["terminal_status"],
        "generated_steps": len(rows), "reviewed_steps": len(reviewed),
        "supported": [len(reviewed) - len(unsupported), len(reviewed)],
        "unsupported_or_unestablished": [len(unsupported), len(reviewed)],
        "excluded_among_unsupported": [sum(map(rejected, unsupported)), len(unsupported)],
        "accepted_among_unsupported": [sum(not rejected(row) for row in unsupported), len(unsupported)],
        "verdicts": {verdict: sum(row["verdict"] == verdict for row in reviewed) for verdict in sorted(VERDICTS)},
        "reviewer_gate_disagreements": sum(bool(row["deterministic_errors"]) and
                                           row["semantic"]["status"] == "supported" for row in rows.values()),
        "selection_quality": review["selection_quality"],
        "retrieval_relevance": [review["retrieval_relevant"], review["retrieval_reviewed"]],
        "attempts": [{key: value for key, value in stage.items()
                      if key in ("role", "status", "latency_ms", "usage", "provider_model")}
                     for stage in data["stages"]],
        "usage_reporting": data["telemetry"]["attempts_with_reported_usage"],
    }


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("directory", type=Path)
    execute.add_argument("--provider", choices=("gemini", "claude"), default="gemini")
    execute.add_argument("--model")
    execute.add_argument("--no-ai", action="store_true")
    execute.add_argument("--holdout", action="store_true")
    evaluate = commands.add_parser("score")
    evaluate.add_argument("artifact", type=Path)
    evaluate.add_argument("ledger", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "run":
            return run(args.directory, args.provider, args.model, args.no_ai, args.holdout)
        print(json.dumps(score(args.artifact, args.ledger), indent=2))
        return 0
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
