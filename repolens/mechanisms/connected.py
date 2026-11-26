"""Source-navigation hints. Never substitute these for measured call targets."""

from collections import defaultdict, deque
import re


def connected_relationships(repository, query, words, entry_points, *, depth=5, limit=22, requested=()):
    entities = repository.entities
    by_subject = defaultdict(list)
    by_name = defaultdict(list)
    imports = defaultdict(list)
    qualified = set(re.findall(r"[\w]+\.([A-Za-z_$][\w$]*)", query))
    command = set(re.findall(rf"\b{re.escape(repository.snapshot.identity['repo'])}\s+([a-z][a-z0-9_-]*)\b", query, re.I))
    command_names = {item.replace("-", "_") + "_command" for item in command}
    for relation in repository.relationships.values():
        by_subject[relation["subject"]].append(relation)
        if relation["type"] == "imports":
            imports[relation["location"]["path"]].append(relation)
    ranked = []
    for identifier, entity in entities.items():
        if entity["kind"] not in {"function", "method", "class"}:
            continue
        loc = entity["location"]
        name = entity["name"]
        path = loc["path"]
        by_name[path, name].append(identifier)
        if entity["scope"]["kind"] in {"test", "example"} or re.search(r"(^|[/_.])(?:test|bench|benchmark)[/_.]", path):
            continue
        preceding = repository.snapshot.lines(path)[max(0, loc["line"] - 2):loc["line"] - 1]
        property_name = re.search(r"([\w$]+)\s*:\s*\{\s*$", preceding[-1]) if preceding else None
        explicit = name in qualified or (property_name and property_name[1] in qualified)
        if explicit or name in command_names or name.lower() in words:
            ranked.append((0 if explicit or name in command_names else 1, identifier))
    strongest = sorted(ranked)
    roots = list(dict.fromkeys([*requested, *entry_points,
                                *(identifier for rank, identifier in strongest if rank == strongest[0][0])][:5]))
    pending = deque((identifier, 0, "entry_or_lexical_anchor") for identifier in roots)
    seen, emitted = set(), set()
    result = []
    while pending and len(result) < limit:
        identifier, distance, via = pending.popleft()
        if identifier in seen or distance > depth:
            continue
        seen.add(identifier)
        if identifier in repository.relationships:
            identifier = repository.relationships[identifier]["subject"]
        for relation in by_subject[identifier]:
            if relation["type"] in {"imports", "defines"}:
                continue
            if relation["id"] not in emitted:
                result.append((relation, distance, via))
                emitted.add(relation["id"])
            if len(result) >= limit:
                break
            if relation["type"] == "returns":
                # Follow a returned local callable for navigation only.
                returned = re.fullmatch(r"return\s+([A-Za-z_$][\w$]*)\s*;?", relation["target_text"] or "")
                if returned:
                    options = by_name[relation["location"]["path"], returned[1]]
                    if len(options) == 1 and entities[options[0]]["parent"] == identifier:
                        pending.append((options[0], distance + 1, "returned_local_name"))
            if relation["type"] != "calls":
                continue
            target = relation["object"]
            if target:
                pending.append((target, distance + 1, "measured_target"))
                continue
            # A simple same-file name or receiver is a navigation hint only.
            # Dynamic receiver dispatch and callback invocation remain unresolved.
            spelling = relation["target_text"] or ""
            receiver = re.fullmatch(r"(?:self|cls)\.([A-Za-z_$][\w$]*)", spelling)
            match = re.fullmatch(r"([A-Za-z_$][\w$]*)(?:\.(?:bind|call|apply))?", spelling)
            if not (match or receiver):
                continue
            path = relation["location"]["path"]
            name = (receiver or match)[1]
            options = by_name[path, name]
            if receiver:
                parent = entities[identifier]["parent"]
                options = [option for option in options if parent and entities[option]["parent"] == parent]
            if len(options) == 1:
                pending.append((options[0], distance + 1, "unresolved_same_file_name"))
            elif not options and spelling == name:
                imported = []
                for edge in imports[path]:
                    excerpt = repository.records[edge["evidence_ids"][0]]["excerpt"]
                    if re.search(rf"\b{re.escape(name)}\b", excerpt):
                        module = entities[edge["object"]]["location"]["path"]
                        imported.extend(by_name[module, name])
                if len(set(imported)) == 1:
                    pending.append((imported[0], distance + 1, "unresolved_import_name"))
    return result
