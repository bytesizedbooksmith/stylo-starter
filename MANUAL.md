# The Stylometry Starter — Manual

A small, self-contained toolkit for giving a writing voice a **measured**
fingerprint, so *"sound like me / don't sound like the model"* becomes something
you can check instead of argue about.

Everything here runs on Python's standard library. There is nothing to install,
nothing to sign up for, and no text ever leaves your machine.

---

## 1. The one idea

A model can imitate a *topic* easily and a *voice* badly. The gap shows up in
the small, unglamorous habits a writer never thinks about: how long their
sentences run and how much that length varies, how often they break into
dialogue, which function words they lean on, whether they favour the dash or the
semicolon, how many paragraphs are a single sentence.

Those habits are stable across a writer's books and hard to fake on purpose.
Measured in bulk, they become a **profile** — a set of *lanes*, each a normal
range for one habit. You can then take any draft and ask: is this inside the
lanes, or has it drifted? When it drifts, the tool tells you which habit drifted
and by how much, and hands back a short rewrite brief. No AI call, no rereading
the manuscript.

That is the whole system. The rest is how to feed it and how to read what it
says back.

---

## 2. Two mental models to keep straight

### The instrument, not the song

The profile does **not** capture your finished, best-edited voice — your *song*.
It captures the structural *instrument* underneath it: the shape of your prose
before polish. That distinction matters because it tells you what the profile is
good for. It is an **anti-drift anchor** — a fixed thing to measure against so a
model can't quietly pull your rhythm toward its own defaults over a long draft.
It is *not* a style you should try to perform. Some of what a raw profile
measures (an elevated adverb rate, say) is just draft residue you'd strip on an
edit pass, not a target to hold prose to.

### The contrast lens

You do not have to measure a draft against *your own* voice. The kit ships with
thirteen public-domain authors already set up as profiles, and the most useful move
in the whole toolkit is to point a scene at **one of them** when their habits fit
what you're writing better than your own baseline does — Christie's short,
dialogue-forward rhythm for a punchy contemporary scene, Wharton's long
interior narration for a reflective one, Nesbit's warm intrusive third person for
cozy fantasy.

This is also the answer to the cold-start problem. **You do not need a backlist
to begin.** With no words of your own yet, you can still measure a draft against
a contrast lens from day one, and the reference authors give you a working
distinctiveness baseline for free (see §6).

Two rules that keep the lens honest:

- **Don't average corpora.** "Good fiction in general" is not a voice. Pick
  *one* target per check, or borrow *specific families* from different targets
  and check each separately (§7).
- **Better lane-fit is necessary, not sufficient.** A draft sitting neatly
  inside Christie's lanes is not proof it reads well. Lanes measure surfaces.
  Only a reader knows if the scene lands.

---

## 3. What's in the box

```
stylo-starter/
  scripts/
    stylo/                     the measurement engine (standard library only)
    fetch_corpus.py            download + convert the reference corpus
    build_stylo_profiles.py    build every profile, card, report and index
    stylo_check.py             audit a draft against one profile
    test_stylo.py              self-test — prove the install works
  registry.json                the authors the build knows about (data, not code)
  catalog.csv                  one row per work, with its Gutenberg id
  authors/<slug>/works/        each author's prose (you fetch or supply it)
  authors/<slug>/profile/      generated: style card, report, profile.json, CSVs
  stylometry/                  generated: shared Delta space + cross-author index
```

The thirteen reference authors are a **genre sampler**, not a literary survey —
each is a lane you might actually write toward:

- **Romance & gothic romance** — Jane Austen (comedy of manners), Charlotte Brontë (first-person gothic romance)
- **Cozy, wholesome & small-town** — Louisa May Alcott, L. M. Montgomery, Elizabeth Gaskell
- **Cozy fantasy** — Kenneth Grahame, E. Nesbit
- **Mystery** — Agatha Christie, Arthur Conan Doyle, G. K. Chesterton (cozy)
- **Gothic / dark** — Bram Stoker
- **Science fiction** — H. G. Wells
- **Literary / upmarket** — Edith Wharton

