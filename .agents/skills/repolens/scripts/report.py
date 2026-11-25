"""Collect pinned evidence and export a Codex-authored RepoLens lesson."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from repolens.artwork import artwork_ids, load_artwork, section_art_references
from repolens.behavior import ROLES
from repolens.checker import source_url
from repolens.cover import cover_references, load_cover
from repolens.explain import documented_items, read_brief
from repolens.guide import guide_references
from repolens.illustration import hero_references
from repolens.lessons import check_intro_lesson, check_lesson_menu, lesson_references
from repolens.mechanisms.evidence import RepositoryEvidence, is_test_source
from repolens.scanner import ScanError
from repolens.snapshot import open_snapshot
from repolens.visual import validate_visual

CACHE = ROOT / ".repolens-cache"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(source, folder):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "packet.json"
    snapshot = open_snapshot(source, target, CACHE)
    commit = snapshot.identity["commit"]
    if not commit["pinned"]:
        raise ScanError("Use a clean Git checkout so the lesson can cite the exact commit.")
    reader = RepositoryEvidence(snapshot)
    setup = documented_items(reader)
    evidence = read_brief(reader)
    for items in setup.values():
        for item in items:
            for ref in item["evidence_ids"]:
                evidence.setdefault(ref, reader.records[ref])
    save_json(target, {
        "project": {"repo": snapshot.identity["repo"], "source": source, "commit": commit},
        "checkout": str(snapshot.root), "files": sorted(reader.paths), "artwork_policy": "distinct",
        "context": reader.knowledge["context"], "setup": setup, "evidence": evidence,
    })
    print(f"Evidence from {commit['sha']} saved to {target}")


def selected_evidence(selections, snapshot):
    if len(selections) > 30:
        raise ScanError("Choose at most 30 evidence ranges.")
    tracked = {item["path"] for item in snapshot.inventory["files"]}
    docs = set(snapshot.identity["documentation"])
    config = set(snapshot.identity["configuration"])
    for ref, location in selections.items():
        path, first, last = (location[key] for key in ("path", "line", "end_line"))
        if path not in tracked or type(first) is not int or type(last) is not int:
            raise ScanError(f"Invalid tracked file or line range for {ref}.")
        lines = snapshot.lines(path)
        if not 1 <= first <= last <= len(lines) or last - first >= 60:
            raise ScanError(f"Use an existing range of at most 60 lines for {ref}.")
        excerpt = "\n".join(lines[first - 1:last])
        if not excerpt.strip() or len(excerpt.encode()) > 8000:
            raise ScanError(f"Choose a short, nonempty excerpt for {ref}.")
        kind = "documentation" if path in docs else "test_source" if is_test_source(path) else (
            "configuration" if path in config else "source_code"
        )
        yield ref, {"id": ref, "type": kind, "path": path, "line": first, "end_line": last,
                    "url": source_url(snapshot.identity["commit"], path, first, last), "excerpt": excerpt}


def render(folder):
    packet = read_json(folder / "packet.json")
    draft = read_json(folder / "draft.json")
    output = folder / "report.html"
    checkout = packet["checkout"]
    snapshot = open_snapshot(checkout, output, CACHE)
    if snapshot.identity["commit"]["sha"] != packet["project"]["commit"]["sha"]:
        raise ScanError("The checkout changed after evidence collection. Prepare the lesson again.")
    evidence = {**packet["evidence"], **dict(selected_evidence(draft["evidence"], snapshot))}
    indexed_claims = {item["id"]: item for item in draft["claims"]}
    if len(indexed_claims) != len(draft["claims"]):
        raise ScanError("Story claims need unique IDs.")
    setup = {**packet["setup"], **draft.get("setup", {})}
    sections = {claim["section"] for claim in indexed_claims.values()}
    behavior = draft.get("behavior")
    story = {
        "schema_version": 1, "project": packet["project"], "mode": "ai", "origin": "codex_skill",
        "claims": indexed_claims, "scenes": draft["scenes"], "setup": setup, "unknowns": draft["unknowns"],
        "checklist": {section: "covered" if section in sections else "unknown" for section in (
            "purpose", "problem", "capability", "mechanism", "application", "limitation"
        )} | {"getting started": "covered" if any(setup.values()) else "unknown", "evidence": "pinned"},
    }
    refs = {ref for claim in indexed_claims.values() for ref in claim["evidence_ids"]}
    refs.update(ref for items in setup.values() for item in items for ref in item["evidence_ids"])
    if "cover" in draft:
        story["cover"] = load_cover(folder, draft["cover"])
        refs.update(cover_references(story["cover"]))
    if "lessons" in draft:
        story["lessons"] = draft["lessons"]
        refs.update(lesson_references(story["lessons"], len(story["scenes"]), evidence))
    if "hero" in draft:
        story["hero"] = draft["hero"]
        refs.update(hero_references(story["hero"]))
    if "guide" in draft:
        story["guide"] = draft["guide"]
        refs.update(guide_references(story["guide"]))
    lessons = story.get("lessons", [])
    if "lesson_menu" in draft:
        check_lesson_menu(draft["lesson_menu"], lessons)
        story["lesson_menu"] = draft["lesson_menu"]
    if "intro_lesson" in draft:
        check_intro_lesson(draft["intro_lesson"], lessons, story.get("lesson_menu"))
        story["intro_lesson"] = draft["intro_lesson"]
    section_art = draft.get("section_art", {})
    if "section_art" in draft:
        refs.update(section_art_references(section_art, len(story["scenes"]), lessons, story["scenes"]))
        story["section_art"] = section_art
    artwork = load_artwork(folder, artwork_ids(lessons, story.get("hero"), story.get("guide"), section_art))
    if artwork:
        story["artwork"] = artwork
    policy = packet.get("artwork_policy", draft.get("artwork_policy"))
    if policy is not None:
        story["artwork_policy"] = policy
    if "visual" in draft:
        story["visual"] = draft["visual"]
        refs.update(validate_visual(story["visual"]))
        story["checklist"]["mechanism"] = "illustrated"
    if behavior:
        facts = {}
        for fact in behavior["facts"]:
            ref_ids = fact["evidence_ids"]
            if fact["id"] in facts:
                raise ScanError("Behavior facts need unique IDs.")
            facts[fact["id"]] = {"id": fact["id"], "assertion": fact["assertion"],
                                 "evidence": [{"id": ref, "role": ROLES[evidence[ref]["type"]]} for ref in ref_ids]}
            refs.update(ref_ids)
        story["behavior"] = {**behavior, "facts": facts, "project": packet["project"],
                             "semantic_review": "reviewed", "generation": {"model": "Codex"}}
        story["checklist"]["mechanism"] = "illustrated"
    story["evidence"] = {ref: evidence[ref] for ref in sorted(refs)}
    story_path = folder / "story.json"
    save_json(story_path, story)
    subprocess.run([sys.executable, "-m", "repolens", "build", checkout, "--story", str(story_path),
                    "--out", str(output)], cwd=ROOT, check=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("prepare")
    collect.add_argument("source")
    collect.add_argument("folder", type=Path)
    export = commands.add_parser("render")
    export.add_argument("folder", type=Path)
    args = cli.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.source, args.folder.resolve())
        else:
            render(args.folder.resolve())
    except (ScanError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"RepoLens skill: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
