from repolens.ranker import build_reading_guide


def edge(identifier, source, target):
    return {"id": identifier, "from": source, "to": target, "line": 2}


def test_guide_prefers_cli_and_follows_a_cycle_free_import_path():
    facts = {
        "edges": [edge("a", "cli.js", "core.js"), edge("b", "core.js", "helper.js"),
                  edge("c", "helper.js", "cli.js")],
        "entry_points": [
            {"path": "library.js", "kind": "package_json",
             "evidence": {"path": "package.json", "key": "main"}},
            {"path": "cli.js", "kind": "package_json",
             "evidence": {"path": "package.json", "key": "bin.tool"}},
        ],
    }
    result = build_reading_guide(facts)
    assert result["flow"]["files"] == ["cli.js", "core.js", "helper.js"]
    assert result["flow"]["edge_ids"] == ["a", "b"]
    assert [item["path"] for item in result["recommendations"]] == [
        "cli.js", "core.js", "helper.js", "library.js",
    ]
    assert all(item["reason"] and item["evidence"] for item in result["recommendations"])


def test_ranker_counts_distinct_importers_and_works_without_entry_points():
    facts = {
        "edges": [edge("a", "a.py", "shared.py"), edge("b", "a.py", "shared.py"),
                  edge("c", "b.py", "shared.py"), edge("d", "c.py", "other.py")],
        "entry_points": [{"path": None, "kind": "project_script", "evidence": {"path": "pyproject.toml"}}],
        "history": {"commits_analyzed": 1000, "files": [{"path": "other.py", "change_count": 999}]},
    }
    result = build_reading_guide(facts)
    assert result["flow"] is None
    assert result["recommendations"][0]["path"] == "shared.py"
    assert "2 repo files" in result["recommendations"][0]["reason"]
    assert result["recommendations"][0]["evidence"]["edge_id"] == "a"
    assert result["recommendations"][1]["history_note"] == "Changed in 999 of 1000 analyzed commits."


def test_empty_guide_is_explicit():
    assert build_reading_guide({"edges": [], "entry_points": []}) == {
        "recommendations": [], "flow": None,
    }
