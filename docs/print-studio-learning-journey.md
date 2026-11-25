# Print Studio learning journey

The source for each chapter’s learning objective, beginner explanation,
evidence, visual, interaction, takeaway and reading depth is
[the chapter map](../web/src/print-studio/content.ts). All references are to
p-limit commit a8a6fbec4e0e866d6d779b10889bb4f5567e70eb.

The first screen answers what p-limit is and who uses it. The essential
route goes from a batch comparison to the shared press scene, maps the
presses to a JavaScript limit, then ends with practical recipes and setup.
The optional route covers the remaining API and the original report.
The sticky navigation uses ordinary fragment links for the story,
playground, setup and technical sections.

The older prototype ended at the metaphor. This version connects it to
functions submitted for later execution, batch results, queue counts,
dynamic limits, discarding pending work, mapping inputs, wrapping one
function, and handling task failure. The repository describes the
library’s intended use. The story makes no claim about the author’s
personal motivation or measured performance.

The numbered tickets carry the model's job IDs from waiting to running
to finished. The physical press and illustrative durations are authored
teaching devices. The README’s first code example contains placeholders
and is annotated in place so it is clear what the developer must supply.

## Manual browser review

Open the generated Print Studio HTML in Safari and Chrome. Start on the
hero, use Tab to reach Behind the Scenes and Enter to jump there. Open the
import map and use Back to return. Repeat at a narrow mobile width.
Return to Try It and capture the initial scene, then use Replay and capture
a ticket in transit. Pause and check that the ticket and counts hold still.
Resume and watch a numbered ticket exit a press as another enters. Step
through several jobs, checking the counts against the illustrated areas
after tickets settle. Raise the limit to four, then lower it to one while
four jobs are active. The current jobs should finish and vacancies should
remain unfilled until the limit allows a new start. Finish all eight jobs,
then reset three times and replay. Repeat with Reduce Motion enabled.
Check that ticket size stays constant and that resize at mid-motion
changes only the size of the whole illustration.

Use the annotated JavaScript example and the recipe picker. Ask someone
new to p-limit to explain what the library is, what it helps with, how it
starts tasks, how a developer uses it, two capabilities, one real use and
one boundary. A correct description of the print shop alone is insufficient.

For automated captures with Playwright and WebKit installed:

```bash
.venv/bin/python tests/browser_check.py --browser webkit \
  --studio-report .repolens-cache/preview/print-studio.html \
  --before .repolens-cache/preview/print-studio-before.html \
  --screenshots .repolens-cache/preview/print-studio-shots
```

## Experience redesign and completeness contract

A review record has one row per dimension. Each row carries a status
(`complete`, `partial`, `unknown`, or `not_applicable`), established
information, snapshot-scoped evidence IDs, learning objective or scene IDs,
missing information, a rationale, and evidence limitations. A
`not_applicable` row requires a justification. A section heading alone
does not establish coverage. Keep coverage separate from browser validation
and observed visitor comprehension.

Evidence IDs below are shorthand for file and line anchors at the pinned
commit at the top of this document.

| Dimension | p-limit finding and evidence IDs | Learning objective and treatment | Review |
| --- | --- | --- | --- |
| Purpose | `readme.md#L1-L5`, `recipes.md#L19-L37` support limited async work and a request batch. The developer audience is inferred from the usage. | Essential. Editorial hero identifies the library, then a batch comparison separates possible simultaneous load from a measured result. | Complete for authored content. Private motivations are unknown. |
| Main capabilities | `readme.md#L33-L119` documents submitting functions, queue counts, updating the limit, discarding waiting work, mapping collections and wrapping a function. | Essential usage walkthrough. Optional API examples explain when each feature matters. | Complete for core documented API. Live execution of the API is outside the prototype. |
| Mechanisms | `index.js#L16-L68` shows admission and release. `index.js#L91-L104` shows limit changes. | Essential. Numbered tickets, a dedicated legend, guide bubbles and speed controls. | Complete for the central mechanism at content level. The animation uses illustrative durations and scheduling. |
| Practical applications | `recipes.md#L3-L37` shows a folder of files and a list of URLs. | Essential. Selectable illustrated inputs, operation and output. | Complete for these documented applications. Real deployments and measured outcomes are unknown. |
| Getting started | `package.json#L13-L21` and `readme.md#L5-L28` establish the Node requirement, browser support, install command and example. | Essential. Install and then follow the annotated example. | Complete for documented first steps. The example uses placeholders and has no fixed console output. |
| Limitations | `readme.md#L46-L52`, `readme.md#L76`, `readme.md#L98-L107`, `readme.md#L171-L175`. | Essential boundary note with optional queue and failure details. | Complete for the central boundaries. No speedup is claimed. |
| Evidence | Pinned docs, manifest and implementation anchors above plus static import analysis. | Essential source links and optional evidence inspector. | Partial. Authored citations are scoped to the pinned revision. Automatic semantic verification and actual comprehension remain pending. |

