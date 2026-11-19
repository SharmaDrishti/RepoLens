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

Phase 1 is committed. Phase 2 is waiting to start.
