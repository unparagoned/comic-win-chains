"""Fetch a list of issues and write one extraction task per story to data/stories/.

Usage: python -m cwc.prepare samples/poc_issues.txt
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from .parse import parse_issue
from .wiki import fetch, page_url

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "data" / "stories"
MIN_SYNOPSIS_CHARS = 200  # shorter than this is usually a stub with no fight detail


def story_id(issue: str, n: int) -> str:
    return f"{issue} #s{n}"


def main(list_file: str) -> None:
    titles = [t.strip() for t in Path(list_file).read_text().splitlines() if t.strip()]
    pages = fetch(titles)
    STORIES_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"issues": len(titles), "missing": [], "stories": 0, "usable": 0, "stub": 0}
    for issue in titles:
        text = pages.get(issue)
        if text is None:
            stats["missing"].append(issue)
            continue
        for story in parse_issue(text):
            stats["stories"] += 1
            usable = len(story.synopsis) >= MIN_SYNOPSIS_CHARS and len(story.characters) >= 2
            stats["usable" if usable else "stub"] += 1
            if not usable:
                continue
            task = {
                "story_id": story_id(issue, story.number),
                "issue": issue,
                "url": page_url(issue),
                **asdict(story),
            }
            safe = task["story_id"].replace("/", "_").replace(" ", "_").replace("#", "")
            (STORIES_DIR / f"{safe}.json").write_text(json.dumps(task, ensure_ascii=False, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