The story order is hero, problem comparison, queue analogy, mechanism
playground, annotated usage, capabilities, recipes, setup, limitations,
and technical exploration. The solution and mechanism share a section but
have distinct objectives. The shared contract allows other stories to
combine or reorder objectives. For Flask a potential visual centers on a
request, with a route match and response permitted only where evidence
supports them. For an uninspected machine-learning repository, preprocessing
or inference are candidates only. Mark every unsupported dimension unknown
until the repository provides evidence, even when a visual pattern is familiar.

The previous renderer starts from a committed target while maintaining a
separate animation clock. A job can therefore appear counted in its new state
while its ticket is still traveling, and pause or speed changes would require
coordinating independent timers. Some labels also share coordinates with the
tray and inbox. Replace this with one logical clock and explicit handoff
boundaries, dedicated HTML labels, and a single SVG translation per ticket.
The earlier duplicate-sized artwork is established by source inspection.
The reported intermittent resizing on Safari is still unconfirmed.

The import explorer will lay out measured edges, offer category and file
filters, preserve focus and evidence inspection, and keep behavior coverage
explicitly unavailable when the report has no verified architecture.

### Running the redesign checks

The browser script accepts both Chromium and WebKit. After regenerating the
standalone report with the preview commands in the README, run:

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium webkit
.venv/bin/python tests/browser_check.py --browser webkit \
  --studio-report .repolens-cache/preview/print-studio.html \
  --before .repolens-cache/preview/print-studio-pre-redesign.html \
  --screenshots .repolens-cache/preview/print-studio-shots
```

Repeat with `--browser chromium`. Check mobile, tablet and desktop,
including 200% zoom, caption text reflow, keyboard focus and graph pan.
For the speed controls test, switch from Slow to Fast mid-transition,
turn captions off and on, pause, change the limit, then step and reset.
Record any clip or ticket jump with browser, resolution, zoom and action.

For human review, give a first-time visitor just the page. After the hero,
ask what kind of project this is and who might use it. After completing the
story, ask them to explain task admission, describe how a developer uses it,
name two capabilities, give an application, and name a limitation. Let them
answer in their own words, record misconceptions separately, and distinguish
recall of the studio metaphor from understanding what the software does.
No participant results have been collected for this revision.

## Motion upgrade plan

| Scene | Learning goal and action | Motion and handoff | Evidence |
| --- | --- | --- | --- |
| Hero | Follow coral ticket 01 into the studio while another stays waiting. Replay on demand. | One restrained introduction; the same numbered ticket appears in the batch comparison. | README L1–5, index.js L16–25 |
| Batch comparison | Toggle how the same six tasks are admitted. | Tickets change lanes in place. This depicts simultaneous admission, with no timing or benchmark comparison. | recipes.md L19–37 |
| Queue rule | Switch between one and two active tasks at a limit of two, then free a slot. | Highlight the applicable branch; move from the rule into the playground. | index.js L16–47, L50–68 |
| Try It | Explore capacity, settlements and the largest active count reached. | User-controlled simulation clock and brief event captions; visiting another section suspends visual updates. | index.js L19–47, L91–104 |
| Usage | Step through setting a limit, handing it functions and collecting results. | Move ticket 01 through those states while matching each step to the exact README excerpt. | readme.md L15–29 |
| Capabilities | Choose a feature, then apply it to a small conceptual example. | Show what changed, including the difference between pending and active jobs. | readme.md L78–119, index.js L32–47 |
| Applications | Choose requests or files and run an illustrated walkthrough. | Distinct inputs move toward the work and result stages; those stages remain readable without animation. | recipes.md L3–37 |
| Setup | Select a documented step and copy the literal install command. | Brief step transition with no simulated terminal output. | package.json L19–21, readme.md L5–29 |
| Import map | Select a file or edge and inspect evidence. | Emphasize incident edges and gently refocus the graph. No motion represents runtime. | Measured static imports |

The p-limit scenes and wording are authored. The once-visible trigger,
motion tokens, ticket strip, stepped content, and graph focus are reusable
interaction patterns. CSS handles short presentation transitions and the
existing deterministic player handles simulator time. Reduced motion
retains the same labels and control outcomes. Coverage is complete for the
six authored teaching dimensions listed above, with evidence partial.
Browser validation and observed comprehension remain separate checks.
