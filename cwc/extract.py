"""Extract "who beat whom" from each story with Claude.

Usage:
  python -m cwc.extract                 # all stories in data/stories without a result yet
  python -m cwc.extract --limit 5       # try a few first
  python -m cwc.extract --model claude-haiku-5-5

Needs Anthropic credentials (ANTHROPIC_API_KEY or `ant auth login`).
Writes data/extracted/<story>.json and appends token usage to data/usage.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "data" / "stories"
OUT_DIR = ROOT / "data" / "extracted"
USAGE_LOG = ROOT / "data" / "usage.jsonl"
DEFAULT_MODEL = "claude-opus-5-5"

METHODS = ["fight", "outsmarted", "talked_down", "other"]

SYSTEM_PROMPT = """You read plot synopses of Marvel comic stories and record who defeated whom.

A defeat counts when the story's own events end a confrontation in one side's favour: the loser is knocked out, captured, trapped, killed, depowered, forced to retreat, flee or surrender, or persuaded to stop fighting. Record it even if the defeat is temporary, a trick, or later undone.

Do not record:
- fights that are interrupted, end in a stalemate, or where the loser simply gets away
- plans that are foiled without anyone being beaten
- defeats of unnamed people, crowds, robots or soldiers not in the character list
- events only remembered, imagined, dreamed or described as happening off-panel in another story

For each defeat:
- winners and losers are character IDs copied exactly from the character list. List every character who actively contributed to the win.
- method: "fight" (beaten physically or with powers), "outsmarted" (tricked, trapped, out-thought), "talked_down" (persuaded or shamed into giving up), or "other".
- how: one plain sentence (under 30 words) saying how the winner won, e.g. "Her squirrels chewed through the Doomship's wiring and tore at his armour until he fled into the sea." Use only what the synopsis says; do not add details from your own knowledge.
- evidence: one short quote copied from the synopsis that shows the defeat.
- confidence: "high" if the synopsis states it plainly, "medium" if it is implied, "low" if you are unsure.

Record one entry per distinct confrontation. If there are no defeats, return an empty list."""

SCHEMA = {
    "type": "object",
    "properties": {
        "defeats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "winners": {"type": "array", "items": {"type": "string"}},
                    "losers": {"type": "array", "items": {"type": "string"}},
                    "method": {"type": "string", "enum": METHODS},
                    "how": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["winners", "losers", "method", "how", "evidence", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["defeats"],
    "additionalProperties": False,
}


def user_prompt(story: dict) -> str:
    chars = "\n".join(
        f"- {c['id']} | shown as: {c['label']} | role: {c['role']}" for c in story["characters"]
    )
    return (
        f"Issue: {story['issue']}\nStory: {story['title']}\n\n"
        f"Characters present (ID | shown as | role):\n{chars}\n\n"
        f"Synopsis:\n{story['synopsis']}"
    )


def validate(story: dict, defeats: list[dict]) -> list[dict]:
    """Drop IDs not in the character list and entries left with an empty side."""
    known = {c["id"] for c in story["characters"]}
    clean = []
    for d in defeats:
        w = [x for x in d["winners"] if x in known]
        l = [x for x in d["losers"] if x in known and x not in w]
        if w and l:
            clean.append({**d, "winners": w, "losers": l})
    return clean


def story_file(story_path: Path) -> Path:
    return OUT_DIR / story_path.name


def extract_one(client, model: str, story: dict) -> tuple[list[dict], dict]:
    import anthropic  # noqa: F401  (imported here so other modules run without the SDK)

    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt(story)}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    usage = {
        "story_id": story["story_id"],
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
    }
    if response.stop_reason in ("refusal", "max_tokens"):
        return [], usage
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["defeats"], usage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--redo", action="store_true", help="re-extract stories that already have a result")
    args = ap.parse_args()

    import anthropic

    client = anthropic.Anthropic()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(STORIES_DIR.glob("*.json"))
    if not args.redo:
        paths = [p for p in paths if not story_file(p).exists()]
    if args.limit:
        paths = paths[: args.limit]

    for i, p in enumerate(paths, 1):
        story = json.loads(p.read_text())
        try:
            raw, usage = extract_one(client, args.model, story)
        except anthropic.RateLimitError as e:
            sys.exit(f"rate limited, stopping (re-run to resume): {e}")
        except anthropic.APIStatusError as e:
            print(f"[{i}/{len(paths)}] {story['story_id']}: API error {e.status_code}, skipped")
            continue
        defeats = validate(story, raw)
        story_file(p).write_text(
            json.dumps(
                {
                    "story_id": story["story_id"],
                    "issue": story["issue"],
                    "url": story["url"],
                    "extracted_by": usage["model"],
                    "dropped": len(raw) - len(defeats),
                    "defeats": defeats,
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        with USAGE_LOG.open("a") as f:
            f.write(json.dumps(usage) + "\n")
        print(f"[{i}/{len(paths)}] {story['story_id']}: {len(defeats)} defeats")


if __name__ == "__main__":
    main()
