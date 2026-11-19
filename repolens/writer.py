"""Assemble a checked report from a provider-independent draft."""

import json
from pathlib import Path

from .checker import MAX_CLAIMS, SECTIONS, build_evidence, check_draft
from .providers import PROVIDERS
from .scanner import ScanError, source_root

def assemble_report(facts: dict, root: Path, draft) -> dict:
    evidence, diagnostics = build_evidence(facts, root.resolve())
    guide = facts.get("reading_guide", {})
    claims, log = [], []
    if evidence:
        # The writer gets the verified facts and a small, sanitized structural view.
        payload = {
            "repo": facts["repo"],
            "evidence": [{"id": item["id"], "fact_text": item["fact_text"]} for item in evidence.values()],
            "import_path": (guide.get("flow") or {}).get("edge_ids", []),
        }
        retry_reasons = []
        for attempt in (1, 2):
            accepted, rejected = check_draft(draft(payload, retry_reasons), evidence)
            claims.extend(accepted)
            log.extend({**item, "attempt": attempt} for item in rejected)
            if not rejected:
                break
            retry_reasons = rejected

    sections = {section: [] for section in SECTIONS}
    unique = set()
    accepted_claims = []
    for claim in claims:
        fingerprint = (claim["kind"], claim["text"])
        if fingerprint in unique:
            continue
        if len(accepted_claims) == MAX_CLAIMS:
            log.append({"reason": "Report claim limit reached.", "text": claim["text"]})
            continue
        unique.add(fingerprint)
        identifier = f"claim:{len(accepted_claims) + 1:04d}"
        sections[claim["section"]].append(identifier)
        accepted_claims.append({
            **claim, "id": identifier,
            "verification": "verified" if claim["kind"] == "FACT" else "interpretation",
            "evidence": [evidence[item] for item in claim["evidence_ids"]],
        })
    return {
        "repo": facts["repo"], "source": facts["source"], "commit": facts["commit"],
        "claims": accepted_claims, "sections": sections, "reading_guide": guide,
        "rejected_claims": log, "evidence_diagnostics": diagnostics,
    }


def write_report(facts_path: Path, cache: Path, model: str | None, *, provider_name: str = "claude") -> dict:
    provider = None

    def draft(payload, reasons):
        nonlocal provider
        if provider is None:
            provider = PROVIDERS[provider_name](model)
        return provider(payload, reasons)

    try:
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        root = source_root(facts["source"], cache)
        return assemble_report(facts, root, draft)
    except (ValueError, KeyError, TypeError) as error:
        raise ScanError(f"Invalid facts file: {error}") from error
