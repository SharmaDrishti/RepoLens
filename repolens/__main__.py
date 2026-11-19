"""Run the scanner from the terminal and save its JSON report."""

import argparse
import json
from pathlib import Path
import sys
from tempfile import gettempdir

from .history import DEFAULT_DEPTH
from .scanner import ScanError, scan


def main() -> int:
    parser = argparse.ArgumentParser(prog="repolens")
    commands = parser.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="Scan a GitHub repository or local folder")
    scan_parser.add_argument("source", help="GitHub URL or local folder path")
    scan_parser.add_argument("--out", type=Path, default=Path("scan.json"))
    imports_parser = commands.add_parser("imports", help="Read import connections and entry points")
    imports_parser.add_argument("source", help="GitHub URL or local folder path")
    imports_parser.add_argument("--out", type=Path, default=Path("facts.json"))
    imports_parser.add_argument("--history", action="store_true", help="Include Git history measurements")
    imports_parser.add_argument("--rank", action="store_true", help="Include a reading guide and import path")
    imports_parser.add_argument("--history-depth", type=int, help="Maximum first-parent commits to analyze (default: 200)")
    report_parser = commands.add_parser("report", help="Write and check a report from RepoLens facts")
    report_parser.add_argument("facts", type=Path, help="Path to facts.json")
    report_parser.add_argument("--out", type=Path, default=Path("report.json"))
    report_parser.add_argument("--provider", choices=("claude", "gemini"), default="claude")
    report_parser.add_argument("--model", help="Override the provider's model")
    args = parser.parse_args()
    if args.command == "imports" and args.history_depth is not None:
        if args.history_depth < 1:
            imports_parser.error("--history-depth must be a positive integer")
        args.history = True
    output = args.out.expanduser()
    cache = Path(gettempdir()) / "repolens-cache"

    try:
        if args.command == "report":
            from .writer import write_report

            report = write_report(args.facts.expanduser(), cache, args.model, provider_name=args.provider)
        elif args.command == "imports":
            from .imports import read_imports

            depth = (args.history_depth or DEFAULT_DEPTH) if args.history else None
            report = read_imports(args.source, output, cache, history_depth=depth)
            if args.rank:
                from .ranker import build_reading_guide

                report["reading_guide"] = build_reading_guide(report)
        else:
            report = scan(args.source, output, cache)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ScanError) as error:
        print(f"RepoLens: {error}", file=sys.stderr)
        return 1

    if args.command == "imports":
        print(
            f"Read {report['repo']}: {len(report['edges'])} import edges, "
            f"{len(report['unresolved_imports'])} unresolved imports, "
            f"{len(report['entry_points'])} entry points"
        )
        if "history" in report:
            history = report["history"]
            print(f"Git history: {history['status']} ({history['commits_analyzed']} commits analyzed)")
            for diagnostic in history["diagnostics"]:
                print(diagnostic, file=sys.stderr)
        if "reading_guide" in report:
            guide = report["reading_guide"]
            print(f"Reading guide: {len(guide['recommendations'])} recommended files")
    elif args.command == "report":
        print(f"Report for {report['repo']}: {len(report['claims'])} accepted claims, "
              f"{len(report['rejected_claims'])} rejected claims")
    else:
        print_scan_summary(report)
    print(f"Report saved to {output}")
    return 0


def print_scan_summary(report: dict) -> None:
    print(f"Scanned {report['repo']}: {len(report['files'])} text files")
    main_languages = [
        f"{name} ({lines:,} lines)"
        for name, lines in report["languages"].items() if lines and name != "Unknown"
    ]
    print("Main languages: " + (", ".join(main_languages[:5]) or "none detected"))


if __name__ == "__main__":
    raise SystemExit(main())
