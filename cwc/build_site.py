"""Build the static site data in docs/data/ from data/extracted/.

  python -m cwc.build_site

docs/data/graph.json        everything the search needs (small; loaded once)
docs/data/details/<n>.json  "how" + quote for one story (fetched only when shown)
"""

from __future__ import annotations

import json
import shutil

from .chain import EXTRACTED, ROOT, load_labels

DOCS = ROOT / "docs" / "data"
METHODS = ["fight", "outsmarted", "talked_down", "other"]
CONF = ["low", "medium", "high"]


def main() -> None:
    labels = load_labels()
    if (DOCS / "details").exists():
        shutil.rmtree(DOCS / "details")
    (DOCS / "details").mkdir(parents=True)

    char_index: dict[str, int] = {}
    chars: list[list] = []  # [label, wiki id]
    stories: list[list] = []  # [issue, url]
    edges: list[list] = []  # [winner, loser, story, defeat#, method, conf, helped]

    def cid(i: str) -> int:
        if i not in char_index:
            char_index[i] = len(chars)
            chars.append([labels.get(i, i), i])
        return char_index[i]

    for p in sorted(EXTRACTED.glob("*.json")):
        rec = json.loads(p.read_text())
        if not rec["defeats"]:
            continue
        s = len(stories)
        stories.append([rec["issue"], rec["url"]])
        details = []
        for k, d in enumerate(rec["defeats"]):
            details.append({"how": d.get("how", ""), "evidence": d["evidence"]})
            helped = 1 if len(d["winners"]) > 1 else 0
            for w in d["winners"]:
                for l in d["losers"]:
                    edges.append([cid(w), cid(l), s, k, METHODS.index(d["method"]),
                                  CONF.index(d["confidence"]), helped])
        (DOCS / "details" / f"{s}.json").write_text(json.dumps(details, ensure_ascii=False))

    graph = {"methods": METHODS, "confidence": CONF, "chars": chars, "stories": stories, "edges": edges}
    (DOCS / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(chars)} characters, {len(edges)} edges, {len(stories)} stories -> {DOCS}")


if __name__ == "__main__":
    main()
