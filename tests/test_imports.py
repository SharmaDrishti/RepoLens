import json
import subprocess
import sys

from repolens.imports import Import, read_imports, resolve_js, resolve_python


def write_files(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_resolvers_decline_ambiguous_targets():
    item = Import("app", 1, "import")
    assert resolve_python("run.py", item, {"app.py", "src/app.py"}) == {"app.py", "src/app.py"}

    item = Import("./util", 1, "import")
    assert resolve_js("main.ts", item, {"util.ts", "util/index.ts"}, {}) == {"util.ts", "util/index.ts"}


def test_imports_reads_python_javascript_and_typescript(tmp_path):
    write_files(tmp_path, {
        "src/app/__init__.py": "",
        "src/app/__main__.py": (
            "from . import logic\nfrom .logic import run\nimport external\n"
            'if __name__ == "__main__":\n    run()\n'
        ),
        "src/app/logic.py": "def run():\n    pass\n",
        "pyproject.toml": '[project.scripts]\napp = "app.logic:run"\n',
        "web/package.json": '{"bin": {"web": "./main.js"}, "main": "./util/index.js"}',
        "web/main.js": 'import "./util";\nexport { run } from "./util/index.js";\n',
        "web/util/index.js": "export function run() {}\n",
        "web/main.ts": 'import "@lib/helper";\nimport "./util/index.js";\nimport(variable);\n',
        "web/tsconfig.json": '{ // alias\n "compilerOptions": {"paths": {"@lib/*": ["./lib/*"]}},\n}',
        "web/lib/helper.tsx": "export const helper = <div />;\n",
        "web/node_modules/ignored/index.js": 'import "ignored";',
    })
    report = read_imports(str(tmp_path), tmp_path / "facts.json", tmp_path / "cache")

    assert {(edge["from"], edge["to"], edge["line"]) for edge in report["edges"]} == {
        ("src/app/__main__.py", "src/app/logic.py", 1),
        ("src/app/__main__.py", "src/app/logic.py", 2),
        ("web/main.js", "web/util/index.js", 1),
        ("web/main.js", "web/util/index.js", 2),
        ("web/main.ts", "web/lib/helper.tsx", 1),
        ("web/main.ts", "web/util/index.js", 2),
    }
    assert len({edge["id"] for edge in report["edges"]}) == len(report["edges"])
    assert {item["specifier"] for item in report["unresolved_imports"]} == {"external", "import(variable)"}
    assert {(item["kind"], item["path"]) for item in report["entry_points"]} == {
        ("python_main_module", "src/app/__main__.py"),
        ("python_main_guard", "src/app/__main__.py"),
        ("project_script", "src/app/logic.py"),
        ("package_json", "web/main.js"),
        ("package_json", "web/util/index.js"),
    }
    assert report["diagnostics"] == []


def test_imports_cli_writes_facts(tmp_path):
    write_files(tmp_path, {"main.py": "import helper\n", "helper.py": "pass\n"})
    output = tmp_path / "facts.json"
    result = subprocess.run(
        [sys.executable, "-m", "repolens", "imports", str(tmp_path), "--out", str(output)],
        capture_output=True, text=True, check=True,
    )
    assert "1 import edges" in result.stdout
    assert json.loads(output.read_text())["edges"][0]["to"] == "helper.py"
