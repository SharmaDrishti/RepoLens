# Behavior and scene contract

RepoLens should teach one central behavior a newcomer can observe or reason
about. Start with a concrete question about that behavior. Use the same pinned
snapshot for the beginner lesson, code example, and developer evidence.

## What passes between stages

| Stage | Output |
| --- | --- |
| Select and retrieve | A learner question, a scoped example and entry point, and evidence for the operation, its conditions, and the outcome. Start from a documented example or public entry point and follow connected source and relevant written test expectations. Keep unresolved calls and external boundaries visible. |
| Describe and review | A versioned behavior record for one snapshot. It contains the question, example, assumptions, behavior facts, scenarios, and unresolved details. Each behavior fact has a stable ID, a short assertion, applicable conditions, and pinned evidence references with their role. |
| Plan and render | A scene selects a behavior, scenario IDs, and a visual family whose input and state shapes fit the scenarios. The shared player steps through the approved states and displays the caption and source for each change. The same behavior can support a simpler scene when no visual family fits. |

Use the existing evidence records for path, line range, excerpt, and snapshot
identity. A reference's role distinguishes documentation, written source,
and a written test expectation. More than one role can support the same
assertion. Keep any inference and its scope explicit. A navigation hint can
help find evidence, and a static import can link to a file. A runtime claim
requires behavior evidence. Source ranges can be checked automatically.
Whether the ranges support the assertion is a separate review question.

### First interactive format

Use finite scenarios for the first implementation. The user chooses between
supported inputs at a clearly marked decision point. Each input leads to
its own sequence of states and an observable outcome. This supports
meaningful comparisons and keeps the player small enough to review.

- A behavior contains `schema_version`, `id`, `snapshot_id`, `question`,
  `example`, `assumptions`, `unknowns`, `facts`, and `scenarios`. A fact
  contains `id`, `assertion`, `conditions`, and `evidence`. Evidence
  entries pair an existing reference ID with its role for that assertion.
- A scenario defines an ID, one choice value, an initial state, and ordered
  steps. Each step supplies a stable ID, an event, the resulting state,
  a short caption, and the IDs of the facts supporting the change.
  Choices being compared share the same starting conditions and change
  one input at a time. Labels and example values can be illustrative.
  Cite any repository behavior those values demonstrate.
- A scene carries the behavior ID, scenario IDs, and scene family. For the
  initial proof, a capacity scene reads a limit and waiting, running, and
  settled counts. A request scene reads a method, path, and the match,
  handler, and response as they become known. A shared player owns step,
  replay, speed, captions, and reduced-motion behavior. Scene components
  can vary in illustration and layout. Repository names stay out of
  the component selection.

Before rendering, check the snapshot and IDs, required state fields, allowed
choices, and state consistency. Review that each scenario covers the learner
question from input through outcome, including any guard that changes the
result. Review captions and visuals for claims beyond the cited facts. A
schema or consistency check alone cannot establish semantic support.

Use a clearly labeled conceptual simulation when the interaction depicts
reviewed scenarios. If evidence establishes only one path, a cited
walkthrough can still step through it. If it establishes a usage example
but leaves the mechanism uncertain, show the annotated example and state
the gap. An unknown outcome stays unknown. The player renders data and
has no need to run repository code, generated code, or network requests.

## Source-checked examples

These are authored test cases for the contract. They exercise the proposed
shape and its evidence requirements. They also provide expected results for
testing automatic generation later.

### p-limit · When can a waiting task start?

Use three submitted functions. Begin after the first two have been admitted
with the limit set to two. Let the learner predict what will happen to the
third task, then choose whether to hold, raise, or lower the limit. Animate
the count and task changes together, with a caption next to the depicted
event. The tasks and settlement sequence are illustrative.

