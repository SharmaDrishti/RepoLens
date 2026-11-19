# RepoLens

RepoLens is a command-line tool that turns a GitHub repository into one
animated HTML page. The page explains what the project does, how its parts
connect, and which files a newcomer should read first.

## How it earns trust

- **Measured facts.** Code scans the repository and extracts import
  connections and Git history. The AI writes explanations using those facts.
- **Evidence.** The checker verifies factual claims against the measured data.
  The report labels interpretations and shows the evidence behind each one.
  Links use a specific commit when available.
- **Scale.** The scanner and other readers handle the repository. The AI
  receives a smaller file of relevant facts.
- **History.** Frequently changed files and files that change together provide
  context for the reading path. Each recommended file gets a plain-language
  reason.

## First demo

A developer who has never seen the repository should be able to find its
entry point and trace one important flow in five minutes.

## Roadmap

1. Scan a GitHub repository or local folder for files, languages, Git details,
   and project manifests.
2. Read import connections with Tree-sitter.
3. Read Git history for frequently changed files and files that change together.
4. Rank files and give a reason for each reading recommendation.
5. Generate explanations that label facts and interpretations.
6. Check factual claims against the measured data.
7. Build a single animated HTML report with React and Vite.

Phases 1 through 4 are committed. Phase 5 has been verified and is awaiting commit.

To add history to the facts report, run
`python -m repolens imports <source> --history --out facts.json`.
The default window is 200 commits along the scanned commit's first-parent chain.
`--history-depth N` selects a different window. A pair's strength is the share
of commits that touched both files among commits that touched either file.
Commits touching more than 100 scanned files are excluded from pair scoring
and still count toward individual file totals. History supplies context for
the report.

Add `--rank` to `imports` to include a reading guide in `facts.json`.
The guide recommends up to five files and records one path of up to four
resolved imports from a confirmed entry point, when available. The path
describes static import connections. Git history can add a change note to
a recommended file without affecting its rank.

To write a report, install `.[writer]`, export `ANTHROPIC_API_KEY`, and run
`python -m repolens report facts.json --model <claude-model> --out report.json`.
The writer receives up to 40 measured facts, with import-path and recommendation
evidence first. The checker accepts factual wording only when it matches a
measured fact exactly. Interpretations keep their label and attached evidence.
Rejected claims get one retry, and the report logs rejections. The checker
requires pinned evidence files to match the scanned commit on disk.

For public-repository evaluation, Gemini is also available through the same
checker. Export `GEMINI_API_KEY` from Google AI Studio and run
`python -m repolens report facts.json --provider gemini --out report.json`.
The Gemini default is `gemini-3.1-flash-lite`; use `--model` to override it.

The Phase 5 live Gemini review covered itsdangerous (`672971d`), Click
(`08b803c`), slash (`2e8a56b`), Flask (`49943b5`), and p-limit (`a8a6fbe`).
The saved reports contained 15 factual claims and six labeled interpretations.
The factual claims matched the cited source. These runs logged no rejections.
Separate tests exercise invented claims and invalid evidence.
