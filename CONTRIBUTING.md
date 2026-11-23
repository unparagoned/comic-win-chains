# Contributing

## Reporting a wrong win

Open an issue with:

- the two characters and the issue (copy the step from the site)
- what is wrong: didn't happen, wrong winner, wrong method, or a bad "how"
- the page or panel that shows it, if you have it

## Fixing it yourself

Each story's wins are in `data/extracted/<issue>.json`. Edit the entry, then run:

```sh
python3 -m cwc.build_site
```

Commit both the data file and `docs/data/`, and open a pull request. Use character IDs exactly as they appear in the file, for example `Peter Parker (Earth-616)`.

By contributing data you agree to license it under CC BY-SA 4.0 (see `DATA-LICENSE.md`). Code contributions are under MIT (see `LICENSE`).
