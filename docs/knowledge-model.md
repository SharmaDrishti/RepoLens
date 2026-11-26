# Repository knowledge v1

`build <source> --no-ai --out report.html --knowledge-out knowledge.json` writes
the versioned data embedded in the page. `context <source> --out <directory>`
uses the same snapshot and context reader and exports the three original
review files. Stories and provider responses are not repository knowledge.

| Key | Contents |
| --- | --- |
| `schema_version` | Integer `1`. |
| `snapshot` | Snapshot ID, source, repository, commit metadata, working-tree and cache status, scanned files, language lines, manifests, documentation and configuration paths, and skipped-file counts. |
| `context.purpose` | Purpose, audience, problem, category, glossary terms, and source diagnostics. |
| `context.use_cases` | Labeled interpretations with cited evidence. |
| `context.getting_started` | Requirements, install, first run or examples, expected output, entry declarations, notes, and conflict diagnostics. |
| `relationships` | Static imports, unresolved imports, and declared hook configuration relationships. |
| `developer` | Entry declarations with scope, import edge IDs, static reading path, recommendations, parser diagnostics, and optional Git history. |
| `metrics` | Counts and language line totals for the scanned inventory. |
| `evidence` | Records keyed by ID, with a type, snapshot ID, path, inclusive line range, exact excerpt, scoped location, optional pinned URL, and limits. |
| `limitations` | Coverage, provenance, and verification limits for the run. |

Illustrative fragment:

```json
{
  "schema_version": 1,
  "snapshot": {
    "id": "snapshot:<digest>",
    "working_tree": "unversioned",
    "content": "working_tree",
    "cache": {"mode": "local", "remote_freshness": "not_applicable"}
  },
  "context": {
    "getting_started": {
      "install": {
        "status": "known",
        "items": [{"kind": "command", "text": "pip install sample", "evidence_ids": ["get:001"]}]
      }
    }
  },
  "evidence": {
    "get:001": {
      "id": "get:001",
      "type": "documentation",
      "snapshot_id": "snapshot:<digest>",
      "path": "README.md",
      "line": 5,
      "end_line": 5,
      "excerpt": "$ pip install sample",
      "url": null,
      "scope": {"kind": "repository", "path": "."},
      "limitations": ["Documented content or a source excerpt; this does not establish runtime behavior."]
    }
  }
}
```

A clean Git checkout is analyzed with source reads checked against the commit.
A dirty or unversioned checkout uses captured file contents and supplies no
commit-pinned citations. The HEAD value can still identify the Git baseline.
Remote freshness is unchecked even on cache reuse. Recorded import links
describe static relations; the tour represents a reading order. Example and
test entry scopes belong to their declaring folders. Evidence IDs used by
the existing readers are preserved within an analysis. They are not promised
to remain stable across changed snapshots or extractor versions.

This version validates structure, evidence references, provenance, and line
ranges. The checked excerpts are read from the scanned source. It cannot
verify the meaning of arbitrary prose or that an import order executes at
runtime. Evidence types reserved for later readers do not imply that those
readers exist.

## Checkpoint 2A source inspection

`repolens structure <source> --out structure.json` exports an independent
schema-version-1 inspection document. It shares the existing repository
snapshot and reuses the Tree-sitter trees from the import pipeline. It is
separate from the knowledge document embedded in HTML.

| Record | Fields |
| --- | --- |
| Entity | `id`, `kind`, `name`, `parent`, `scope`, `location`. Definition IDs use the lexical parent, kind, name, and occurrence within the scope. |
| Relationship | `id`, `subject`, `object`, `type`, `target_text`, `location`, `evidence_ids`, `scope`, `conditions`, `resolution`, `classification`, `limitations`. The subject-to-object direction is explicit. |
| Evidence | `id`, `snapshot_id`, `type`, `location`, `excerpt`, `url`. The excerpt includes the exact source lines in the inclusive location. |

The extractor emits definitions, imports, written calls, returns, raises,
decorator syntax, and scoped configuration declarations. Bare calls may
link to a unique same-module candidate when no conflicting references are
found. Receiver calls, imported bindings, and dynamic dispatch remain
unresolved. Files with syntax errors retain import diagnostics and are
excluded from symbol and call extraction. A branch context records the
syntactic region and expression.
It does not model control-flow dominance or establish an execution sequence.
The export validator checks references, direction of declarations, and
evidence type, location, and snapshot consistency. Behavioral assertion
verification and purpose-guided mechanism discovery are later checkpoints.
