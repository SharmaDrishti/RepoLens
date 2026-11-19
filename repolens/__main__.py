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
    args = parser.parse_args()
    output = args.out.expanduser()
    cache = Path(gettempdir()) / "repolens-cache"

    try:
        report = scan(args.source, output, cache)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, ScanError) as error:
        print(f"RepoLens: {error}", file=sys.stderr)
        return 1

    print(f"Scanned {report['repo']}: {len(report['files'])} text files")
    main_languages = [
        f"{name} ({lines:,} lines)"
        for name, lines in report["languages"].items() if lines and name != "Unknown"
    ]
    print("Main languages: " + (", ".join(main_languages[:5]) or "none detected"))
    print(f"Report saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
