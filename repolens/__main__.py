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
    page_parser = commands.add_parser("page", help="Make a standalone HTML page from a checked report")
    page_parser.add_argument("report", type=Path, help="Path to report.json")
    page_parser.add_argument("--facts", type=Path, help="Matching facts JSON for a fuller import map and history")
    page_parser.add_argument("--out", type=Path, default=Path("report.html"))
    build_parser = commands.add_parser("build", help="Scan a repo and create an offline HTML report")
    build_parser.add_argument("source", help="GitHub URL or local folder path")
    build_parser.add_argument("--out", type=Path, default=Path("report.html"))
    build_parser.add_argument("--knowledge-out", type=Path, help="Also save the versioned knowledge JSON")
    build_parser.add_argument("--story", type=Path, help="Use a prepared, source-reviewed story JSON")
    provider = build_parser.add_mutually_exclusive_group()
    provider.add_argument("--provider", choices=("claude", "gemini"), default="gemini")
    provider.add_argument("--no-ai", action="store_true", help="Create a report from measured facts without an API key")
    build_parser.add_argument("--model", help="Override the provider's model")
    build_parser.add_argument("--history", action="store_true", help="Include Git history measurements")
    context_parser = commands.add_parser("context", help="Extract purpose, use cases, and getting-started evidence")
    context_parser.add_argument("source", help="GitHub URL or local folder path")
    context_parser.add_argument("--out", type=Path, default=Path("context"), help="Directory for the three JSON files")
    structure_parser = commands.add_parser("structure", help="Inspect scoped source entities and relationships")
    structure_parser.add_argument("source", help="GitHub URL or local folder path")
    structure_parser.add_argument("--out", type=Path, default=Path("structure.json"))
    mechanism_parser = commands.add_parser("mechanisms", help="Investigate one evidence-grounded behavior")
    mechanism_parser.add_argument("source", help="GitHub URL or local checkout")
    mechanism_parser.add_argument("--out", type=Path, default=Path("mechanisms.json"))
    mechanism_parser.add_argument("--trace-out", type=Path, help="Optional local trace with role inputs and replies")
    mode = mechanism_parser.add_mutually_exclusive_group()
    mode.add_argument("--no-ai", action="store_true")
    mode.add_argument("--provider", choices=("claude", "gemini"), default="gemini")
    mechanism_parser.add_argument("--model")
    mechanism_parser.add_argument("--expect-commit", help="Require the full analyzed commit SHA")
    mechanism_parser.add_argument("--max-calls", type=int, default=5)
    mechanism_parser.add_argument("--max-output-tokens", type=int, default=11000)
    mechanism_parser.add_argument("--max-input-bytes", type=int, default=150000)
    mechanism_parser.add_argument("--timeout", type=int, default=60, help="Provider request timeout in seconds")
    mechanism_parser.add_argument("--no-revision", action="store_true")
    behavior_parser = commands.add_parser("behavior", help="Generate a source-cited behavior record")
    behavior_parser.add_argument("source", help="GitHub URL or local checkout")
    behavior_parser.add_argument("--question", required=True, help="One scoped question for the learner")
    behavior_parser.add_argument("--focus", action="append", default=[], metavar="PATH:START-END",
                                 help="Supply a pinned source range for a controlled comparison")
    behavior_parser.add_argument("--expect-commit", help="Require the full analyzed commit SHA")
    behavior_parser.add_argument("--provider", choices=("gemini", "claude", "openrouter"), default="gemini")
    behavior_parser.add_argument("--model", help="Override the provider's model")
    behavior_parser.add_argument("--out", type=Path, default=Path("behavior.json"))
    explain_parser = commands.add_parser("explain", help="Generate an interactive offline learning report")
    explain_parser.add_argument("source")
    explain_parser.add_argument("--out", type=Path, default=Path("explanation.html"))
    explain_parser.add_argument("--artifact-out", type=Path)
    explain_parser.add_argument("--provider", choices=("gemini", "claude"), default="gemini")
    explain_parser.add_argument("--model")
    explain_parser.add_argument("--expect-commit")
    explain_parser.add_argument("--max-output-tokens", type=int, default=3200)
    explain_parser.add_argument("--timeout", type=int, default=60)
    explain_parser.add_argument("--retries", type=int, choices=(0, 1), default=0)
    explain_parser.add_argument("--no-ai", action="store_true", help="Render a labeled deterministic preview")
    args = parser.parse_args()
    if args.command == "build" and args.no_ai and args.model:
        build_parser.error("--model requires an AI provider")
    if args.command == "imports" and args.history_depth is not None:
        if args.history_depth < 1:
            imports_parser.error("--history-depth must be a positive integer")
        args.history = True
    output = args.out.expanduser()
    cache = Path(gettempdir()) / "repolens-cache"

    try:
        if args.command == "behavior":
            from .behavior import generate_behavior

            record = generate_behavior(args.source, output, cache, question=args.question,
                                       expected_commit=args.expect_commit, focus=args.focus,
                                       provider=args.provider, model=args.model)
            print(f"Behavior draft for {record['project']['repo']}: {len(record['scenarios'])} scenarios · {output}")
            print("Pinned-source and state checks passed. Semantic review is pending.")
            return 0
        if args.command == "explain":
            from .explain import explain

            story = explain(args.source, output, cache, provider=args.provider, model=args.model,
                            tokens=args.max_output_tokens, timeout=args.timeout, expected_commit=args.expect_commit,
                            no_ai=args.no_ai, retries=args.retries,
                            artifact_out=args.artifact_out.expanduser() if args.artifact_out else None)
            print(f"RepoLens {story['mode']} learning report saved to {output}")
            for limitation in story["unknowns"]:
                print(f"• {limitation}")
            return 0
        if args.command == "mechanisms":
            from .mechanisms.orchestrator import Limits, run_mechanisms

            trace_out = args.trace_out.expanduser() if args.trace_out else None
            if trace_out and trace_out.resolve() == output.resolve():
                raise ScanError("Choose different output and trace paths.")
            limits = Limits(args.max_calls, args.max_output_tokens, args.max_input_bytes,
                            args.timeout, int(not args.no_revision))
            run, trace = run_mechanisms(args.source, output, cache, provider=args.provider,
                                        model=args.model, no_ai=args.no_ai, limits=limits,
                                        expected_commit=args.expect_commit)
            if trace_out:
                run["trace_path"] = str(trace_out)
            output.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
            if trace_out:
                trace_out.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
            print(f"Mechanism investigation: {run['terminal_status']} · {output}")
            if run.get("reason"):
                print(f"RepoLens: {run['reason']}", file=sys.stderr)
            return {"failed": 1, "cancelled": 130}.get(run["terminal_status"], 0)
        if args.command == "structure":
            from .structure import write_structure

            write_structure(args.source, output, cache)
            print(f"Source structure saved to {output}")
            return 0
        if args.command == "context":
            from .readers import write_context

            write_context(args.source, output, cache)
            print(f"Purpose, use cases, and getting-started files saved to {output}")
            return 0
        if args.command == "build":
            from .imports import imports_from_snapshot
            from .knowledge import build_knowledge
            from .page import render_page
            from .ranker import build_reading_guide
            from .readers import context_from_snapshot
            from .snapshot import open_snapshot
            from .writer import report_from_facts

            knowledge_out = args.knowledge_out.expanduser() if args.knowledge_out else None
            story_path = args.story.expanduser() if args.story else None
            if story_path and story_path.resolve() in (output.resolve(), knowledge_out and knowledge_out.resolve()):
                raise ScanError("Choose output paths different from the input story.")
            if knowledge_out and knowledge_out.resolve() == output.resolve():
                raise ScanError("Choose different output paths for HTML and knowledge JSON.")
            depth = DEFAULT_DEPTH if args.history else None
            snapshot = open_snapshot(args.source, output, cache)
            story = None
            if story_path:
                from .explain import load_reviewed_story

                story = load_reviewed_story(story_path, snapshot)
            facts = imports_from_snapshot(snapshot, history_depth=depth)
            facts["reading_guide"] = build_reading_guide(facts)
            exports = context_from_snapshot(snapshot)
            knowledge = build_knowledge(snapshot, exports, facts)
            purpose = exports["purpose.json"]
            statement = purpose["what_it_is"]
            if statement["text"] != "unknown" and statement["evidence_ids"]:
                record = knowledge["evidence"][statement["evidence_ids"][0]]
                facts["overview"]["description"] = {
                    "text": statement["text"], "path": record["path"], "line": record["line"],
                    "end_line": record["end_line"], "url": record["url"],
                }
            report = report_from_facts(facts, cache, args.model, None if args.no_ai or story is not None else args.provider,
                                       root=snapshot.root, line_reader=snapshot.lines)
            render_page(report, output, cache, facts, knowledge=knowledge, story=story)
            if knowledge_out:
                knowledge_out.write_text(json.dumps(knowledge, indent=2) + "\n", encoding="utf-8")
            print(f"Built {report['repo']}: {len(report['claims'])} checked claims")
            if "history" in facts:
                for diagnostic in facts["history"]["diagnostics"]:
                    print(diagnostic, file=sys.stderr)
            print(f"Offline page saved to {output}")
            return 0
        if args.command == "page":
            from .page import write_page

            facts = args.facts.expanduser() if args.facts else None
            write_page(args.report.expanduser(), output, cache, facts)
            print(f"Offline page saved to {output}")
            return 0
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
