import json

import pytest

from repolens.reader_language import plain_is_grounded
from repolens.reader_sources import passages, validate_excerpt
from repolens.readers import collect_context, write_context


def collect(root, readme, content):
    project = root / "project"
    project.mkdir()
    (project / readme).write_text(content, encoding="utf-8")
    return collect_context(str(project), root / "out", root / "cache")


def test_markdown_badges_html_and_multiline_commands(tmp_path):
    results = collect(tmp_path, "README.md", r"""# Sample
[![build](badge.svg)](https://example.invalid)
<div><img src="logo.svg"></div>

<p>Sample is a Python package for building websites with as little code as necessary.</p>

## Install
```sh
$ pip install sample \
  --no-deps
```

## Quickstart
```python
from sample import render

render("<div>hello</div>")
```

```console
$ python hello.py
Hello!
```
""")
    purpose = results["purpose.json"]
    assert purpose["readmes"][0]["status"] == "supported"
    assert purpose["what_it_is"]["text"].startswith("Sample is a Python package")
    assert purpose["evidence"][0]["line"] == 5
    assert purpose["who_uses_it"]["items"][0]["plain"]["kind"] == "INTERPRETATION"
    getting = results["getstarted.json"]
    assert getting["install"]["items"][0]["text"] == "pip install sample \\\n  --no-deps"
    assert getting["first_run"]["items"][0]["text"] == 'from sample import render\n\nrender("<div>hello</div>")'
    assert getting["first_run"]["items"][1]["text"] == "python hello.py"
    assert getting["expected_output"]["items"][0]["text"] == "Hello!"


@pytest.mark.parametrize("readme", ["README.rst", "README.txt", "README"])
def test_plain_and_rst_readmes(tmp_path, readme):
    body = "Sample\n======\n\nSample is a command line utility for reading files from a folder.\n"
    if readme.endswith(".rst"):
        body += "\nInstall\n-------\n\n.. code-block:: console\n\n   $ pip install sample\n"
    else:
        body += "\nInstall\n\n$ pip install sample\n"
    results = collect(tmp_path, readme, body)
    assert results["purpose.json"]["category"]["value"] == "cli tool"
    assert results["getstarted.json"]["install"]["items"][0]["text"] == "pip install sample"


def test_non_english_readme_falls_back_to_manifest(tmp_path):
    (tmp_path / "README.md").write_text("Esta herramienta convierte archivos de datos para los usuarios. "
                                      "También permite transformar los registros en otros formatos.", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\ndescription = "A library for reading data files."\n')
    results = collect_context(str(tmp_path), tmp_path / "out", tmp_path / "cache")
    purpose = results["purpose.json"]
    assert purpose["readmes"] == [{"source": "README.md", "status": "unsupported_language"}]
    assert purpose["evidence"][0]["source"] == "pyproject.toml"
    assert results["getstarted.json"]["install"]["status"] == "not_documented"


def test_conflicting_identity_and_requirements_are_unknown(tmp_path):
    (tmp_path / "README.md").write_text("Project is a web application framework for building websites.\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndescription = "A data pipeline for reading files."\nrequires-python = ">=3.11"\n'
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "installation.rst").write_text("Project supports Python 3.9 and newer.\n")
    results = collect_context(str(tmp_path), tmp_path / "out", tmp_path / "cache")
    purpose = results["purpose.json"]
    assert purpose["what_it_is"]["text"] == "unknown"
    assert len(purpose["conflicts"][0]["evidence_ids"]) == 2
    assert results["getstarted.json"]["requirements"]["status"] == "unknown"
    assert len(results["getstarted.json"]["conflicts"][0]["evidence_ids"]) == 2


def test_plain_candidate_cannot_invent_names_or_use_unrelated_citation():
    excerpt = "Flask is a Python web application framework for developers."
    assert plain_is_grounded("A tool for building websites with Python.", [excerpt])
    assert not plain_is_grounded("It trains a model on pictures.", [excerpt])
    assert not plain_is_grounded("Django is a tool for building websites.", [excerpt])
    assert not plain_is_grounded("The helper.py file helps build websites.", [excerpt])
    assert not plain_is_grounded("Use route() for building websites.", [excerpt])


def test_wrong_line_is_rejected():
    lines = ["# Title", "A library for reading files."]
    passage, = list(passages("README.md", lines))
    record = passage.evidence("pur:001", {})
    assert validate_excerpt(record, lines)
    assert not validate_excerpt({**record, "line": 1}, lines)
    assert not validate_excerpt({**record, "text": "Made-up text"}, lines)


def test_empty_documentation_writes_three_review_files(tmp_path):
    (tmp_path / "README").write_text("Hello World!\n")
    output = tmp_path / "out"
    write_context(str(tmp_path), output, tmp_path / "cache")
    assert {path.name for path in output.iterdir()} == {"purpose.json", "usecases.json", "getstarted.json"}
    purpose = json.loads((output / "purpose.json").read_text())
    assert purpose["what_it_is"]["text"] == "unknown"
