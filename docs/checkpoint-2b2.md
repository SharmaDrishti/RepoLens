# Checkpoint 2B.2 — live evaluation protocol

## Scope and observations

The starting baseline was 60 Python passes, two expected failures, and
10 frontend passes. The worktree already held the 2B.1 implementation
and visual work. The runner writes Git status alongside each new batch.
This checkpoint adds instrumentation and evaluation tooling. It changes
neither evidence selection nor the semantic acceptance criteria.

| Repository | Pinned commit | Local deterministic analysis | Live replies |
| --- | --- | --- | --- |
| sindresorhus/p-limit | `a8a6fbec4e0e866d6d779b10889bb4f5567e70eb` | 59 entities, 0.170 s | 0 |
| pallets/flask | `49943b5a94413a530761350f04e896f76e8d620e` | 1,850 entities, 1.602 s | 0 |
| pallets/itsdangerous | `672971d66a2ef9f85151e53283113f33d642dabd` | 190 entities, 0.378 s | 0 |

The optional holdout was not used to develop the initial mechanism
prompts. It has appeared in earlier report-writer evaluation.
All measured times above are single local deterministic runs, not model
latency. Cache freshness was not checked. Both provider keys were absent.
All three Gemini preflights failed explicitly before any role attempted a
provider request. The configured model was `gemini-3.1-flash-lite`.
There are zero live claims, no autonomous selections, no live agent
disagreements, and no provider usage or cost observations.

The comparison reran the existing 2B.1 controlled queries, separately
from the live and deterministic directories. The two verification
artifacts matched the original controlled outcomes exactly. Independent
source review covered all four mock steps: two written calls had adequate
support and two added chronological claims were unestablished. Both
unestablished claims used real citations; the mocked reviewer accepted them
and the deterministic gate excluded them. Support was 2/4 and exclusion
among unestablished claims was 2/2. These are programmed adversarial cases,
not estimates of live model accuracy. The source locations were p-limit
`index.js:21–23` and Flask `src/flask/app.py:527,546–549`. The local
review ledgers store the full commit-pinned links and reasons. No change
to ranking, prompts, or retrieval is justified by this comparison.

## Run the same evaluation

Run from the project root, using a new directory per batch:

```sh
.venv/bin/python tests/live_mechanism_eval.py run .repolens-cache/checkpoint-2b2/baseline --no-ai --holdout
.venv/bin/python tests/live_mechanism_eval.py run .repolens-cache/checkpoint-2b2/live --provider gemini --holdout
```

The live command requires `GEMINI_API_KEY` in the local process environment.
Existing Claude setup is also supported. Pass `--model` to freeze the
requested model explicitly. Each repository gets at most three role calls,
no revisions, 6,600 reserved output tokens, a 150,000-byte input limit per
role and a 60-second provider timeout. The prompts are the current generic
role instructions. The runner supplies no mechanism names, paths or expected
answers. Rerun before and after a future targeted fix using identical pins,
limits and model identities in different directories.

Per-role telemetry includes UTC timestamps and monotonic elapsed time.
Provider responses record the reported model revision, when present, and
allowlisted usage counters. Gemini may include thought and cached tokens.
Claude exposes input, output and cache counts when reported. Missing
usage stays missing. Reserved output tokens are a budget, not a measured
invoice. Calculate cost from model- and date-specific rates only where
all applicable counters and rates are available. No rate or estimated
price is inferred here. The optional trace remains local and includes
source excerpts and agent output. Provider credentials and raw transport
error bodies are excluded.

## Independent review

1. Open the run and trace. Save the selected and alternative capabilities,
   rationale, entry entities and gaps from `artifacts.understanding`.
   Assess whether the selected capability is central, useful but
   secondary, poor or unestablished, citing the repository's own docs.
2. Review all final proposed steps, up to the current schema limit of
   eight per repository. Review accepted and excluded steps. If fewer
   are reviewed, report the number reviewed and emitted. On the first
   pass, avoid using the agent verdict as a reference label.
3. Check each claim against the cited pinned excerpt and surrounding
   docs, source code and relevant test assertions. Preserve conditions
   and distinguish tests written in the repository from observed results.
   Record one verdict: `supported`, `insufficient` for a correct claim
   with inadequate cited support, `incorrect`, or `unestablished`.
   Include references and the reason for each verdict.
4. For retrieval relevance, review the complete investigation evidence
   packet if feasible. If sampling, take its first ten records in packet
   order and disclose the sample rule. Count an excerpt as relevant only
   if it materially helps establish or challenge the chosen behavior.
   Record relevant and reviewed counts. Describe important missing
   source independently of the relevance ratio.
5. Compare human verdicts with the reviewer and gate. Record
   false acceptances and exclusions, and audit how unresolved claims
   were communicated. Metrics count only reviewed rows. A denominator
   of zero is unavailable, rather than a zero-percent rate.

Fill the generated `<name>.review.json` and run:

```sh
.venv/bin/python tests/live_mechanism_eval.py score \
  .repolens-cache/checkpoint-2b2/live/flask.json \
  .repolens-cache/checkpoint-2b2/live/flask.review.json
```

The scorer binds reviews to the exact artifact digest and commit. Do not
generalize results beyond the reviewed sample. An unresolved result should
remain usable as a documented example or source inspection prompt, with no
fabricated behavioral transition.

