"""Opt-in Gemini request isolation, using synthetic evidence only."""

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from repolens.mechanisms.contracts import MECHANISM, validate
from repolens.mechanisms.orchestrator import INVESTIGATE
from repolens.providers import ProviderError, gemini_writer, without_array_bounds
from repolens.scanner import ScanError


def main():
    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("Probe blocked: GEMINI_API_KEY is not set. No requests sent.")
        return 1
    payload = {
        "candidate": {"id": "synthetic", "description": "A documented operation",
                      "evidence_ids": ["doc:1"]},
        "source": {"entities": {}, "relationships": {}, "evidence": {
            "doc:1": {"type": "documentation", "excerpt": "The operation returns the input unchanged."}}},
        "revision_requests": [],
    }
    # Keep model, prompt, evidence, MIME type, budget and timeout constant.
    system = INVESTIGATE.instructions + " For this probe, return " + json.dumps({
        "candidate_id": "synthetic", "summary": "Probe", "entities": [], "steps": [], "unknowns": [],
    })
    for label, schema in (("original_schema", MECHANISM),
                          ("no_wire_maxItems", without_array_bounds(MECHANISM)),
                          ("json_without_schema", None)):
        try:
            result = gemini_writer(None, system=system, schema=schema, max_tokens=2200, timeout=30,
                                   observe=lambda *_: None)(payload, [])
        except ProviderError as error:
            print(json.dumps({"variant": label, **error.diagnostic()}))
            if error.status == 400:
                continue
            return 1
        except ScanError:
            print(json.dumps({"variant": label, "result": "provider_configuration_error"}))
            return 1
        try:
            validate(result, MECHANISM)
        except ScanError:
            print(json.dumps({"variant": label, "result": "response_failed_full_local_validation"}))
            return 1
        print(json.dumps({"variant": label, "result": "response_passed_full_local_validation"}))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
