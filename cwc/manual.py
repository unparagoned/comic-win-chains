"""Run the extraction without the API: write prompts out, read answers back.

Used for the first proof-of-concept run, which was done inside a Claude Code
session (no API key on the machine). Same prompt, schema and validation as
cwc.extract, so results are comparable.

  python -m cwc.manual dump            # data/manual/prompts/<story>.txt
  python -m cwc.manual ingest          # data/manual/answers/<story>.json -> data/extracted/
"""

from __future__ import annotations

import json
import sys

from .extract import OUT_DIR, ROOT, SCHEMA, STORIES_DIR, SYSTEM_PROMPT, user_prompt, validate

MANUAL = ROOT / "data" / "manual"


def dump() -> None:
    out = MANUAL / "prompts"
    out.mkdir(parents=True, exist_ok=True)
    (MANUAL / "answers").mkdir(parents=True, exist_ok=True)
    (MANUAL / "SYSTEM_PROMPT.txt").write_text(
        SYSTEM_PROMPT + "\n\nAnswer with JSON matching this schema:\n" + json.dumps(SCHEMA, indent=1)
    )
    n = 0
    for p in sorted(STORIES_DIR.glob("*.json")):
        story = json.loads(p.read_text())
        (out / (p.stem + ".txt")).write_text(user_prompt(story))
        n += 1
    print(f"wrote {n} prompts to {out}")


def ingest() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = dropped = 0
    for a in sorted((MANUAL / "answers").glob("*.json")):
        story = json.loads((STORIES_DIR / a.name).read_text())
        raw = json.loads(a.read_text())["defeats"]
        defeats = validate(story, raw)
        total += len(defeats)
        dropped += len(raw) - len(defeats)
        (OUT_DIR / a.name).write_text(
            json.dumps(
                {
                    "story_id": story["story_id"],
                    "issue": story["issue"],
                    "url": story["url"],
                    "extracted_by": "claude-code-session (manual run, Claude Opus 5.5)",
                    "dropped": len(raw) - len(defeats),
                    "defeats": defeats,
                },
                ensure_ascii=False,
                indent=1,
            )
        )
    print(f"ingested: {total} defeats kept, {dropped} dropped by validation")


if __name__ == "__main__":
    {"dump": dump, "ingest": ingest}[sys.argv[1]]()