| Fact | Scope and evidence |
| --- | --- |
| Submitting a function adds it to the waiting queue. | The public usage example submits three functions. The wrapper passes the submitted function to enqueue. [Usage](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/readme.md#L15-L28) · [Enqueue and wrapper](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/index.js#L50-L68) |
| A waiting task can be admitted when the active count is below the limit and the queue has work. | The source increments the active count and takes a queued item inside that guard. [Admission guard](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/index.js#L16-L25) |
| When a task settles, p-limit frees capacity and checks the queue again. | The release path follows either fulfillment or rejection. The scene uses “settled” to cover both. [Release and settlement](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/index.js#L27-L48) |
| Changing the limit changes admission. Running work continues when the limit drops. | The setter updates the limit and schedules an admission check. The upstream tests expect different admission counts after a decrease or increase. [Setter](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/index.js#L91-L104) · [Written test expectations](https://github.com/sindresorhus/p-limit/blob/a8a6fbec4e0e866d6d779b10889bb4f5567e70eb/test.js#L443-L479) |

| Choice | Event | Limit | Waiting | Running | Settled |
| --- | --- | ---: | ---: | ---: | ---: |
| All | Begin with the third task waiting | 2 | 1 | 2 | 0 |
| Keep at 2 | One active task settles. A slot opens and admits the third. | 2 | 0 | 2 | 1 |
| Raise to 3 | The scheduled admission check starts the third before either active task settles. | 3 | 0 | 3 | 0 |
| Lower to 1 | Both active tasks continue. The third stays waiting. | 1 | 1 | 2 | 0 |
| Lower to 1 | One active task settles. One running task still fills the limit. | 1 | 1 | 1 | 1 |
| Lower to 1 | The other active task settles. The third is admitted. | 1 | 0 | 1 | 2 |

The counts show stable points after each depicted event, including any
immediate admission check. They conserve three tasks. The running count may
temporarily exceed a newly lowered limit. The guard applies when admitting
additional work. Reject a scenario that cancels active jobs on a decrease,
admits a task when the active count equals the limit, or implies a measured
speedup, exact promise scheduling, or a requests-per-second guarantee.

### Flask · Why does one address show a greeting and another give a 404?

Use the minimal quickstart app. Fix the method to GET and let the learner
choose the path `/` or an illustrative unmatched path `/missing`. Assume the
quickstart app as written, with no added routes handling `/missing`, no
preprocessing that returns a response first, and default error handling.
Show the request, match or miss, and result on one stage.

| Fact | Scope and evidence |
| --- | --- |
| The example registers `/` for `hello_world`. | The quickstart includes the declaration and greeting. The decorator delegates to registration, which adds the rule and binds its endpoint to the function. [Quickstart example](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/docs/quickstart.rst#L11-L36) · [Decorator](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/sansio/scaffold.py#L368-L373) · [Registration](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/sansio/app.py#L651-L662) |
| Flask records a rule and its arguments, or a routing error. | The request context delegates matching to the URL adapter. Show the input to the adapter and the result Flask receives. [Matching boundary](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/ctx.py#L405-L414) |
| A matching GET reaches the bound function in this example. | Dispatch uses the matched rule's endpoint to find the function. A hook can supply a response before dispatch, and the source has a separate branch for automatic OPTIONS. [Dispatch](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/app.py#L1007-L1021) · [Preprocessing](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/app.py#L1047-L1054) |
| The matched path produces the documented greeting. An unmatched path in this app produces a not-found response. | The quickstart describes the greeting. The lifecycle documents stored routing errors, default HTTP error statuses, and response conversion. The 404 for the illustrative path follows from the example scope and this default behavior. [Greeting](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/docs/quickstart.rst#L61-L62) · [Routing and response lifecycle](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/docs/lifecycle.rst#L126-L152) · [Response conversion](https://github.com/pallets/flask/blob/49943b5a94413a530761350f04e896f76e8d620e/src/flask/app.py#L1078-L1083) |

| Choice | Input | Match | Handler | Visible outcome |
| --- | --- | --- | --- | --- |
| Home | GET `/` | Registered home rule | `hello_world` | Documented “Hello, World!” greeting |
| Missing page | GET `/missing` | No matching rule in this app | None for the request path | 404 Not Found with default handling |

Present receipt, match or miss, and response as separate steps. The miss
branch skips the view. Reject a scenario that sends the missing path to the
home handler, generalizes all routing errors to 404, or promises which hook
or handler will run in a different Flask app. If evidence for the miss is
unavailable, use the documented home example as a walkthrough and omit the
path comparison.

## What the checkpoint establishes

The same scenario contract can describe a capacity decision and a route
decision with different visual states and the same playback controls. The
queue case needs the admission guard and settlement path. The request case
needs the example's registration, match boundary, dispatch, and response
path. Removing that evidence changes what the page can responsibly show.

## Running the behavior checkpoint

`repolens behavior` asks a provider for a behavior record and writes JSON
after checking its references and scenario transitions. Its output keeps
semantic review pending. Read the assertions, captions, and outcomes against
the source before using it in a lesson.

The command retries transient provider failures such as HTTP 503 up to twice.

The runs below supply reviewed source ranges to isolate draft generation and
validation from retrieval quality. Omit the `--focus` arguments for a
separate retrieval comparison. In a local packet check, even queries that
named relevant symbols missed p-limit's admission guard and Flask's dispatch
and lifecycle documentation. The focused runs do not establish that RepoLens
can discover these ranges or choose a learner question automatically.

With `GEMINI_API_KEY` set in the current Terminal tab:

```zsh
cd ~/Documents/RepoLens
mkdir -p .repolens-cache/behavior-checkpoint

.venv/bin/python -m repolens behavior https://github.com/sindresorhus/p-limit \
  --expect-commit a8a6fbec4e0e866d6d779b10889bb4f5567e70eb \
  --question 'When can a waiting task start as the concurrency limit changes? Compare holding, raising, and lowering the limit with three submitted tasks, starting with two active.' \
  --focus readme.md:15-28 --focus index.js:16-25 --focus index.js:27-48 \
  --focus index.js:50-68 --focus index.js:91-104 --focus test.js:443-479 \
  --out .repolens-cache/behavior-checkpoint/p-limit.live.json

.venv/bin/python -m repolens behavior https://github.com/pallets/flask \
  --expect-commit 49943b5a94413a530761350f04e896f76e8d620e \
  --question 'In the quickstart app, why does GET / show a greeting while GET /missing returns 404?' \
  --focus docs/quickstart.rst:11-36 --focus docs/quickstart.rst:61-62 \
  --focus src/flask/sansio/app.py:651-662 --focus src/flask/ctx.py:405-414 \
  --focus src/flask/app.py:1007-1021 --focus src/flask/app.py:1047-1054 \
  --focus docs/lifecycle.rst:126-152 \
  --out .repolens-cache/behavior-checkpoint/flask.live.json
```

A URL uses the usual repository cache or clones the remote's default branch.
If the checked-out SHA differs, the command stops. Pass the path to a clean
local checkout at the listed commit to reproduce the pinned case.

For OpenRouter, set `OPENROUTER_API_KEY` and add `--provider openrouter` to
either command. It uses the free router by default. To pin a specific
model, pass a model ID ending in `:free` with `--model`. The output records
the model OpenRouter reports for the completed request.

In the first live OpenRouter checkpoint, both default-route replies
hit the 5,500-token completion cap. A follow-up with the free Ling 3.2
Flash model received HTTP 429 on both inputs. The OpenRouter completion cap
is now 10,000 tokens.

The higher cap let both default-route replies finish. The p-limit reply
used labeled counts and supplied no facts. The Flask reply used evidence
IDs where the step contract required fact IDs. The validator rejected
both. A second pass pinned both requests to
`nvidia/nemotron-3.5-super-vl:free`.

| Case | Pinned-model result | Review against the example |
| --- | --- | --- |
| p-limit | Passed structural validation with all three choices. All five retained excerpts matched the pinned Git source. | Hold and raise matched the expected transitions. Lower stopped after the limit change and omitted both settlements, including the event that finally lets the waiting task start. The FIFO assumption is outside the retained evidence. The fixed-limit README example does not support a blanket claim that the active count can never exceed a new limit. |
| Flask | Rejected because the unmatched branch included a dispatch event with no state change. | The draft identified the documented greeting and the scoped 404. It correctly described `dispatch_request` raising the routing exception. The scene's dispatch event represents calling a view, so the error branch should explain the exception when it shows the error response. |

These runs isolated generation and validation using the supplied source
ranges. The next generation checkpoint needs an explicit completion check
against the learner question, in addition to checking the validity of
individual transitions.

Controlled replies against the pinned checkouts passed the same validation
for all three p-limit choices and both Flask paths. These runs checked
artifact creation, evidence roles, and scenario states. Live generation
and independent semantic review remain the next checks. An unfamiliar
repository should then test whether retrieval and scene selection generalize.

## Reviewed offline report

The print-shop illustration reads the same capacity states for each choice.
Numbered tickets retain their identity as they move. Captions and counts
advance when the ticket reaches its destination. A settlement that opens a
slot and the subsequent admission appear as separate frames.

To rebuild the p-limit pilot from its prepared artifact:

```zsh
npm --prefix web run build
.venv/bin/python -m repolens build .repolens-cache/4c5a*/p-limit \
  --story .repolens-cache/behavior-checkpoint/p-limit.reviewed.story.json \
  --out .repolens-cache/behavior-checkpoint/p-limit.reviewed.html
```

This export checks the story against the pinned checkout and requires each
capacity choice to show at least one waiting task start. It uses measured
repository data for the developer view. The prepared story reuses the live
draft's choices and source evidence, adds two source-reviewed settlement
steps to the lowering branch, and uses the repository's recipes and README
for the rest of the report. The added steps are labeled in the page. The
reviewed artifact can be rebuilt offline.
