# Report input

The helper creates the report identity, exact excerpts, and pinned links.
Write a JSON object with `evidence`, `claims`, `scenes`, `unknowns`, and optional
`lessons`, `lesson_menu`, `intro_lesson`, `section_art`, `hero`, `guide`, and `cover`. The packet supplies existing setup entries. An optional `setup`
object can select, replace, or add setup groups using the same item
shape as the packet.

- `evidence` maps your short aliases to `{"path":"relative/path","line":10,"end_line":18}`.
  Use tracked files and inclusive, one-based ranges. Give each assertion the
  narrowest range that supports it. Use up to 30 explicit ranges of up to 60
  lines. The packet's existing evidence IDs can also be used directly.
- Each entry in the `claims` array has `id`, `section`, `label`, `text`, and
  `evidence_ids`. Sections are `purpose`, `audience`, `problem`, `capability`,
  `mechanism`, `application`, `limitation`, and `glossary`. Use a separate
  statement per finding. Add a purpose claim for the opening.
- Each `scenes` entry has `kind`, `title`, `objective`, `accessibility`, and
  `claim_ids`. Use `explorer` for independent topics, `comparison` for alternative
  inputs with documented outcomes, `flow` or `walkthrough` for a supported
  sequence, or `example` for an example alongside claims. An ordered scene
  or comparison requires two or more claim IDs.
- `unknowns` is an array of coverage gaps or material limits on the conclusions.
- `setup` is optional. Supported groups are `requirements`, `install`,
  `first_run`, `expected_output`, and `gotchas`. Each item has `kind`, `text`
  and `evidence_ids`. Use exact source text for commands, code examples, and
  documented output. Use kind `note` to explain placeholders or conditions.

## Looping opening

Design one large illustration for the report’s first screen. Choose a scene
with a focal point and a place for the main action. Use the project’s purpose
to give the scene something distinctive to depict. Keep the edges transparent
and compose the artwork into the page. A large, coherent base with one or two
separate moving pieces can create a stronger scene than a row of assets.
Commission the art from the built-in image tool if available. Use coordinated
[freeform marks and PNG pieces](freeform-stage.md). Vector marks can work on
their own when a drawing, chart, or text transformation suits the concept.

Add a `hero` object with `alt` (one line up to 300 characters), `evidence_ids`
(one to eight), `height`, `objects`, and `frames`. Optionally supply the verified public
project name as `title` when the repository slug is different. The first frame should read
as a finished still. Design the layers around one action before generating the pieces. Supply three to eight frames with `changes` and
`duration_ms` (650–4000). Each duration is the time from that pose to the next.
The final pose transitions back to the first automatically. Build a gentle
return into the story and leave enough margin for the moving parts. Motion
is illustrative, so avoid suggesting performance or timing measurements.

For a coordinated gesture, add `cues` to a hero frame or to a guided frame
with `motion_ms`. Each cue has `at` (an increasing whole percentage from
1–99) and `changes`. Use up to eight cues per transition. Each cue overrides
the pose the transition started from. For the hero, cues follow the outgoing
pose and also work on its return to the first pose. In a guide, cues lead
into the named frame from the preceding frame. Sketch who moves first and
what reacts. Model a moving object between a pocket's back layer and a
separate foreground lip if it needs to disappear into the pocket. Design a
short hold into the action so the viewer can see the contact and result.
Consider how it reads at phone scale.

Preview the whole loop beside the title. Check that it makes sense before
reading the text and that the first frame communicates the same idea. The
renderer provides pause and a reduced-motion still. An older report can also
carry a static cover as described below.

## Guided story

Use a guided sequence only when time or order explains the behavior. Set up the question, show a causal
change, and connect what the viewer can see back to its outcome. Make each
chapter build on the last. Choose the number of beats and reading time from
the source and the viewer's needs. Leave time to look at changed details.
Use different compositions from the opening. Keep any hands-on exercise as
a separate lesson that the reader can enter from the guide.

For new reports, use `kind: "guide"` in `lessons` and put the following data
in its `guide` field. A top-level `guide` remains supported for earlier reports.

