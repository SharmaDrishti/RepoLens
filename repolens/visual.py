"""Validate the data used by RepoLens's composable illustration renderer."""

import re

from .scanner import ScanError


SHAPES = {"card", "pill", "circle", "stack", "gate"}
TONES = {"amber", "rose", "mint", "blue", "violet"}


def validate_visual(visual):
    """Return the cited excerpt IDs once the plan is safe and renderable."""
    def check(condition, message):
        if not condition:
            raise ScanError(f"Visual plan: {message}.")

    def fields(value, *names):
        check(isinstance(value, dict) and value.keys() == set(names),
              f"expected fields {', '.join(names)}")

    def label(value, limit=120):
        check(isinstance(value, str) and value.strip() and len(value) <= limit,
              f"labels and captions must contain 1–{limit} characters")

    def entries(value, minimum, maximum):
        check(isinstance(value, list) and minimum <= len(value) <= maximum,
              f"expected {minimum}–{maximum} entries")
        return value

    def known(value, allowed):
        return isinstance(value, str) and value in allowed

    def indexed(values):
        ids = set()
        for value in values:
            key = value.get("id") if isinstance(value, dict) else None
            check(isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,31}", key) and key not in ids,
                  "IDs must be unique lowercase names")
            ids.add(key)
        return ids

    fields(visual, "title", "prompt", "grid", "objects", "paths", "tokens", "choices")
    label(visual["title"], 70)
    label(visual["prompt"], 240)
    grid = visual["grid"]
    fields(grid, "columns", "rows")
    columns, rows = grid["columns"], grid["rows"]
    check(type(columns) is int and 2 <= columns <= 4 and type(rows) is int and 1 <= rows <= 3,
          "use two to four columns and one to three rows")

    objects = entries(visual["objects"], 2, 8)
    object_ids = indexed(objects)
    cells = set()
    for item in objects:
        fields(item, "id", "label", "shape", "tone", "column", "row")
        label(item["label"], 28)
        check(known(item["shape"], SHAPES) and known(item["tone"], TONES), "choose a supported shape and tone")
        x, y = item["column"], item["row"]
        check(type(x) is int and type(y) is int and 1 <= x <= columns and 1 <= y <= rows,
              "place each object inside the grid")
        check((x, y) not in cells, "give each object its own cell")
        cells.add((x, y))

    paths = entries(visual["paths"], 0, 10)
    path_ids = indexed(paths)
    edges = set()
    for path in paths:
        fields(path, "id", "from", "to")
        edge = path["from"], path["to"]
        check(all(known(end, object_ids) for end in edge) and edge[0] != edge[1] and edge not in edges,
              "paths must connect two distinct objects without duplicate directions")
        edges.add(edge)

    tokens = entries(visual["tokens"], 0, 4)
    token_ids = indexed(tokens)
    for token in tokens:
        fields(token, "id", "label", "tone")
        label(token["label"], 16)
        check(known(token["tone"], TONES), "choose a supported token tone")

    choices = entries(visual["choices"], 2, 4)
    indexed(choices)
    alternatives, names, refs = set(), set(), set()
    for choice in choices:
        fields(choice, "id", "label", "frames")
        label(choice["label"], 48)
        check(choice["label"] not in names, "give each choice a distinct label")
        names.add(choice["label"])
        states = []
        for frame in entries(choice["frames"], 2, 6):
            fields(frame, "caption", "evidence_ids", "values", "placements", "active", "paths")
            label(frame["caption"], 350)
            citations = entries(frame["evidence_ids"], 1, 8)
            for ref in citations:
                label(ref, 300)
            refs.update(citations)
            values, placements = frame["values"], frame["placements"]
            check(isinstance(values, dict) and values.keys() <= object_ids,
                  "frame values must name existing objects")
            for value in values.values():
                label(value, 60)
            check(isinstance(placements, dict) and placements.keys() <= token_ids
                  and all(known(target, object_ids) for target in placements.values()),
                  "place tokens on existing objects")
            active = entries(frame["active"], 0, len(object_ids))
            routes = entries(frame["paths"], 0, len(path_ids))
            check(all(known(id_, object_ids) for id_ in active) and all(known(id_, path_ids) for id_ in routes),
                  "frame highlights must refer to existing objects and paths")
            state = (tuple(sorted(values.items())), tuple(sorted(placements.items())),
                     tuple(sorted(set(active))), tuple(sorted(set(routes))))
            check(not states or state != states[-1], "consecutive frames need an observable change")
            states.append(state)
        alternatives.add(tuple(states))
    check(len(alternatives) == len(choices), "choices must show different visual states or paths")
    return refs
