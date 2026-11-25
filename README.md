# RepoLens

RepoLens turns a GitHub repository into one offline HTML file. See where to
start reading, follow real import connections, and open the source lines
behind the report.

## Try it

Requires Python 3.10+ and Git. From the RepoLens folder:

```bash
python -m pip install -e '.[imports]'
python -m repolens build https://github.com/pallets/flask --no-ai --out report.html
```

Double-click `report.html` and select an import connection to see its source
excerpt. The page works offline. GitHub links use the scanned commit and open
when you have internet access.

`--no-ai` runs on measured facts and needs no API key. For draft explanations,
set `GEMINI_API_KEY` locally and replace `--no-ai` with `--provider gemini`.
For Claude, install `.[imports,writer]`, set `ANTHROPIC_API_KEY`, and use
`--provider claude --model <model-id>`. Add `--history` for Git change
context. GitHub checkouts are cached between runs.

## Verification

Five live Gemini reports covered itsdangerous, Click, slash, Flask, and
p-limit. All 15 sampled factual claims matched their cited code. The six
other accepted claims were labeled interpretations. Tests also exercise
invented claims, missing evidence, and the offline HTML build.

The map shows static imports. Some imports cannot be resolved, and a repo
without a confirmed entry point can have a reading guide without a path
to play.

## Development preview

From the project root, install the frontend dependencies once and generate
the Click report that Vite uses:

```bash
npm --prefix web install
mkdir -p .repolens-cache/preview
.venv/bin/python -m repolens build https://github.com/pallets/click --no-ai --out .repolens-cache/preview/click.html
npm --prefix web run dev -- --host 127.0.0.1
```

Open the local URL printed by Vite, usually `http://127.0.0.1:5173`. Vite
updates frontend edits and reloads when the generated report file changes.
After changing Python code, rerun the report command in another terminal.
After editing frontend source, run `npm --prefix web run build` before
regenerating the standalone HTML so the template passes the freshness check.
Open the standalone report directly on macOS with
`open .repolens-cache/preview/click.html`.

To inspect the source relationships:

```bash
.venv/bin/python -m repolens structure https://github.com/pallets/click --out .repolens-cache/preview/click-structure.json
```

The browser workflow runs the same offline check in Chromium and Firefox.
To run it locally in an environment with browser support:

```bash
.venv/bin/python -m pip install 'playwright==1.64.1'
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/browser_check.py --browser chromium
```

### Print Studio design preview

Start the existing Vite server from the project root:

```bash
npm --prefix web run dev -- --host 127.0.0.1 --port 5187 --strictPort
```

Open `http://127.0.0.1:5187/print-studio`. The illustrations, walkthrough
and playground update as you edit the frontend. To load the optional
developer tools, generate the matching report in a second terminal:

```bash
npm --prefix web run build
mkdir -p .repolens-cache/preview
.venv/bin/python -m repolens build https://github.com/sindresorhus/p-limit --no-ai --out .repolens-cache/preview/p-limit.html
```

The source report must match commit
`a8a6fbec4e0e866d6d779b10889bb4f5567e70eb`. The evidence links in the
prototype always target that revision.

The print-shop copy and staged lesson are hand-authored in
`web/src/print-studio/scene.ts`. The simulator in
`web/src/print-studio/simulation.ts` uses illustrative job durations.
It does not run repository code or produce benchmark results.

Run the simulator tests with Node 24:

```bash
node --test web/tests/print-simulation.test.mjs
```

To make an offline Print Studio preview after generating the p-limit report:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
preview = Path(".repolens-cache/preview")
report = (preview / "p-limit.html").read_text(encoding="utf-8")
(preview / "print-studio.html").write_text(
    report.replace('<html lang="en">', '<html lang="en" data-repolens-prototype="print-studio">', 1),
    encoding="utf-8",
)
PY
open .repolens-cache/preview/print-studio.html
```

With Playwright and Chromium installed, run the offline interaction check:

```bash
.venv/bin/python tests/browser_check.py --browser chromium --studio-report .repolens-cache/preview/print-studio.html
```
