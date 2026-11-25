"""Validate multi-chapter lessons and collect their pinned citations."""

from .illustration import (
    bounded_int, check_fields, check_id, check_list, check_motion_cues, check_text, checked_frame, drawing_objects, require,
)


def guide_references(guide):
    check_fields(guide, {"title", "prompt", "chapters"})
    check_text(guide["title"], 100)
    check_text(guide["prompt"], 240)
    refs, ids = set(), set()
    steps = 0
    for chapter in check_list(guide["chapters"], 1, 3):
        check_fields(chapter, {"id", "title", "height", "objects", "frames"})
        check_id(chapter["id"], ids)
        ids.add(chapter["id"])
        check_text(chapter["title"], 64)
        objects, height = drawing_objects(chapter)
        previous = None
        base = None
        frames = check_list(chapter["frames"], 2, 6)
        steps += len(frames)
        require(steps <= 6, "the entire guided lesson may have at most six steps")
        for frame in frames:
            optional = {"motion_ms", "callout", "cues"} & frame.keys() if isinstance(frame, dict) else set()
            check_fields(frame, {"caption", "changes", "evidence_ids", "duration_ms"} | optional)
            check_text(frame["caption"], 350)
            require(bounded_int(frame["duration_ms"], 2500, 16000), "guided step duration must be 2500–16000 ms")
            if "motion_ms" in frame:
                require(previous is not None and
                        bounded_int(frame["motion_ms"], 500, frame["duration_ms"] - 1200),
                        "set motion_ms on later frames and leave at least 1200 ms to read the result")
            if "callout" in frame:
                callout = frame["callout"]
                check_fields(callout, {"text", "x", "y"})
                check_text(callout["text"], 32)
                require(bounded_int(callout["x"], 12, 88) and bounded_int(callout["y"], 12, 88),
                        "position the callout within 12–88 percent of the stage")
            for ref in check_list(frame["evidence_ids"], 1, 8):
                check_text(ref, 300)
                refs.add(ref)
            visible = checked_frame(frame["changes"], objects, height)
            if "cues" in frame:
                require(base is not None and "motion_ms" in frame, "motion cues need a preceding pose and motion_ms")
                check_motion_cues(frame["cues"], base, objects, height)
            require(visible != previous, "each guided step needs a visible change")
            previous = visible
            base = frame["changes"]
    return refs
