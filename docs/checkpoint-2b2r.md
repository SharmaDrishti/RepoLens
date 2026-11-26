# Checkpoint 2B.2R — connected evidence and mechanism adequacy

## Observed failure

The first successful p-limit workflow selected the documented batch mapping
behavior and returned no resolved entry entity. The Investigator packet
ranked each relationship independently and capped each file at eight
relationships. Validation calls matched concurrency terms, while helpers
such as `next` received little lexical weight. The static graph marked the
relevant JS helper calls unresolved. The original packet covered two of
eight manually selected implementation landmarks, and the two accepted
claims covered configuration validation rather than the selected behavior.

## Retrieval and adequacy

Investigation first anchors on supplied entities, explicit qualified
API mentions, recognizable command declarations, and lexical source
symbols. It expands through measured targets and narrowly labeled
same-file name, receiver, or exact imported-name hints. Hints guide
retrieval only. They do not resolve receiver dispatch, promote imports
to calls, or establish execution order. Existing lexical documentation,
test and relationship selection still fills the remaining packet.
A source navigation walk is bounded to 5 hops and 22 relationships,
with at most 26 relationships in the initial packet and compact pinned
source windows. Each model request retains the configured byte cap.
Control-flow conditions stay attached to the original relationships.
Source windows expose nearby state updates without manufacturing
state-transition relationships.

The Investigator can request up to three supplied entity or relationship
IDs. If there are enough calls and output tokens left for Investigation
and Verification, the controller permits one read-only expansion.
It retains at most 48 relationships, 85 evidence records, and 115 KB of
serialized packet data. Arbitrary file paths are ignored. The result
records initial evidence IDs, requested IDs and added evidence IDs.
Three-call runs cannot expand. Optional expansion failures retain the
initial draft for verification when budget permits.

The independent verifier now returns adequacy dimensions separately
from its per-step semantic verdicts. The controller keeps only
dimension references to accepted claims linked to candidate evidence or
connected source. Entry, operation, and outcome receive an explicit
disposition. Conditions also receive one when relevant conditional
relationships were retrieved. Participants, state changes, and
uncertainties may be assessed as applicable. Missing, excluded, or
off-topic evidence cannot establish coverage. This is a conservative
coverage screen and independent model assessment, not a proof of
semantic completeness. Consumers should check `artifacts.adequacy`
separately from `artifacts.claim_support` and terminal status. Gemini
wire-only array bounds stay omitted for Investigator and are also
omitted for the expanded reviewer schema. Local schema limits and
the deterministic claim gate still apply to both.

## Controlled comparison

The same captured candidate and pinned checkout were used per repository.
No new agent responses were generated in this comparison. Every new
packet excerpt was checked against its pinned source range.

| Repository / captured behavior | Evidence records before → after | Connected relationships | Outcome |
| --- | ---: | ---: | --- |
| p-limit `a8a6fbe`, batch mapping | 39 → 60 | 20 | All 8 audited source landmarks recovered versus 2 before. |
| Flask `49943b5`, CLI startup | 46 → 66 | 22 | CLI command decorators, app loading, reload/error branches and the written server startup call. The server dependency and dynamic calls stay unresolved. |
| itsdangerous `672971d`, signed-token loading | 43 → 61 | 22 | Serializer loading, candidate signer iteration, payload load and signature-error branches. Multiple similarly named declarations remain possible and receiver targets remain unresolved. |

The p-limit landmarks were `index.js:21,28,43,47,57,67,112,125`.
The new packet covers collection submission, enqueue, admission when below
the limit and the queue is nonempty, waiting when capacity is occupied,
settlement and release, and result collection. It includes relevant
`test.js` excerpts for batch behavior, including mapping with a limit and
mapping inputs with indices. Those are written expectations, not
executed upstream tests. Neither of the two historically accepted
claims explains how batches flow through these steps. The old claims
remain **partial for support, incomplete for adequacy**. A fresh live
explanation after improved retrieval is not available. The Flask and
itsdangerous comparison assesses packet coverage only.

From the repository root, rerun the controlled p-limit comparison:

```sh
mkdir -p .repolens-cache/checkpoint-2b2/retrieval-review
.venv/bin/python tests/mechanism_retrieval_eval.py \
  .repolens-cache/checkpoint-2b2/p-limit-wire-fix-live.trace.json \
  .repolens-cache/checkpoint-2b2/retrieval-review/p-limit.json
```

For Flask and itsdangerous, substitute their saved
`live-candidate-check/<name>.trace.json` inputs. The live p-limit
preflight in this session stopped before any API call because
`GEMINI_API_KEY` was absent. Run the following from a credentialed
terminal before expanding to either other repository:

```sh
.venv/bin/python -m repolens mechanisms https://github.com/sindresorhus/p-limit \
  --provider gemini --expect-commit a8a6fbec4e0e866d6d779b10889bb4f5567e70eb \
  --max-calls 4 --max-output-tokens 8800 --no-revision \
  --out .repolens-cache/checkpoint-2b2/p-limit-retrieval-live.json \
  --trace-out .repolens-cache/checkpoint-2b2/p-limit-retrieval-live.trace.json
```

A Story Planner should wait for a live result and independent review
showing that the accepted claims cover the chosen mechanism, including
guard, outcome and limitations where applicable. Source navigation
cannot justify dynamic dispatch, runtime ordering or general state
tracking.

## Latest live run diagnosis

Both saved runs used the same pinned commit and completed the three
provider stages. The earlier run selected `limit.map`. The latest reused
the generated ID `candidate:001` for a different scope, general async
concurrency limiting. The latest reached Verification but retained no
steps. All three semantic verdicts were supported. The deterministic gate
found mixed documentation and relationship fields on initialization,
mixed interpretation and relationship fields plus unsupported ordering on
queueing, and a nonbehavioral definition relationship on the wrapper.
The draft also listed an unsupplied `file:index.js` entity, which added an
error to every row. Each row already had its own rejection reason. All
seven adequacy dimensions remained unresolved because no claim survived.
No evidence expansion was requested. Although one revision was enabled,
the four-call limit left just one slot after the three stages. A revision
requires both Investigation and Verification calls.

The latest live packet had zero navigation links. It retained two of the
eight earlier batch landmarks. It contained queue-enqueue source but
omitted the admission and settlement paths for the broader selected
mechanism. The selected evidence `get:002` contained an example calling
`pLimit`, while the candidate's prose used the package spelling
`p-limit(concurrency)` and gave no entry entities. The focused fix uses
exact callable spellings in selected cited documentation as navigation
anchors when the primary walk finds no relationships. It can follow a
returned local callable under its defining scope, without resolving
dynamic calls or introducing execution-order assertions.

Controlled replay of the latest candidate yielded 18 navigation
relationships and 58 evidence records versus zero and 44. It recovered
all six inspected submit/queue/admission/settlement locations
(`index.js:21,28,43,47,57,67`), versus one in the latest live input.
It also recovered all eight prior batch landmarks, although batch
mapping was not the latest scope. This only evaluates retrieval. No
model call was made, and the verifier and its gate were left unchanged.
