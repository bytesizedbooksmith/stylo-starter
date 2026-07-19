# Stylometry Starter

Give a writing voice a **measured** fingerprint — so *"sound like me / don't
sound like the model"* becomes something you can check, not just argue about.

The toolkit measures the small, stable habits that make a voice (sentence
rhythm, dialogue architecture, punctuation, function words, and more), turns
them into a set of normal ranges — *lanes* — and then tells you whether any
draft is inside those lanes or has drifted, and where.

- **Nothing to install.** Python 3.9+ and the standard library. No spaCy, no
  numpy, no accounts, no API keys.
- **Nothing leaves your machine.** Measuring, building and checking are all
  local. The only network call is downloading public-domain books from Project
  Gutenberg when you ask for them.
- **Works with no backlist.** Thirteen public-domain authors ship ready to measure
  against, so you can start on day one and add your own voice later.

## Quickstart

```bash
# from this folder
python3 scripts/test_stylo.py           # (optional) prove the install works
python3 scripts/fetch_corpus.py         # download + convert the reference authors
python3 scripts/build_stylo_profiles.py # build every profile, card and index
python3 scripts/stylo_check.py my-scene.md --author agatha-christie
```

Then open `authors/agatha-christie/profile/agatha-christie-style-card.md` to see
what a profile looks like.

## Where to go next

**[MANUAL.md](MANUAL.md)** is the full guide: the two mental models (the
*instrument* vs the *song*, and the *contrast lens*), how to add your own voice
as a target, how to add another public-domain author, what every measurement
means, and how to use it in a drafting loop. Start there.

## The three commands

| Command | Does |
|---|---|
| `scripts/fetch_corpus.py` | Downloads the works in `catalog.csv` from Project Gutenberg and converts them to the Markdown the profiler reads. |
| `scripts/build_stylo_profiles.py` | Measures every author in `registry.json`, writes each one's style card + report + `profile.json`, and fits the shared cross-author space. |
| `scripts/stylo_check.py` | Audits one draft against one profile and prints only what drifted, with a rewrite brief. Exit `0` = in lane, `1` = drift. |

## What's public-domain, and what's yours

The **engine** is a from-scratch implementation of classic, public stylometry
(Burrows's Delta, function-word analysis) — standard library only. The
**reference texts** are Project Gutenberg public-domain editions, downloaded by
you at build time from the ids in `catalog.csv`. Anything **you** add — your own
prose, your own pen's profile — stays entirely in your copy.

Public-domain status is judged here on a U.S. publication-year basis and changes
by country and by year; confirm a work where you are before adding it.

## License

The code and documentation are released under the [MIT License](LICENSE) — use,
modify and share freely. The reference texts themselves are not included in this
repository; you download them from Project Gutenberg at build time, and they are
public domain.

## Acknowledgments

The approach behind this toolkit was **deeply inspired by Future Fiction
Academy's stylometry class**, which is where these ideas came from. The engine
and manual here are an independent, from-scratch implementation of classic,
public stylometry methods — none of FFA's course materials are reproduced — but
the inspiration and the debt are theirs, and gratefully acknowledged.

## Layout

```
scripts/stylo/         the measurement engine
scripts/*.py           fetch / build / check / self-test
registry.json          the authors the build knows about
catalog.csv            one row per work (+ its Gutenberg id)
authors/<slug>/works/  each author's prose (fetched or supplied by you)
authors/<slug>/profile/  generated style card, report, profile.json, CSVs
stylometry/            generated shared space + cross-author index
```

Generated folders (`profile/`, `stylometry/`, `sources/`) are yours to
regenerate any time with `build_stylo_profiles.py`; they're git-ignored by
default.