They still span genres on purpose: distinctiveness is only meaningful against a
spread, so keep some spread even as you tailor the set. Swap any of them, or add
your own — the whole set is just `catalog.csv` plus `registry.json` (§7).

---

## 4. Quickstart

```bash
# From the stylo-starter/ folder. Python 3.9+; nothing to install.

# 0. (optional) prove the engine works.
python3 scripts/test_stylo.py

# 1. Fetch the reference authors from Project Gutenberg and convert
#    them to the Markdown the profiler reads. ~45 files, a couple of minutes.
python3 scripts/fetch_corpus.py

# 2. Build every profile, style card, report and the cross-author index.
python3 scripts/build_stylo_profiles.py

# 3. Audit a draft against one author's lane.
python3 scripts/stylo_check.py my-scene.md --author agatha-christie
```

`stylo_check.py` exits `0` when the draft is inside the lane on every primary
measurement and `1` when something drifted, so it can gate a script.

Useful options on the check:

| Option | Why |
|---|---|
| `--scene conversation` / `--scene reflection` | Swap the dialogue lane for the scene type. A confrontation is *allowed* to be talk-heavy; a reflection is not. |
| `--pov third --tense past` | Declare intent so the tool can flag POV/tense slips. It can't tell a choice from a mistake unless you tell it. |
| `--families dialogue,punctuation` | Check only some families — how you build a hybrid lane from several authors. |
| `--json` | Machine-readable result for a rewrite loop. |

---

## 5. The two on-ramps

**You have a backlist.** Add your own prose as an author (§6) and measure drafts
against yourself. Use your **cleanest pre-AI writing** — the point of the anchor
is that it has zero model contamination. Aim for ~150k+ words for stable lanes;
less works but the lanes will be wider and shakier.

**You don't have a backlist yet.** Skip straight to measuring against a contrast
lens (§2). Pick the reference author whose genre and register are closest to what
you're writing and check against them. When you've written enough of your own
clean prose, add yourself and switch the anchor over.

---

## 6. Add your own voice as a target

Three things have to be in place before you build, because the build measures
each registered author and will error on one that has no works. Add all three,
then build.

**a. Drop your prose into `authors/<your-slug>/works/`** as UTF-8 Markdown, one
file per book. The recommended shape (the profiler skips the non-prose parts):

```markdown
---
title: The Book Title
credited_author: Your Pen Name
original_publication_year: 2024
---

# The Book Title

*Your Pen Name; original text.*

## Chapter One

The prose starts here. Ordinary paragraphs separated by blank lines. Hard-wrapped
lines inside a paragraph are joined automatically, so paste is fine.
```

Front matter and headings are optional — raw paragraphs measure too — but the
shape above keeps chapter titles and bylines out of the numbers.

**b. Add one row per work to `catalog.csv`.** Leave `project_gutenberg_id`
**blank** for your own writing; that is how `fetch_corpus.py` knows to skip it
(it only downloads works that have an id). Minimum useful columns:

```
author,author_folder,series,series_number,title,genre,original_publication_year,work_type,chapter_count,word_count,markdown_path,raw_source_path,project_gutenberg_id,source_url
Your Pen Name,authors/your-slug,,,The Book Title,cozy romance,2024,novel,,,authors/your-slug/works/01-the-book-title.md,,,
```

**c. Add yourself to `registry.json`:**

```json
"your-slug": {
  "slug": "your-slug",
  "name": "Your Pen Name",
  "short": "You",
  "genre": "Cozy romance",
  "period": "2020–2025",
  "caution": "Whatever a reader of the numbers needs to know — mixed POV across books, a novella that skews the averages, learner-stage drafts, etc.",
  "single_author": true
}
```

Then `python3 scripts/build_stylo_profiles.py`. Your style card lands at
`authors/your-slug/profile/`. Check a draft with
`python3 scripts/stylo_check.py draft.md --author your-slug`.

Keep the reference authors in place while you do this. They cost nothing to
carry and they are what makes your profile's "unusual for you" numbers mean
anything — distinctiveness is measured *against the whole set*.

---

## 7. Add another public-domain contrast author

Same three steps as §6, but the works come from Project Gutenberg:

