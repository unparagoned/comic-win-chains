"""Fetch issue pages from the Marvel Database (marvel.fandom.com) and cache them.

Uses the MediaWiki API, 50 titles per request, with a pause between requests.
Cached pages go to data/raw/<title>.json and are reused on later runs.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://marvel.fandom.com/api.php"
USER_AGENT = "comic-win-chains/0.1 (research prototype; github.com/unparagoned/comic-win-chains)"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BATCH = 50
PAUSE_SECONDS = 1.0


def cache_path(title: str) -> Path:
    return RAW_DIR / f"{title.replace('/', '_')}.json"


def _query(titles: list[str]) -> dict:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content|ids",
        "rvslots": "main",
        "titles": "|".join(titles),
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch(titles: list[str], refresh: bool = False) -> dict[str, str | None]:
    """Return {requested title: wikitext or None if the page doesn't exist}."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, str | None] = {}
    todo = []
    for t in titles:
        p = cache_path(t)
        if p.exists() and not refresh:
            result[t] = json.loads(p.read_text())["wikitext"]
        else:
            todo.append(t)

    for i in range(0, len(todo), BATCH):
        chunk = todo[i : i + BATCH]
        data = _query(chunk)["query"]
        # Map normalised/redirected titles back to what was requested.
        alias = {t: t for t in chunk}
        for step in ("normalized", "redirects"):
            for m in data.get(step, []):
                for req_t, cur in list(alias.items()):
                    if cur == m["from"]:
                        alias[req_t] = m["to"]
        pages = {p["title"]: p for p in data["pages"]}
        for req_t, final in alias.items():
            page = pages.get(final)
            if not page or page.get("missing"):
                result[req_t] = None
                continue
            rev = page["revisions"][0]
            text = rev["slots"]["main"]["content"]
            cache_path(req_t).write_text(
                json.dumps(
                    {"title": final, "revid": rev["revid"], "wikitext": text},
                    ensure_ascii=False,
                )
            )
            result[req_t] = text
        if i + BATCH < len(todo):
            time.sleep(PAUSE_SECONDS)
    return result


def page_url(title: str) -> str:
    return "https://marvel.fandom.com/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
