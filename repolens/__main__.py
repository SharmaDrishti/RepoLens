"""Run the scanner from the terminal and save its JSON report."""

import argparse
import json
from pathlib import Path
import sys
from tempfile import gettempdir

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
    args = parser.parse_args()
    output = args.out.expanduser()
    cache = Path(gettempdir()) / "repolens-cache"

    try:
        if args.command == "imports":
            from .imports import read_imports

            report = read_imports(args.source, output, cache)
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