A `guide` has `title` (100 characters maximum), `prompt` (240 maximum), and
one to three `chapters`. Each chapter has a unique lowercase `id`, a `title`
(up to 64 characters), and `height` and `objects` from the
[freeform stage](freeform-stage.md). Supply at least two `frames` per chapter and at most six in the entire guide.
Each frame has `changes`, `caption` (350 characters maximum), one to eight
`evidence_ids`, and `duration_ms` (2500–16000). Each change is relative to
the chapter's base objects. The player moves into that pose, then holds it
for the rest of the supplied time. To show a longer cause-and-effect movement, set
`motion_ms` on a frame after the first. Its minimum is 500 and it leaves at least
1200 ms inside `duration_ms` for the caption and final pose. Use an optional
`callout` with short `text` (up to 32 characters) and `x`, `y` (12–88 percent
from the top-left) near the resulting change. The player shows it when the
motion settles. Check that it is legible on a narrow screen and clear of
critical artwork. A visible change should teach something.
Use a shorter format if the evidence supports only one simple observation.

Check that it plays across chapter boundaries, that the captions stay on
screen long enough to follow, and that the source evidence tracks the current
frame. The reader can pause, jump chapters, replay, and skip to Try It.

## Static cover

Choose a single recognizable scene that visually expresses what the project
helps someone do. Ground the concept in the purpose and core behavior. Pick
representative objects, a clear focal point, and a cohesive palette. Give the
artwork depth using viewpoint, lighting, layered shapes, and cast shadows.
Request a landscape still, with breathing room and bold details that hold up
on a phone. Let the page display the title and explanatory copy. Keep the art
free of added text, logos, animation, and invented interface details.

Use the session’s built-in image generation tool when available. Generate
the image from an original prompt, confirm it fits the evidence, and save it
to the output directory as `cover.jpg`. Export a still JPEG about 1200–1600
pixels wide at up to 2 MB. Add this report metadata to the draft:

```json
{"cover": {"alt": "A short description of the scene and what it represents.",
           "evidence_ids": ["purpose-source"]}}
```

The helper embeds the artifact in the HTML, with no runtime dependency. The
cover is an illustration of the project. Use the evidence to support the idea
shown, and describe the actual image in the alt text. If the session lacks a
built-in image generation tool, use the existing opening and report the
coverage gap.

## Choose and place teaching sections

Use `lessons` to add one to six teaching sections inside the story. Each has a
unique lowercase `id` and an integer `after`. Use `after: 0` to place a section
before the first ordinary scene and `after: 1` after the first scene. The maximum
is the number of entries in `scenes`. Sections at the same boundary appear in
the order supplied. An ordinary prose scene can introduce the key question.
Use more than one format where each makes a different idea easier to grasp.

- **Compare.** Add `kind: "compare"`, a `title`, a learner-facing `prompt`,
  `columns` with two or three alternative labels, and one to six `rows`. A
  row has a `label` and `cells` in column order. A cell has `text` and
  `evidence_ids`. Keep cell text short and compare alternatives under aligned
  conditions. Clicking a cell exposes its citations.
- **Annotate.** Add `kind: "annotate"`, `title`, `prompt`, `source_id`, and two
  to six `notes`. Choose one actual source excerpt of up to 24 lines for
  `source_id`. Each note has `label`, `first`, `last`, `caption`, and
  `evidence_ids`. Its inclusive line numbers start at 1 for the excerpt.
  Selecting a note highlights those lines. Suitable excerpts include an
  example, a short public function, an input file, or a configuration block.
- **Explore.** Add `kind: "explore"`, `title`, `prompt`, and two to six
  `parts`. Each part has a `label`, an `example` display string, a `caption`
  explaining its role, and `evidence_ids`. Use this when understanding the
  parts or responsibilities matters more than their order.
