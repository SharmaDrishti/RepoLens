# RepoLens

Current phase: Automatic explain MVP awaiting credentialed generation and browser review

RepoLens helps developers understand an unfamiliar repository. Code measures
facts and AI explains them using evidence. Keep each phase scoped to its task.

- Use Python 3.10+ and the standard library for the scanner. Use pytest for tests.
- Record the scanned commit when available so future reports can link to that version.
- In later phases, verify structured claims against measured facts and explain
  why each file is recommended. Wait for authorization before starting the next phase.
- Explain new files and their roles in plain language.

Read the owner's RepoLens master brief and PROJECT_BRIEF.md at the start of every
session. The master brief takes precedence. Show a plan and wait for approval
before each implementation step.
