"""Extract line-numbered prose and literal blocks from repository sources."""

from dataclasses import dataclass
import html
from pathlib import Path
import re

from .checker import source_lines, source_url

READMES = {"readme", "readme.md", "readme.rst", "readme.txt"}
DOC_TYPES = {".md", ".rst", ".txt"}
FENCE = re.compile(r"^\s*([~\x60]{3,})(.*)$")
DIRECTIVE = re.compile(r"^\s*\.\. (?:code-block|code|sourcecode)::\s*(\S*)")
UNDERLINE = re.compile(r"^[=\-~^]{3,}$")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
LIST_ITEM = re.compile(r"^\s*(?:[-*+] |\d+[.)]\s+)")
ENGLISH_MARKERS = set("a an and are as at be by can for from how in is it of on or that the this to use was we what when which will with you your".split())


@dataclass(frozen=True)
class Passage:
    path: str
    line: int
    raw: tuple[str, ...]
    text: str
    section: str = ""
    language: str | None = None

    def evidence(self, identifier: str, commit: dict) -> dict:
        end = self.line + len(self.raw) - 1
        return {
            "id": identifier, "source": self.path, "line": self.line, "end_line": end,
            "text": "\n".join(self.raw), "url": source_url(commit, self.path, self.line, end),
        }


def exact_passage(path: str, lines: list[str], index: int, count: int = 1) -> Passage:
    raw = tuple(lines[index:index + count])
    return Passage(path, index + 1, raw, "\n".join(raw))


def clean_prose(text: str) -> str:
    text = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r":\w+:" + r"\x60([^\x60]+)\x60", r"\1", text)
    return " ".join(html.unescape(text).replace("\x60", "").replace("**", "").split())


def prose_line(line: str) -> bool:
    s = line.strip()
    if s.startswith("<"):
        return bool(re.match(r"<p(?:\s[^>]*)?>", s, re.IGNORECASE) and clean_prose(s))
    return bool(s and not s.startswith((".. ", "|", "{.", "![", "[!["))
                and not re.match(r"^\[[^]]+\]:", s))


def passages(path: str, lines: list[str]):
    """Keep exact raw ranges, including indentation and blank lines inside code."""
    section = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        fence = FENCE.match(line)
        directive = DIRECTIVE.match(line)
        if fence:
            end = index + 1
            while end < len(lines) and not re.fullmatch(
                r"\s*" + re.escape(fence[1][0]) + "{" + str(len(fence[1])) + r",}\s*", lines[end]
            ):
                end += 1
            if end < len(lines) and end > index + 1:
                raw = tuple(lines[index + 1:end])
                yield Passage(path, index + 2, raw, "\n".join(raw), section, fence[2].strip().lower())
            index = end + 1
            continue
        if directive:
            start = index + 1
            while start < len(lines) and (not lines[start].strip() or lines[start].lstrip().startswith(":")):
                start += 1
            indent = len(line) - len(line.lstrip())
            end = start
            while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent):
                end += 1
            while end > start and not lines[end - 1].strip():
                end -= 1
            if end > start:
                raw = tuple(lines[start:end])
                yield Passage(path, start + 1, raw, "\n".join(raw), section, directive[1].lower())
            index = max(index + 1, end)
            continue
        if stripped.startswith("#"):
            section = stripped.lstrip("# ").strip()
            index += 1
            continue
        if stripped.lower().rstrip(":") in {"installation", "install", "quickstart", "getting started", "usage"}:
            section = stripped.rstrip(":")
            index += 1
            continue
        if stripped and index + 1 < len(lines) and UNDERLINE.fullmatch(lines[index + 1].strip()):
            section = stripped
            index += 2
            continue
        if stripped.startswith("$ "):
            start = index
            index += 1
            while index < len(lines) and lines[index - 1].rstrip().endswith("\\"):
                index += 1
            raw = tuple(lines[start:index])
            yield Passage(path, start + 1, raw, "\n".join(raw), section, "console")
            continue
        if not prose_line(line):
            index += 1
            continue
        start = index
        index += 1
        is_list = LIST_ITEM.match(line)
        while not is_list and index < len(lines):
            next_line = lines[index]
            if (not prose_line(next_line) or FENCE.match(next_line)
                    or next_line.lstrip().startswith(("#", "$ ")) or LIST_ITEM.match(next_line)):
                break
            if index + 1 < len(lines) and UNDERLINE.fullmatch(lines[index + 1].strip()):
                break
            index += 1
        raw = tuple(lines[start:index])
        text = clean_prose(" ".join(raw).lstrip("> "))
        if text:
            yield Passage(path, start + 1, raw, text, section)


def english_status(parts: list[Passage]) -> str:
    prose = " ".join(part.text for part in parts if part.language is None)
    words = [word.lower().strip("'") for word in WORD.findall(prose)]
    letters = [char for char in prose if char.isalpha()]
    if letters and sum(char.isascii() for char in letters) / len(letters) < .7:
        return "unsupported_language"
    markers = sum(word in ENGLISH_MARKERS for word in words)
    if len(words) >= 12 and (markers < 2 or markers / len(words) < .11):
        return "unsupported_language"
    if re.search(r"\b(?:ce logiciel|cette bibliothèque|esta ferramenta|esta herramienta|dieses werkzeug|questo strumento)\b",
                 prose, re.IGNORECASE):
        return "unsupported_language"
    return "supported" if markers >= 2 else "insufficient_prose"


def read_source(root: Path, path: str, sha: str | None) -> list[str]:
    return source_lines(root, path, sha)


def validate_excerpt(record: dict, lines: list[str]) -> bool:
    start, end = record["line"], record["end_line"]
    return (type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
            and "\n".join(lines[start - 1:end]) == record["text"])


def ordered_docs(paths: set[str]) -> list[str]:
    def priority(path: str) -> tuple:
        name = Path(path).stem.lower()
        preferred = ("index", "overview", "intro", "install", "quickstart", "getting-started", "tutorial")
        return (not any(word in name for word in preferred), path.count("/"), path)

    docs = (path for path in paths if path.lower().startswith(("docs/", "doc/"))
            and Path(path).suffix.lower() in DOC_TYPES)
    return sorted(docs, key=priority)[:40]