Before the Story Planner consumes a mechanism, evaluate live false
acceptances, require a separate claim-level support label and exact
citations, preserve order and condition uncertainty, and provide a fallback
for missing behavior evidence. The current language-model judgments do not
supply a runtime proof.

## First live failure investigation

The original `live/` directory was preserved. The understanding stage
for p-limit returned the pinned GitHub URL in `repository` while the old
contract compared it to `p-limit`. Its full commit and snapshot ID were
correct. The current provider schema omits identity echoes and the
orchestrator attaches authoritative identity. Exact legacy aliases require
the same snapshot and commit. The captured candidate's
`pLimit(concurrency)` remains an unresolved entry hypothesis.

Flask supplied `src/flask/app.py` while the supplied packet already
contained `file:src/flask/app.py`. The coordinator can bind an exact
packet path to its matching file entity. Unknown hints are kept separate
from stable entity IDs and never enter mechanical assertion checks.

itsdangerous completed Understanding. Its Investigator request failed
after about 1.01 seconds with only the class `ScanError` recorded, without
a provider response or an HTTP status. The original HTTP or transport
cause cannot be recovered from that trace. New diagnostics retain a safe
category and HTTP status. No raw body, headers, URL or exception text is
logged. One delayed retry is allowed for classified transient failures
within the same call and output budget. HTTP 429 is intentionally treated
as an ambiguous rate or quota signal and is not retried automatically.

A captured-reply replay accepted Understanding in all three cases. The
selected candidates were promise concurrency limits, the central Flask
application class, and the BadData exception. Only the first is already
phrased as a behavioral mechanism. The replay had a one-call limit and
did not invoke either downstream role. A separate Gemini rerun preflight
in `live-reliability-rerun/` made zero calls because this process lacked
`GEMINI_API_KEY`. The captured runs contain no completed mechanism or
verification report. No new provider usage or costs were incurred.

From a terminal with the existing Gemini credential, use a new output
directory to preserve both the original failure and the blocked rerun:

```sh
.venv/bin/python tests/live_mechanism_eval.py run \
  .repolens-cache/checkpoint-2b2/live-after-fixes --provider gemini --holdout
```

The next live batch, preserved under `live-after-fixes/`, returned no
candidate in any Understanding reply. Flask and itsdangerous had
schema-valid replies with cited documented capabilities. p-limit omitted
the namespace on three citations, each uniquely matched to a supplied
`context:` ID. Understanding now restores that prefix only for a unique,
exact 24-hex suffix and still checks the pinned excerpt. The revised
prompt distinguishes a documented candidate worth investigating from a
verified runtime explanation. Captured-reply replay accepted all three
Understanding replies; it did not create candidates or run later stages.

## Investigator HTTP 400 isolation

In the `live-candidate-check/` batch, all three Understanding stages were
accepted and all three Investigator requests received HTTP 400. No
investigator reply or verification result exists. Both roles share the
configured model, Gemini v1beta endpoint, JSON MIME type and output
budget. The investigator uses a different response schema with nested
bounded arrays, and its recorded request estimates were approximately
44–51 KB. The saved diagnostics did not retain the API error status,
message or field violations. Schema grammar complexity is a hypothesis,
not a confirmed diagnosis. Google documents that nested array bounds can
multiply the output grammar state count.

The adapter now reads a bounded HTTP 400 error body and emits only a
recognized API status, a recognized diagnostic category and allowlisted
request field paths, when present. It emits no raw response or request
content. HTTP 400 remains non-retryable.

With credentials configured, run the synthetic probe before any full
repository evaluation:

```sh
.venv/bin/python tests/gemini_investigator_probe.py
```

The probe tries the original schema first. On HTTP 400 it tries the same
request with wire-only array bounds removed. If that still returns 400,
it tries JSON mode without a wire schema. All replies must meet the
original full local schema. The probe stops at the first locally valid
response or a non-400 failure. No candidate wire changes are enabled in
production pending isolation. This session lacked a key and did not send
a synthetic or repository request.

The credentialed synthetic probe reproduced `structured_output_complexity`
with the original Investigator schema. With only wire-level `maxItems`
removed, Gemini responded and the reply passed the full local schema.
The production Gemini Investigator now uses that projection. Claude
and the other two roles retain their prior wire schemas. The local
controller still rejects oversized arrays and checks evidence independently.
The next credentialed repository run is p-limit only, with the pinned
SHA, three calls and no revision.

## Independent review of the first successful p-limit live pipeline

The live workflow selected batch limiting through `limit.map`. This is a
useful documented example of the library, while the shared admission
mechanism is broader. Two of three claims were both source-supported and
accepted. Neither accepted claim explained the selected batch mechanism.
The excluded claim's TypeError wording is supported as a conditional
statement, but its additional order assertion is unestablished and its
evidence classification is wrong. The gate excluded the whole step.

The missing flow is batch submission (`index.js:106–125`), admission
and waiting (`index.js:19–25,50–68`), and freeing capacity on settlement
(`index.js:27–47`). The Investigator packet contained isolated batch
and enqueue lines but did not include the admission guard or settlement
path. This is a retrieval gap in addition to a relevance gap in the
accepted steps. The review ledger and score are beside the live artifact.
No post-fix Flask or itsdangerous verification artifact was available.
