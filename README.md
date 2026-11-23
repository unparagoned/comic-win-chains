# comic-win-chains

"Six degrees of separation", but for comic fights: find a chain of on-panel wins from any character to any other. Squirrel Girl beat Doctor Doom, Doom beat the Beyonder, so Squirrel Girl "beats" the Beyonder in two steps.

Comics are inconsistent, so the win graph is full of loops. The question is how often any character can reach any other.

## How it works

1. **Fetch** issue pages from the [Marvel Database](https://marvel.fandom.com) wiki through its MediaWiki API (`cwc/wiki.py`).
2. **Parse** each story into its synopsis and the characters actually present, with their wiki IDs such as `Peter Parker (Earth-616)`. Mentioned, vision and flashback appearances are dropped (`cwc/parse.py`).
3. **Extract** "who beat whom" with Claude. The model picks winners and losers from that story's character list, and tags each defeat with a method (`fight`, `outsmarted`, `talked_down`, `other`), a one-sentence "how", a confidence and a verbatim evidence quote (`cwc/extract.py`). IDs not in the list are dropped.
4. **Chain**: a directed graph from winner to loser, with a shortest-path search (`cwc/chain.py`).

```sh
uv venv && uv pip install anthropic
python3 samples/make_sample.py                  # 103-issue sample list
python3 -m cwc.prepare samples/poc_issues.txt   # fetch + parse -> data/stories/
python3 -m cwc.extract --limit 5                # needs ANTHROPIC_API_KEY
python3 -m cwc.review                           # data/review.md, for checking by hand
python3 -m cwc.chain "Squirrel Girl" "Galactus"
python3 -m cwc.chain --stats --solo --methods fight --min-confidence high
```

Each chain option is a filter that can be ticked on or off:

| Option | Effect |
|---|---|
| `--solo` | ignore wins where the winner had help |
| `--methods fight,outsmarted` | only these kinds of win |
| `--min-confidence high` | drop implied or unsure defeats |
| `--main-only` | Earth-616 only |

## Proof of concept (Nov 2026): 103 issues

The sample is 18 well-known upset issues plus 85 random issues from ten flagship series (seed 616).

- 103 pages were fetched, giving 113 stories. 98 had a synopsis long enough to use; 15 were stubs.
- **167 defeats** were extracted, covering 225 characters and 408 distinct "A beat B" pairs.
- 21 stories had no defeats.
- 15.3% of ordered character pairs have a chain. With `--solo --methods fight --min-confidence high` this falls to 2.0%.

This first run did not use the API, because no key was available. It was done inside a Claude Code session (Claude Opus 5.5) using the same prompt, schema and validation, via `cwc/manual.py`. Every ID and every evidence quote was checked against its prompt file. `extracted_by` in each file records this.

Sample chain:

```
Squirrel Girl beats Galactus in 3 step(s):

1. Squirrel Girl beat Doctor Doom  [fight, high confidence]
   Marvel Super-Heroes Vol 2 8
   How: Her squirrels chewed through the Doomship's wiring and attacked Doom, decimating his armour until he fled through a hatch and jumped into the water.
2. Doctor Doom beat Mister Fantastic  [outsmarted, high confidence]
   Fantastic Four Vol 1 23
   How: Doom used a Thing robot to fire an FF signal flare, luring Reed into a trap where they captured him in an escape-proof container.
3. Mister Fantastic beat Galactus  [talked_down, with help, high confidence]
   Fantastic Four Vol 1 50
   How: Johnny brought back the Ultimate Nullifier and Reed threatened to use it, so Galactus agreed to spare Earth and leave in exchange for the weapon.
```

The "how" field was added in a second pass over the same 167 defeats, without changing them. For 30 of them the synopsis gives no real detail, and the sentence says so ("The synopsis only says...").

### Findings

- **The wiki data is good enough.** Synopses are detailed (median about 1,900 characters), and the character lists make the IDs reliable: 0 of 167 defeats were dropped for bad IDs.
- **Accuracy.** In a random sample of 20 defeats checked against their quotes, about 17 were plainly supported. The weak ones were already tagged `low` or `medium`. This was a quick check, not a full review; `data/review.md` is there for a proper one.
- **One-to-many entries dominate the graph.** One medium-confidence entry ("massive blast of energy", Secret Wars 11) makes Doom beat 23 heroes. A cap on losers per entry, or counting that entry once, would help.
- **Team IDs are nodes**, for example `X-Men (Earth-616)` and `Avengers (Earth-616)`. They should probably be dropped or expanded into members.
- **Coverage is the limit.** With about 100 issues, Spider-Man has no chain to Thanos. Reach should grow quickly with more issues, as in any small-world network, but this sample doesn't show that yet.
- **Wiki quirks.** Page titles don't always match the cover title (`Marvel Super Heroes Secret Wars`, `G.L.A.`), so look titles up with search.

### Cost estimate (not measured)

The 98 prompts are about 150k input tokens in total (characters ÷ 4), and the answers about 11k output tokens, plus thinking.

| Model | Rough cost per 100 stories |
|---|---|
| `claude-opus-5-5` at low effort | ~$1-2 |
| `claude-haiku-5-5` | ~$0.05 |

The Batches API halves both. Run `python3 -m cwc.extract --limit 20` with a key, then sum `data/usage.jsonl`, to get real numbers.

## Next

- Have someone review `data/review.md` to get a real accuracy number.
- Run the API extraction on the same 98 stories and compare it with this run.
- Cap or flag mass-defeat entries; handle team IDs.
- Scale up: start with the issue lists of the most-appearing characters, then go wider. Add DC from the DC Database.
- A web page with tick-box options.

## Licence and attribution

Synopses and character data come from the Marvel Database on Fandom, under [CC BY-SA](https://www.fandom.com/licensing). Raw pages and full synopses are not committed (`data/raw/` and `data/stories/` are gitignored); the extracted files hold only short evidence quotes, with a link to each source page.
