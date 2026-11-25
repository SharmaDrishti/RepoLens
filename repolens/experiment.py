"""Check bounded, source-backed experiments where readers combine filters."""

from .illustration import check_fields, check_id, check_list, check_text, checked_frame, drawing_objects, require


def experiment_references(lesson):
    check_fields(lesson, {"id", "after", "kind", "title", "prompt", "explanation",
                          "height", "objects", "groups", "items", "evidence_ids"})
    check_text(lesson["explanation"], 350)
    objects, height = drawing_objects(lesson)
    initial = checked_frame({}, objects, height)
    groups, labels = {}, set()
    for group in check_list(lesson["groups"], 2, 4):
        check_fields(group, {"id", "label"})
        check_id(group["id"], groups)
        check_text(group["label"], 32)
        require(group["label"] not in labels, "give filter groups distinct labels")
        labels.add(group["label"])
        groups[group["id"]] = set()

    items, owned_marks, owned_labels = set(), set(), set()
    for item in check_list(lesson["items"], 3, 8):
        check_fields(item, {"id", "label", "values", "hidden"})
        check_id(item["id"], items)
        items.add(item["id"])
        check_text(item["label"], 44)
        require(item["label"] not in owned_labels, "give records distinct labels")
        owned_labels.add(item["label"])
        require(isinstance(item["values"], dict) and item["values"].keys() == groups.keys(),
                "each record needs a value for every filter group")
        for group, value in item["values"].items():
            check_text(value, 36)
            groups[group].add(value)

        hidden = item["hidden"]
        require(isinstance(hidden, dict) and hidden and not hidden.keys() & owned_marks,
                "positions must move unique marks for each record")
        owned_marks.update(hidden)
        require(checked_frame(hidden, objects, height) != initial,
                "a hidden record must look different on the stage")

    require(all(2 <= len(values) <= 6 for values in groups.values()),
            "use two to six distinct values in every filter group")
    return check_list(lesson["evidence_ids"], 1, 8)