- **Picture.** Use [an explorable illustration](#explorable-illustration)
  when one coherent picture communicates the idea. A second view can show
  a useful before-and-after or an alternate state.
- **Experiment.** When the important behavior is combining inclusion filters
  across fields, use [the filter experiment](#filter-experiment). The reader
  chooses independent inputs and can inspect live results.
- **Illustrate.** Add `kind: "illustrate"`, `title`, and `prompt`, then use
  [the freeform stage](freeform-stage.md) to draw and change your own composition.
- **Animate.** Add `kind: "animate"` and a `plan` as described below. Choose a
  visible state change with a supported cause. Use motion when seeing that
  change helps the reader.

Each point or frame needs one to eight evidence IDs. Keep section titles
under 100 characters, prompts under 240, and control labels concise.
For new reports use `lessons` for these sections. Older artifacts with
top-level `visual` or `behavior` remain supported.

## Lesson chooser and supporting graphics

Set `lesson_menu` to the IDs of two or more standalone lessons, with a
suggested starting point first. Choose the entries from what beginners need
to learn. If a sequence has prerequisites, keep those beats together inside
a guide. A standalone guide can still sit beside a separate independent
lesson in the switcher. Only the selected lesson is displayed. Omit the menu
for one path through the material. Set `intro_lesson` to a separate teaching
section ID when a short visual example can communicate the problem or
payoff. The hero button links to that example before the main lessons. For one quick comparison, use the compact reveal below.

Use `section_art` to attach source-backed transparent PNGs to supporting
sections. Its keys are `chapter-0` for the first ordinary scene and so on,
`learn-setup`, or `learn-source`. To change the art with the selected subsection,
use `chapter-<index>-<claim-id>` or `learn-setup-<group>`. The section-wide
key can supply a fallback. Use `lesson-<id>` for a dedicated lesson thumbnail in the chooser. Leave the selector text-only if there is no dedicated thumbnail. Each entry
has `asset` (PNG file ID in `artwork/`), `alt` (up to 300 characters), and
one to eight `evidence_ids`. Choose supporting compositions that explain
what the attached section adds. Keep paper texture and lighting consistent
with the report. Give each graphic a clear idea and usable silhouette at
the size it is shown. Fresh packets require distinct files for the hero,
intro, each lesson, and each supporting topic. Pieces may repeat inside
one scene. Across sections, review the compositions visually as the
validator catches identical artwork files, including renamed copies.

## Compact opening reveal

Use `kind: "reveal"` for one short action that demonstrates a project’s payoff. Use a realistic input and an outcome that differs from the main lesson. Leave the intermediate behavior to the lesson. Reference its ID with `intro_lesson`. The renderer
keeps the illustration, action, and onward link together. Choose a short
title and prompt that will fit on a narrow screen, and check both states.

Supply the usual `id`, `after`, `title` (up to 68 characters), and `prompt`
(up to 135). Add `height` and `objects` from the freeform stage,
`alt` (up to 260), and `duration_ms` (500–3500). The two `states` each
have an action button `label` (32 maximum), a short `caption` (135
maximum), `changes`, and one to eight `evidence_ids`. The first action
reveals the result and the second returns to the initial state. Optional
`cues` use the same format as the hero and are relative to the initial
state. Keep the main context visible as the result changes so the viewer
can compare the difference without having to remember another screen.

## Explorable illustration

Choose one composed image that shows how the key pieces relate. Decide where
someone’s eye goes first and how they will follow the picture. Generate a
different composition from the opening, using related paper texture,
dimensional layers, and lighting. With the image alone, a reader should be
able to locate the main idea. Add short detail captions that explain why
the pieces matter. Use a second image only if switching states makes a
source-backed comparison clearer. Match its framing so the visual difference
is easy to see.

Use `kind: "picture"` with `id`, `after`, `title`, `prompt`, and
one or two `views`. A view has a `label` (up to 40 characters), `alt`
(up to 300), an `asset` saved as `OUTPUT_DIR/artwork/<asset>.png`, and
one to six `points`. Each point contains integer `x` and `y` positions
(8–92 percent from the top-left), a `label`, a short `caption`, and
`evidence_ids` supporting what that part teaches. Preview the positions
over the actual image so the markers point to the right details without
covering any important feature.

## Filter experiment

Use `kind: "experiment"` with the usual `id`, `after`, `title`, and `prompt`,
plus a short `explanation` (350 characters maximum), one to eight
`evidence_ids` for the filter rule, and `height` and `objects` drawn using
[the freeform stage](freeform-stage.md). Design a distinct lesson scene
that shows how records are kept or hidden as the reader changes inputs.
Use separate assets from the opening where raster art helps.

- `groups` contains two to four independent filters, each with a lowercase
  `id` and a short `label`. Each filter offers the distinct values present
  in the sample records. Use two to six values per group.
- `items` contains three to eight sample records, each with a unique `id`,
  readable `label`, and `values` mapping every group ID to its value.
  `hidden` maps the record's stage mark IDs to their changed poses when
  the record is filtered out. Leave visible poses in the base `objects`.
  Marks can move into a different area or become hidden. Each record owns
  its own moving marks.

An empty group permits all its values. The renderer includes any selected
value within one group and requires every active group to pass. Use this only
where the sources establish that behavior. Provide sample combinations that
can widen a result, narrow it, and produce an empty result where relevant.
Ask the reader to predict a change before trying it. In browser review, check
both the position of the records and the explanation when one is inspected.

## Composable illustration

Use this object as the `plan` of an animated section. Choose a visual idea that
makes the source behavior easier to predict. The shapes carry meaning through
their placement, labels, and changes. Prefer a compact grid and short labels.
Each choice should lead to a distinct visible path or result and show the
reason it changes. An existing chapter can provide context before the scene.

| Field | Shape |
| --- | --- |
| `title`, `prompt` | A short lesson title (70 characters maximum) and a learner-facing question or instruction (240 maximum). |
| `grid` | `{"columns":3,"rows":2}`. Use 2–4 columns and 1–3 rows, numbered from 1. |
| `objects` | 2–8 objects with `id`, `label` (up to 28 characters), `shape`, `tone`, `column`, and `row`. Each object occupies its own cell. Shapes are `card`, `pill`, `circle`, `stack`, and `gate`. Tones are `amber`, `rose`, `mint`, `blue`, and `violet`. |
| `paths` | Zero to ten arrows with `id`, `from`, and `to`. Endpoints are object IDs. |
| `tokens` | Zero to four movable items with `id`, `label` (up to 16 characters), and `tone`. Keep labels short on busy boards. Use the same token ID as the item moves. |
| `choices` | 2–4 alternatives with `id`, a distinct `label` (up to 48 characters), and `frames` (2–6 per choice). |

Use short lowercase IDs with hyphens. The renderer draws only the supplied
objects and activates the chosen frame. Each frame is a full snapshot with
these six fields, including empty maps or arrays as needed:

- `caption` explains the change and why it matters (up to 350 characters).
- `evidence_ids` cites one to eight pinned excerpts that support the frame.
- `values` maps object IDs to visible strings (up to 60 characters each).
- `placements` maps token IDs to object IDs. Omit a token here to hide it.
- `active` lists highlighted object IDs.
- `paths` lists highlighted arrow IDs.

Moving a token to another object animates the transition. A frame can also
show a decision or update a value without a token. Represent distinct
intermediate states in separate frames. Display the end result in an object
value or position so it is visible on the diagram. The renderer does not
execute repository code or calculate unsupplied outcomes. Base the choices
on documented inputs, written tests, or source-supported inference and scope
the captions to those examples. Make any illustration-only timing or labels
clear where they could be mistaken for measured results.

## Legacy walkthrough data


The renderer supports these two shapes. Choose the family by its behavior,
independent of the repository name. Keep example size small and describe
timing or identities as illustrative if applicable.

`behavior` has `family`, `question`, `facts`, and `scenarios`. Each fact has an
`id`, `assertion`, and `evidence_ids`. A scenario has `id`, `choice`,
`initial_state`, and ordered `steps`. Each step has a unique `id`, an
`event`, its whole resulting `state`, a plain-language `caption`, and
`fact_ids` that refer to behavior facts. Use two to four distinct choices
with identical initial states. Follow the scenario through its outcome.

- **Capacity:** Use this for a queue that fills available slots after a
  limit change or a task settlement, while allowing existing work to
  continue. The state has integer `limit`, `waiting`, `running`, and
  `settled` fields. Use at most eight tasks and begin with active and waiting
  work. The numeric choice is the desired limit. Use `limit` when it changes
  and `settle` when one active task completes. Write the resulting stable
  state after admission. In every choice, show the waiting count decrease
  when waiting work starts. A reduced limit can leave the running count
  temporarily above it.
- **Request:** Use this for a scoped, evidence-backed request example.
  Every state has string fields `method`, `path`, `match`, `handler`, and
  `response`. Keep the method fixed across choices. The choice is a path.
  Start with only the method set. Use `submit` to set the path, `match` to
  set `matched` or `unmatched`, `dispatch` to set a handler for a match, and
  `respond` to set the visible result. Each event changes only its named
  field. On a miss, go from match to respond. Explain routing-error
  handling in the response caption. Scope status and handler claims to the
  example, including any assumptions about hooks or error handling.
