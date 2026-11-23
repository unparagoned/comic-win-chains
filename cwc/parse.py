"""Turn an issue page's wikitext into stories: title, characters present, plain-text synopsis.

An issue page can hold several stories (StoryTitle1/Appearing1/Synopsis1, ...2, ...).
Only characters shown on-panel count. Lines tagged Mentioned, Vision, Referenced,
Invoked, Photo and similar are dropped, as are races, locations, items and vehicles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Appearance templates that mean the character is not physically there.
NOT_PRESENT = {
    "mentioned", "vision", "referenced", "invoked", "photo", "picture", "image",
    "flashback", "flashbackonly", "impersonated", "imposter", "corpse", "statue",
    "illusion", "mention", "voice", "hologram", "dream", "fantasy", "poster",
    "appears in flashback", "apfb",
}
SECTION_ROLES = {
    "featured": "featured",
    "supporting": "supporting",
    "antagonist": "antagonist",
    "villain": "antagonist",
    "other": "other",
}
STOP_SECTIONS = ("races", "locations", "items", "vehicles", "realities", "groups:")

LINK_RE = re.compile(r"\[\[([^\[\]|]+)(?:\|([^\[\]]*))?\]\]")
CHAR_ID_RE = re.compile(r"\(Earth-[^)]+\)$")


@dataclass
class Character:
    id: str        # wiki page name, e.g. "Peter Parker (Earth-616)"
    label: str     # display text, e.g. "Spider-Man (Peter Parker)"
    role: str      # featured / supporting / antagonist / other


@dataclass
class Story:
    number: int
    title: str
    characters: list[Character] = field(default_factory=list)
    synopsis: str = ""


def _template_fields(wikitext: str) -> dict[str, str]:
    """Split the top-level '| Key = value' fields of the comic template."""
    fields: dict[str, str] = {}
    key = None
    buf: list[str] = []
    for line in wikitext.splitlines():
        m = re.match(r"^\|\s*([A-Za-z0-9_]+)\s*=\s*(.*)$", line)
        if m:
            if key:
                fields[key] = "\n".join(buf).strip()
            key, buf = m.group(1), [m.group(2)]
        elif key:
            buf.append(line)
    if key:
        fields[key] = "\n".join(buf).strip()
    return fields


def _strip_files(text: str) -> str:
    """Remove [[File:...]] blocks, which can nest links inside their captions."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("[[File:", i) or text.startswith("[[Image:", i):
            depth, j = 0, i
            while j < len(text):
                if text.startswith("[[", j):
                    depth += 1
                    j += 2
                elif text.startswith("]]", j):
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _strip_templates(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    return text


def clean_synopsis(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = _strip_files(text)
    text = _strip_templates(text)
    text = LINK_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_appearing(text: str) -> list[Character]:
    chars: dict[str, Character] = {}
    role = "other"
    for raw in text.splitlines():
        line = raw.strip()
        header = re.match(r"^'''(.+?)'''", line)
        if header:
            h = header.group(1).lower()
            if h.startswith(STOP_SECTIONS):
                role = None
                continue
            role = next((r for k, r in SECTION_ROLES.items() if k in h), "other")
            continue
        if role is None or not line.startswith("*"):
            continue
        # Outermost template name on the line, e.g. {{Mentioned|...}} or {{apn|...}}
        tmpl = re.search(r"\{\{\s*([^|}]+)", line)
        if tmpl and tmpl.group(1).strip().lower() in NOT_PRESENT:
            continue
        link = LINK_RE.search(line)
        if not link:
            continue
        cid, label = link.group(1).strip(), (link.group(2) or link.group(1)).strip()
        if "#" in cid or not CHAR_ID_RE.search(cid):
            continue  # unnamed index entries and non-character pages
        if cid not in chars:
            chars[cid] = Character(cid, label, role)
    return list(chars.values())


def parse_issue(wikitext: str) -> list[Story]:
    f = _template_fields(wikitext)
    stories = []
    n = 1
    while f"Synopsis{n}" in f or f"Appearing{n}" in f:
        synopsis = clean_synopsis(f.get(f"Synopsis{n}", ""))
        story = Story(
            number=n,
            title=clean_synopsis(f.get(f"StoryTitle{n}", "")),
            characters=parse_appearing(f.get(f"Appearing{n}", "")),
            synopsis=synopsis,
        )
        stories.append(story)
        n += 1
    return stories
