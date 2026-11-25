# RepoLens visual explanation MVP

```sh
.venv/bin/python -m repolens explain https://github.com/sindresorhus/p-limit \
  --provider gemini --expect-commit a8a6fbec4e0e866d6d779b10889bb4f5567e70eb \
  --out p-limit.html --artifact-out p-limit.story.json
open p-limit.html
```

A provider credential is needed only during generation. The same selected
model supplies Understanding and Story in two ordinary calls. The optional
`--retries 1` permits one delayed retry for a classified transient failure
across the whole generation. Model, timeout and per-call output tokens
are configurable. `--no-ai` generates an explicitly labeled deterministic
preview. A missing provider key fails explicitly. A bad story reply after
successful understanding falls back to the available explanations.

## How it fits together

The shared snapshot captures the commit and checks pinned source lines.
The existing context reader and structure analysis supply README and
documentation excerpts, manifests, examples, measured imports and
source context. The explanation packet combines broad and targeted
retrieval under a byte budget. This path does not invoke the experimental
orchestrator.

Understanding emits beginner-language claims by topic with evidence IDs
and uncertainty. The validator drops claims with untraceable references.
The planner receives only retained claims and arranges them into scenes
by ID. The renderer uses those IDs as labels and captions, so a scene
cannot introduce another fact through an uncited caption. Titles and
objectives are instructional copy. Scene data runs through predefined
components, and generated code remains plain text. Ordinal flow scenes
are labeled conceptual. Evidence checks confirm IDs, paths, ranges and
exact excerpts. A valid citation does not establish semantic entailment.

The frontend supports an overview, comparison, conceptual sequence,
selectable relationship and capability views, code alongside explanation,
setup steps and the existing import explorer. Interactive scenes change
the active concept, caption and citation. Ordered scenes offer Next,
Previous, Replay, keyboard arrows and optional Play/Pause. Auto-play is
suppressed during reduced motion. The existing standalone bundle
includes scripts, CSS and fonts. GitHub links are optional online exits.
No source repository code is executed.

## Evidence and evaluation

The three local artifact pairs are under `.repolens-cache/mvp/`.
They are deterministic previews of real pinned sources. The model
generation path stopped at Understanding with
`Set GEMINI_API_KEY to run the Gemini writer` in this session. No live
model draft, story, usage, or quality results exist for this pipeline.

| Preview | Pin | Pinned excerpts checked | Content review |
| --- | --- | ---: | --- |
| p-limit | `a8a6fbec4e0e866d6d779b10889bb4f5567e70eb` | 9 | README introduces async concurrency and supplies the install and use example. The reader's closure-optimization excerpt was peripheral as a problem statement, so deterministic previews avoid promoting that slot. |
| Flask | `49943b5a94413a530761350f04e896f76e8d620e` | 12 | README supports the web-framework description and a minimal application. The CLI and install command are present. A Celery forms excerpt still needs integration context before being used as an application claim. |
| itsdangerous | `672971d66a2ef9f85151e53283113f33d642dabd` | 4 | The stated safe round-trip comes from the README. The install and serializer example are available. The excerpt alone does not teach signing or make claims about encryption. |

No model-authored mechanism is present in these three previews. A
separate `synthetic.html` uses two synthetic model replies to exercise
the real ingestion, validation and HTML generation path with an
interactive walkthrough. Its visible label discloses the synthetic
fixture. Tests also exercise two stages via the mocked Gemini transport.

Open the previews directly from the project folder:

```sh
open .repolens-cache/mvp/p-limit-preview.html
open .repolens-cache/mvp/flask-preview.html
open .repolens-cache/mvp/itsdangerous-preview.html
open .repolens-cache/mvp/synthetic.html
```

Frontend build passed. Python had 85 passes and two pre-existing expected
failures. All 11 frontend tests passed. Browser rendering remains unverified.
Python Playwright was unavailable and cached browser launch checks found
that Chrome closed immediately and WebKit had no installed executable.
With Playwright and Chromium installed:

```sh
.venv/bin/python tests/browser_check.py --browser chromium \
  --story-report .repolens-cache/mvp/synthetic.html
```

The browser check targets offline rendering, keyboard progression,
replay, pinned links, narrow-screen overflow and reduced-motion playback.
Next, generate the three live model reports in a credentialed terminal,
run browser checks, and audit each planned mechanism against the pinned
source before extending the scene library.
