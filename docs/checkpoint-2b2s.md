# Checkpoint 2B.2S — reliable revision

The captured p-limit revision was a replacement draft. The feedback
contained rejected rows and reviewer requests, but omitted the accepted
claim and the adequacy gaps. The model returned the same two invalid rows,
and the controller replaced the first result with the weaker one.
Semantic approval did not repair the mixed evidence classes.

Corrections keep IDs and additions get new IDs. Revision feedback includes
accepted claims, uncovered dimensions, evidence references, populated
structural fields, gate diagnostics and correction requirements. Review
receives independent semantic and coverage questions alongside structural
diagnostics and retained claims. The deterministic gate is unchanged.

The controller merges only passing additions or corrections. Omission,
unsupported replacements and renamed duplicates cannot remove passing
claims. A reviewer may challenge a retained claim explicitly. Withdrawal
requires a contradiction rationale and at least one different, valid
pinned citation. This is an evidence-backed semantic contradiction,
not a formal proof that the old wording is false. Accepted claims
cannot be silently replaced under the same ID. The result records
attempts and unchanged, corrected, added, rejected and superseded
claims. Coverage is evaluated over the retained set. An exact repeat
of prior claims ends revision before another reviewer call.

The controlled replay used the exact saved p-limit source packet and
captured replies. The first draft's initialization call survived.
Its two rejected rows stayed rejected when the revision repeated them.
The final result changed from the original run's unresolved to partial
claim support, with incomplete adequacy. Only the initialization call
was retained. Batch submission, queueing, capacity, settlement and
result collection remain unexplained. The enqueue claim was rejected
for mixing evidence classes, and the validation constraint was rejected
for mixing fields and citing source where documentation was required.
The replay stopped before the redundant second review. No API was called.

The pinned live evaluation remains blocked in this process because
GEMINI_API_KEY is absent. From a credentialed terminal, use the original
pin and a fresh artifact path:

```sh
.venv/bin/python -m repolens mechanisms https://github.com/sindresorhus/p-limit \
  --provider gemini --expect-commit a8a6fbec4e0e866d6d779b10889bb4f5567e70eb \
  --max-calls 5 --max-output-tokens 11000 \
  --out .repolens-cache/checkpoint-2b2/p-limit-revision-live.json \
  --trace-out .repolens-cache/checkpoint-2b2/p-limit-revision-live.trace.json
```
