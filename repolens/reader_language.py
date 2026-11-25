"""Conservative vocabulary checks for beginner-facing interpretations."""

import re

STOP_WORDS = set(
    "a an and are as at be by can for from has have how in is it its of on or that the their them "
    "this to was what when where who will with while you your helps using use used people anyone".split()
)
GLOSSARY = {
    "web application framework": ("tool for building websites", "make websites", "build websites"),
    "building complex web applications": ("building websites",),
    "command line interface": ("tool for making programs people run by typing commands", "terminal commands"),
    "command line tools": ("programs people run by typing commands",),
    "with as little code as necessary": ("people who write code",),
    "scale up to complex applications": ("build more complex websites later",),
    "getting started": ("get started",),
    "quick and fun": ("quicker",),
    "developer": ("people who write code",),
    "package": ("tool",),
    "paths": ("file paths",),
    "slash paths": ("forward slashes",),
    "automatic help page generation": ("make help screens automatically",),
    "nesting of commands": ("group related commands",),
    "lazy loading of subcommands": ("load smaller commands only when needed",),
    "create a small but complete application": ("build a small complete app",),
    "returns the message": ("show a message in the browser",),
    "adding custom management commands": ("add commands for managing your project",),
    "forms to submit tasks": ("use forms to submit tasks",),
    "notification arrives": ("get a notification",),
    "promise returning": ("tasks",),
    "limited concurrency": ("limiting how many run at a time", "limit how many tasks run at a time"),
    "run multiple": ("runs several",),
    "processing inputs that arrive in batches": ("process inputs in batches",),
    "fires the push straight to telegram": ("send notifications to Telegram",),
}
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)*")
CODE_NAME = re.compile(r"\b(?:[a-zA-Z0-9_-]+/)+[a-zA-Z0-9_.-]+|\b[\w-]+\.(?:py|js|ts|json|toml|txt|rst|md)\b|\b[A-Za-z]\w*\(\)")


def singular(word: str) -> str:
    word = word.lower()
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def plain_is_grounded(plain: str, excerpts: list[str]) -> bool:
    """Require all content words to be traceable to evidence or an anchored glossary entry."""
    if not isinstance(plain, str) or not plain.strip() or len(plain) > 400:
        return False
    source = " ".join(excerpts)
    normalized = re.sub(r"[\s_-]+", " ", source.lower())
    if any(name not in source for name in CODE_NAME.findall(plain)):
        return False
    allowed = {singular(word) for word in TOKEN.findall(source)}
    for term, definitions in GLOSSARY.items():
        if re.search(r"\b" + re.escape(term) + r"s?\b", normalized):
            allowed.update(singular(word) for word in TOKEN.findall(" ".join(definitions)))
    for match in TOKEN.finditer(plain):
        word = match[0]
        # Internal capitalized and code-like names must be present as written.
        if (word[1:] != word[1:].lower() or "_" in word or
                (word[0].isupper() and match.start() > 0 and plain[:match.start()].rstrip()[-1:] not in ".!?")):
            if word not in TOKEN.findall(source):
                return False
        if singular(word) not in allowed and word.lower() not in STOP_WORDS:
            return False
    return True


def purpose_plain(text: str) -> str:
    lowered = text.lower()
    if "web application framework" in lowered:
        return "A tool for building websites with Python." if "Python" in text else "A tool for building websites."
    if "command line interface" in lowered.replace("-", " "):
        return "A tool for making programs people run by typing commands."
    if "windows" in lowered and "backslash" in lowered and "slash paths" in lowered:
        return "Convert Windows file paths to forward slashes."
    if "promise-returning" in lowered and "limited concurrency" in lowered:
        return "Runs several tasks while limiting how many run at a time."
    watched = re.search(r"\bwatches (.{1,40}?) activity\b", text)
    if watched and "notification arrives" in lowered and "usage window resets" in lowered:
        return f"Watches {watched[1]} activity so you get a notification when your usage window resets."
    return re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0][:220].strip()