1. Add a `registry.json` entry for the author.
2. Add a `catalog.csv` row per work, each with its **Gutenberg ebook id** (the
   number in the ebook's URL) and a `markdown_path` under `authors/<slug>/works/`.
3. `python3 scripts/fetch_corpus.py --author <slug>` to download and convert,
   then `python3 scripts/build_stylo_profiles.py`.

**Look at what the converter produced.** It gets ordinary chapter-per-heading
novels right on its own. Collections of short pieces, translated editions, and
books with a long title page or an appendix may carry non-prose text into the
profile. When they do, open the converted `.md`, find the line where the real
prose starts (and stops), and add a `WORK_FILTERS` line-range trim in
`scripts/stylo/corpus.py` — there's a worked example in that file — or set
`EXCLUDED_WORKS` to drop a whole file (verse, an essay) from the profile while
keeping it in the folder.

> **Public-domain caution.** These authors are used here on a U.S.
> publication-year basis (works published before ~1930). Copyright terms differ
> by country and change every January. Confirm a work's status where you are
> before you add it.

---

## 8. What gets measured

About ninety features in a dozen families. You never set these by hand; the
build derives them and the check compares against them.

| Family | Examples |
|---|---|
| Sentence rhythm | length distribution, percentiles, variation, longest runs, adjacent deltas |
| Paragraph rhythm | words and sentences per paragraph, one-sentence rate, short/long runs |
| Dialogue architecture | speech share, utterance length, tags, action beats, interruptions |
| Punctuation | every mark per 1,000 words, **counted separately in narration and dialogue** |
| Function words | articles, pronouns, coordinators, subordinators, and more |
| Pronouns & POV | person, gender, number, names-to-pronouns ratio |
| Lexical texture | type/token variety (MATTR, MTLD), filter phrases, crutch phrases |

Reliability is marked in every report so you always know how much to trust a
number: `~` means a rule-based estimate (the toolkit has no grammar parser), and
`≈` means a lexicon proxy. Both are directional — good in bulk, wrong on the odd
hard case — never treat one flag on a short passage as a verdict.

---

## 9. Using it in a drafting loop

The style card steers *before* you draft; the check pays off *after*.

1. Paste the target's **style card** (`authors/<slug>/profile/<slug>-style-card.md`)
   into your drafting prompt. It's deliberately short — ranges and tendencies,
   not quotas. A model handed a hundred exact numbers starts performing the
   statistics instead of writing.
2. Draft a scene or a ~2,000-word chunk.
3. Run `stylo_check.py` on it. Feed **only the drifting passages plus the rewrite
   brief** back for a targeted rewrite — not the whole scene.
4. Re-check. Stop when it's in lane *and* it reads well to you. The tool can
   confirm the first; only you can confirm the second.

---

## 10. Honest limits

- **It measures surfaces.** Never subtext, irony, freshness, or whether a scene
  earns its ending. It flags candidates for a human reader; it does not judge.
- **Delta and n-grams recognise; they do not steer.** The "which author is this
  closest to" number belongs in the checker, never in a writing prompt.
- **Short passages are noisy.** Lanes are built from ~2,000-word chunks.
  Distribution features (percentiles, longest runs) wobble on anything much
  shorter, and the report says so.
- **A raw profile is a floor, not a ceiling.** It captures the instrument. Your
  executed voice — the song — still needs your own best-edited pages layered on
  top, and your own eye.

---

## 11. Credit, and what's yours

The approach here was **deeply inspired by Future Fiction Academy's stylometry
class** — that is where these ideas came from, and the debt is gladly
acknowledged. What lives in this repository, though, is an independent,
from-scratch build: the engine is original code implementing **classic, public
stylometry** — Burrows's Delta, function-word frequency analysis, the standard
authorship features — in nothing but Python's standard library, and this manual
is written fresh. **None of FFA's course materials are reproduced or included
here.**

The reference texts are **Project Gutenberg** public-domain editions, fetched by
you at build time from the ids in `catalog.csv`.

Nothing you add — your own prose, your own pen's profile — is shared by using
this. It all stays in your copy. Measure, build, check: all of it is local.
