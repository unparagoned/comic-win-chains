"""Write data/review.md: every extracted defeat with its evidence, for checking by hand.

Tick a box when the defeat is right; write a note when it isn't. Accuracy =
ticked / total. Also lists stories with no defeats, so missed fights can be spotted.
"""

from __future__ import annotations

import json

from .chain import EXTRACTED, ROOT, load_labels

OUT = ROOT / "data" / "review.md"


def main() -> None:
    labels = load_labels()
    name = lambda ids: ", ".join(labels.get(i, i) for i in ids)  # noqa: E731
    lines = ["# Extraction review", "",
             "Tick each defeat that the linked issue page supports. Note anything missed under 'No defeats found'.", ""]
    empty = []
    n = 0
    for p in sorted(EXTRACTED.glob("*.json")):
        rec = json.loads(p.read_text())
        if not rec["defeats"]:
            empty.append(rec)
            continue
        lines.append(f"## [{rec['story_id']}]({rec['url']})")
        for d in rec["defeats"]:
            n += 1
            lines.append(
                f"- [ ] **{name(d['winners'])}** beat **{name(d['losers'])}** "
                f"({d['method']}, {d['confidence']})  \n  > {d['evidence']}"
            )
        lines.append("")
    lines += ["## No defeats found", ""]
    lines += [f"- [{r['story_id']}]({r['url']})" for r in empty]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {n} defeats and {len(empty)} empty stories to {OUT}")


if __name__ == "__main__":
    main()
