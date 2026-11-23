"""Build the 100-issue proof-of-concept sample.

About 20 issues with well-known upsets, plus random issues (fixed seed) from the
long-running flagship series, where the most-searched characters appear.
Missing pages are dropped at fetch time, so the list can overshoot slightly.
"""

import random
from pathlib import Path

KNOWN_UPSETS = [
    "Marvel Super-Heroes Vol 2 8",            # Squirrel Girl vs Doctor Doom
    "G.L.A. Vol 1 4",                            # Squirrel Girl vs Thanos
    "Unbeatable Squirrel Girl Vol 1 4",       # Squirrel Girl vs Galactus
    "Marvel Super Heroes Secret Wars Vol 1 10",  # Doom takes the Beyonder's power
    "Marvel Super Heroes Secret Wars Vol 1 11",
    "Marvel Super Heroes Secret Wars Vol 1 12",
    "Amazing Spider-Man Vol 1 229",           # Spider-Man vs Juggernaut
    "Amazing Spider-Man Vol 1 230",
    "Amazing Spider-Man Vol 1 269",           # Spider-Man vs Firelord
    "Amazing Spider-Man Vol 1 270",
    "Fantastic Four Vol 1 48",                # Galactus trilogy
    "Fantastic Four Vol 1 49",
    "Fantastic Four Vol 1 50",
    "Infinity Gauntlet Vol 1 1",
    "Infinity Gauntlet Vol 1 4",
    "Infinity Gauntlet Vol 1 6",
    "Avengers Vol 1 4",
    "Incredible Hulk Vol 1 1",
]

# (page-title prefix, first issue, last issue)
FLAGSHIP_SERIES = [
    ("Amazing Spider-Man Vol 1", 1, 441),
    ("Fantastic Four Vol 1", 1, 416),
    ("Avengers Vol 1", 1, 402),
    ("X-Men Vol 1", 1, 141),
    ("Uncanny X-Men Vol 1", 142, 544),
    ("Thor Vol 1", 126, 502),
    ("Incredible Hulk Vol 1", 102, 474),
    ("Iron Man Vol 1", 1, 332),
    ("Captain America Vol 1", 100, 454),
    ("Daredevil Vol 1", 1, 380),
]
RANDOM_COUNT = 85
SEED = 616


def main() -> None:
    rng = random.Random(SEED)
    chosen = set(KNOWN_UPSETS)
    random_titles = []
    while len(random_titles) < RANDOM_COUNT:
        prefix, lo, hi = rng.choice(FLAGSHIP_SERIES)
        title = f"{prefix} {rng.randint(lo, hi)}"
        if title not in chosen:
            chosen.add(title)
            random_titles.append(title)
    out = Path(__file__).with_name("poc_issues.txt")
    out.write_text("\n".join(KNOWN_UPSETS + random_titles) + "\n")
    print(f"wrote {len(KNOWN_UPSETS) + len(random_titles)} titles to {out}")


if __name__ == "__main__":
    main()
