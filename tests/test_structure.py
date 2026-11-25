import json

import pytest

from repolens.snapshot import open_snapshot
from repolens.scanner import ScanError
from repolens.structure import structure_from_snapshot, validate_structure


def extract(root, content):
    for name, text in content.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return structure_from_snapshot(open_snapshot(str(root), root / "structure.json", root / "cache"))


def calls(data):
    return [item for item in data["relationships"] if item["type"] == "calls"]


def test_python_definitions_direct_call_direction_and_branches(tmp_path):
    data = extract(tmp_path, {"example.py": """def send():
    return True

class Worker:
    def run(self, active, obj):
        if active:
            return send()
        else:
            return obj.send()
"""})
    entities = data["entities"]
    send = next(item for item in entities.values() if item["name"] == "send")
    worker = next(item for item in entities.values() if item["name"] == "Worker")
    run = next(item for item in entities.values() if item["name"] == "run")
    assert worker["kind"] == "class" and run["kind"] == "method" and run["parent"] == worker["id"]
    direct, dynamic = calls(data)
    assert (direct["subject"], direct["object"], direct["resolution"]) == (run["id"], send["id"], "static_candidate")
    assert direct["conditions"] == [{"kind": "branch", "region": "consequence", "line": 6, "expression": "active"}]
    assert dynamic["subject"] == run["id"] and dynamic["object"] is None
    assert dynamic["resolution"] == "unresolved"
    assert dynamic["target_text"] == "obj.send"
    assert dynamic["conditions"][0]["region"] == "alternative"
    assert data["evidence"][direct["evidence_ids"][0]]["excerpt"] == "            return send()"
    assert data["evidence"][direct["evidence_ids"][0]]["snapshot_id"] == data["snapshot"]["id"]
    assert all("order" not in item for item in data["relationships"])


def test_python_shadowing_and_decorator_syntax(tmp_path):
    data = extract(tmp_path, {"examples/demo.py": """def callback():
    return 1

@registry.handler
def run(callback):
    callback()
    raise ValueError()
"""})
    (local,) = [item for item in calls(data) if item["target_text"] == "callback"]
    assert local["object"] is None
    decorator, = (item for item in data["relationships"] if item["type"] == "declares_decorator")
    assert decorator["target_text"] == "@registry.handler"
    assert decorator["scope"] == {"kind": "example", "path": "examples"}
    assert decorator["object"] is None
    assert any(item["type"] == "raises" for item in data["relationships"])


@pytest.mark.parametrize("extension", [".js", ".ts"])
def test_javascript_and_typescript_symbols_and_unresolved_receiver(tmp_path, extension):
    data = extract(tmp_path, {"worker" + extension: """function finish() {
  return true;
}
class Worker {
  run(active, queue) {
    if (active) {
      return finish();
    }
    queue.push(1);
  }
}
const deferred = () => 2;
"""})
    entities = data["entities"]
    direct, dynamic = calls(data)
    assert entities[direct["object"]]["name"] == "finish"
    assert entities[direct["subject"]]["kind"] == "method"
    assert direct["conditions"][0]["region"] == "consequence"
    assert dynamic["object"] is None and dynamic["target_text"] == "queue.push"
    assert any(item["name"] == "deferred" and item["kind"] == "function" for item in entities.values())


def test_reused_import_and_configuration_have_distinct_evidence(tmp_path):
    hook = {"hooks": {"UserPromptSubmit": [{"hooks": [
        {"type": "command", "command": "python3 helper.py record"},
    ]}]}}
    data = extract(tmp_path, {
        "main.py": "import helper\n", "helper.py": "def run():\n    pass\n",
        "hooks.snippet.json": json.dumps(hook),
    })
    imports, config = [item for item in data["relationships"] if item["type"] in {"imports", "declares_hook"}]
    assert imports["id"] == "imp:0001"
    assert (imports["subject"], imports["object"]) == ("file:main.py", "file:helper.py")
    assert data["evidence"][imports["evidence_ids"][0]]["type"] == "import_relationship"
    assert config["object"] == "file:helper.py"
    assert config["scope"] == {"kind": "hook_template", "path": "hooks.snippet.json"}
    assert data["evidence"][config["evidence_ids"][0]]["type"] == "configuration"


def test_structure_is_repeatable_for_one_snapshot(tmp_path):
    first = extract(tmp_path, {"sample.py": "def run():\n    return 1\nrun().strip().lower()\n"})
    second = structure_from_snapshot(open_snapshot(str(tmp_path), tmp_path / "structure.json", tmp_path / "cache"))
    assert first == second
    assert len({rel["id"] for rel in first["relationships"]}) == len(first["relationships"])


def test_structure_rejects_cross_snapshot_evidence(tmp_path):
    data = extract(tmp_path, {"sample.py": "def run():\n    return 1\n"})
    next(iter(data["evidence"].values()))["snapshot_id"] = "another-snapshot"
    with pytest.raises(ScanError, match="Invalid structure evidence"):
        validate_structure(data)
