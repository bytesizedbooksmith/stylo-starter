# _TEMPLATE — how to add a voice

Copy this folder to `authors/<your-slug>/` and follow the three steps. See
[../../MANUAL.md](../../MANUAL.md) §6 (your own voice) and §7 (a public-domain
author) for the full version.

`<slug>` is lowercase, hyphenated, and must match the folder name, the
`registry.json` key, and the `author_folder` column in `catalog.csv`.

## 1. Put the prose in `works/`

One UTF-8 Markdown file per book. For your **own** writing, paste it in directly.
For a **public-domain** author, leave `works/` empty and let
`fetch_corpus.py` fill it from the Gutenberg ids in `catalog.csv`.

Recommended shape (front matter and headings are optional — raw paragraphs
measure too):

```markdown
---
title: The Book Title
credited_author: Your Pen Name
original_publication_year: 2024
---

# The Book Title

*Your Pen Name; original text.*

## Chapter One

The prose starts here...
```

## 2. Add a row per work to `catalog.csv`

Leave `project_gutenberg_id` **blank** for your own work (that's how the fetcher
knows to skip it); fill it in for a public-domain author.

## 3. Add an entry to `registry.json`

Then build:

```bash
python3 scripts/fetch_corpus.py --author <slug>   # public-domain authors only
python3 scripts/build_stylo_profiles.py
```

> The build measures every author listed in `registry.json`. Don't add a
> registry entry until its `works/` has prose in it (or a Gutenberg id to fetch),
> or the build will error on an empty corpus.
