"""Find a chain of wins from one character to another.

  python -m cwc.chain "Squirrel Girl" "Galactus"
  python -m cwc.chain "Spider-Man" "Thanos" --solo --methods fight
  python -m cwc.chain --stats

An arrow A -> B means A (alone or with others) beat B in some story.
Options:
  --solo              ignore wins where the winner had help
  --methods a,b       only count these methods (fight, outsmarted, talked_down, other)
  --min-confidence    high | medium | low (default low = everything)
  --main-only         only Earth-616 characters
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "data" / "extracted"
STORIES = ROOT / "data" / "stories"
CONF_RANK = {"low": 0, "medium": 1, "high": 2}


def load_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for p in STORIES.glob("*.json"):
        for c in json.loads(p.read_text())["characters"]:
            labels.setdefault(c["id"], c["label"])
    return labels


def load_edges(solo=False, methods=None, min_conf="low", main_only=False) -> list[dict]:
    edges = []
    for p in sorted(EXTRACTED.glob("*.json")):
        rec = json.loads(p.read_text())
        for d in rec["defeats"]:
            helped = len(d["winners"]) > 1
            if solo and helped:
                continue
            if methods and d["method"] not in methods:
                continue
            if CONF_RANK[d["confidence"]] < CONF_RANK[min_conf]:
                continue
            for w in d["winners"]:
                for l in d["losers"]:
                    if main_only and not (w.endswith("(Earth-616)") and l.endswith("(Earth-616)")):
                        continue
                    edges.append(
                        {
                            "winner": w,
                            "loser": l,
                            "issue": rec["issue"],
                            "url": rec["url"],
                            "method": d["method"],
                            "with_help": helped,
                            "confidence": d["confidence"],
                            "evidence": d["evidence"],
                        }
                    )
    return edges


def build_graph(edges: list[dict]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        g[e["winner"]].append(e)
    return g


def resolve(name: str, labels: dict[str, str], degree: dict[str, int]) -> str | None:
    q = name.lower()
    exact = [i for i, l in labels.items() if q in (i.lower(), l.lower())]
    hits = exact or [i for i, l in labels.items() if q in i.lower() or q in l.lower()]
    hits = [h for h in hits if degree.get(h)] or hits
    if not hits:
        return None
    hits.sort(key=lambda h: (-degree.get(h, 0), h))
    if len(hits) > 1:
        others = ", ".join(labels[h] for h in hits[1:4])
        print(f'"{name}" -> {labels[hits[0]]}  (also matched: {others})')
    return hits[0]


def shortest_chain(g, start: str, goal: str) -> list[dict] | None:
    prev: dict[str, dict | None] = {start: None}
    q = deque([start])
    while q:
        node = q.popleft()
        if node == goal:
            path = []
            while prev[node] is not None:
                e = prev[node]
                path.append(e)
                node = e["winner"]
            return path[::-1]
        for e in g.get(node, []):
            if e["loser"] not in prev:
                prev[e["loser"]] = e
                q.append(e["loser"])
    return None


def stats(edges: list[dict], labels: dict[str, str]) -> None:
    g = build_graph(edges)
    nodes = {e["winner"] for e in edges} | {e["loser"] for e in edges}
    pairs = {(e["winner"], e["loser"]) for e in edges}
    print(f"characters in the graph: {len(nodes)}")
    print(f"distinct 'A beat B' pairs: {len(pairs)}  (from {len(edges)} edge records)")
    # How many ordered pairs (A, B) have a chain from A to B?
    reach_total = 0
    best = (0, "")
    for n in nodes:
        seen = {n}
        q = deque([n])
        while q:
            for e in g.get(q.popleft(), []):
                if e["loser"] not in seen:
                    seen.add(e["loser"])
                    q.append(e["loser"])
        reach_total += len(seen) - 1
        best = max(best, (len(seen) - 1, n))
    possible = len(nodes) * (len(nodes) - 1)
    print(f"ordered pairs with a chain: {reach_total}/{possible} ({100 * reach_total / max(possible, 1):.1f}%)")
    if best[1]:
        print(f"widest reach: {labels.get(best[1], best[1])} can 'beat' {best[0]} characters")
    wins = defaultdict(int)
    for a, _ in pairs:
        wins[a] += 1
    top = sorted(wins.items(), key=lambda kv: -kv[1])[:10]
    print("most direct wins:", ", ".join(f"{labels.get(a, a)} ({n})" for a, n in top))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("start", nargs="?")
    ap.add_argument("goal", nargs="?")
    ap.add_argument("--solo", action="store_true")
    ap.add_argument("--methods")
    ap.add_argument("--min-confidence", default="low", choices=CONF_RANK)
    ap.add_argument("--main-only", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    labels = load_labels()
    edges = load_edges(
        solo=args.solo,
        methods=set(args.methods.split(",")) if args.methods else None,
        min_conf=args.min_confidence,
        main_only=args.main_only,
    )
    if args.stats or not (args.start and args.goal):
        stats(edges, labels)
        return

    degree: dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["winner"]] += 1
        degree[e["loser"]] += 1
    a = resolve(args.start, labels, degree)
    b = resolve(args.goal, labels, degree)
    if not a or not b:
        print(f"no character matched: {args.start if not a else args.goal}")
        return
    path = shortest_chain(build_graph(edges), a, b)
    if path is None:
        print(f"No chain from {labels[a]} to {labels[b]} with the current data and options.")
        return
    print(f"{labels[a]} beats {labels[b]} in {len(path)} step(s):\n")
    for i, e in enumerate(path, 1):
        helped = ", with help" if e["with_help"] else ""
        print(f"{i}. {labels.get(e['winner'], e['winner'])} beat {labels.get(e['loser'], e['loser'])}"
              f"  [{e['method']}{helped}, {e['confidence']} confidence]")
        print(f"   {e['issue']}: \"{e['evidence']}\"")
        print(f"   {e['url']}")


if __name__ == "__main__":
    main()
