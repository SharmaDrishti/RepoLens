# Freeform stage

Use this when the reader can see what an input changes and why. Sketch the
composition that makes the idea clear before writing the data. Vary positions,
sizes, layering, and labels to communicate the behavior. A scene can use a
cross-section, an arrangement of items, before-and-after text, or an entirely
different visual idea. Reuse an object's ID as it moves. Use the board to
communicate results and use the caption to explain their cause in plain language.
Ask the reader to predict a result when that helps them learn.

Give the most important change the strongest contrast and let supporting
shapes recede. An outline can show a container, a dashed mark can show an
empty slot or a limit, and a muted mark can preserve context without competing
with the result. Where the geometry is the idea, make the drawing itself the subject. A trace can show a contour, a sampled signal, or an image feature changing. Place labels close to what they explain. Use motion to
follow an item, show a change in size, or reveal a change in state.

Add these fields alongside `id`, `kind`, `after`, `title`, and `prompt`:

- `height` gives the board height, an integer from 96 to 300. Width is 320.
  The origin is the top left. Use whole coordinates. Leave room for labels
  and a small margin on all edges. The stage scales to the available width.
- `objects` contains 2–40 marks in back-to-front drawing order. Each has a
  unique lowercase hyphenated `id`, `shape`, `x`, `y`, and `tone`. Add
  `visible: false` for a hidden initial mark. Tones are `ink`, `paper`,
  `amber`, `rose`, `mint`, `blue`, and `violet`. Use `ink` text on
  light surfaces and `paper` text on dark surfaces. Use direct labels or
  a clear spatial distinction wherever color conveys meaning.
- `choices` contains 2–4 selectable inputs. Each choice has a unique `id`,
  a distinct `label` up to 48 characters, and 2–8 `frames`. Make the
  different inputs produce distinct visible outcomes. Each frame contains
  `caption` (up to 350 characters, including the visible state for screen
  readers), one to eight `evidence_ids`, and `changes`. The first frame can
  use an empty changes object to show the default layout.

| Shape | Additional fields |
| --- | --- |
| `sprite` | `asset` is a lowercase artwork ID, with `w` and `h` for its bounding box. The image fits inside the box without distortion. Supply `tone: "ink"` to use the shared mark shape. |
| `rect`, `ellipse` | `w`, `h` for the bounding box from `x`, `y` |
| `polyline`, `polygon` | `points` as 2–24 ordered `[dx, dy]` offsets from `x`, `y`. Polygons need at least 3. Coordinates must stay on the board. |
| `curve` | Exactly four `[dx, dy]` offsets for the start, two cubic Bézier control points, and the end. All four must fit on the board. |
| `trace` | `commands` contains 2–64 commands. Begin with `["M",dx,dy]` and continue with `["L",dx,dy]`, `["Q",cx,cy,dx,dy]`, or `["C",c1x,c1y,c2x,c2y,dx,dy]`. Coordinates are offsets from the mark origin. Optional `reveal` gives the visible percentage of the stroke from 0 to 100 and defaults to 100. |
| `text` | `text` up to 38 characters and `size` (`small` 12, `body` 14, `large` 22). `x`, `y` position the top-left. Optional `align` (`start`, `middle`, `end`) anchors the text horizontally at `x`. Optional `font` is `sans` or `mono`. Check that the labels fit on a phone. |

Drawing marks also accept optional `finish` (`solid`, `outline`, `dashed`,
`muted`). Existing marks default to `solid`. Use fixed-width text when
character positions or column alignment carry meaning.

Each `changes` object maps mark IDs to changed fields. For example,
`{"marker":{"x":150,"y":40},"result":{"text":"3 lines","visible":true}}`
moves a marker and shows a new result. Supported changes are `x`, `y`,
`tone`, `visible`, plus `w` and `h` for boxes and ellipses, and `text` for
text marks. Drawing marks can change `finish` at arrival, and a trace can change
`reveal` over the course of the transition. Use a reveal when following the stroke
helps interpret the outcome. Changes are relative to `objects` independently for every frame.
Retain the changed fields in subsequent frames where they should persist.
Playback interpolates movement, resizing, and visibility. Text and tones
update at arrival. Step works with reduced motion. These are source-backed
scenarios with defined outputs. Limit the lesson's claims to those scenarios.

When reviewing, step through each choice. Check that the outcome stays
readable, motion tracks the source behavior, and captions and evidence
explain the visible change.

## Illustrated objects and depth

Use depth when handling or positioning recognizable objects makes the concept
easier to follow. First decide what a reader should notice in a still frame,
then give the important object a clear trajectory. Compose from a few purposeful
layers such as a base, a face, and a label or detail. Use changes in depth and
placement to show where an object came from and where it ends up. Use a chart,
text comparison, or simpler drawing when that communicates the behavior better.

- On `rect`, `ellipse`, and `polygon`, optional `material` is `paper` (softly
  lit) or `enamel` (brighter highlights). Add `depth` from 0 to 12 for a visible
  edge below the face. The renderer provides surface lighting and shadows.
  Outline and dashed states display without the material.
- Any mark can use optional `lift` (0–32 units above its current position),
  `tilt` (−30–30 degrees about its own origin), or `scale_y` (20–100 percent
  of its height about its own origin). These fields can change in a frame.
  A short tilt or a change in height can show a turn or fold.
- Set optional `arc` from 0 to 24 on a moving mark to raise it halfway
  through a change of position. It lands at its new position by the end of
  the frame. Give any attached label the same movement delta and arc.
- The order of `objects` determines which marks cover others through
  playback. Leave breathing room for shadows and moving marks, and review
  the composition at phone width. Depth and timing are illustrative unless
  the repository actually establishes them.


## Generated pieces

When recognizable objects carry the explanation, create original, transparent
illustrations with the session’s built-in image tool if available. Give related
pieces one viewpoint, palette, light direction, and texture. A sheet with
generous transparent gutters can keep the art consistent in one generation.
Crop each piece to its own PNG and save it in `OUTPUT_DIR/artwork/<asset>.png`.
Use up to twenty static transparent PNGs, at most 750 KiB each and 4 MiB total.
Image edges may be up to 1600 pixels. The report embeds the used pieces.

Sketch the starting and ending composition before writing poses. Give each
moving object a stable mark ID and use the same asset when it travels. Label the
state or outcome where a person should look. Write captions that describe
the visible change and cite the source supporting it. Use the existing vector
marks for labels, counts, highlights, and other state indicators. If only an
image is useful, keep it still. If the session lacks image generation, use
vector marks or another fitting lesson format.

Use `scale_x` (20–150 percent) with `tilt` to stretch a shape along its own axis, such as a connector that stays pinned at one end. Check the entire range in the browser.

For a rectangular, ellipse, or sprite object, an optional `pivot: [x, y]`
sets the local center of rotation and scale. Use this for working hinges
or centered wheels. Its coordinates must stay within the object’s bounds
throughout the scene. An optional `inscription` (up to 24 characters) prints
a short live label centered on that object and follows its pose. Design a
clear surface space for it. Put moving pieces between back and front
layers in the `objects` order. Preview the overlap throughout the action.
