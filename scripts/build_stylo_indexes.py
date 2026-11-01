#!/usr/bin/env python3
"""Write the master index and the cross-author comparison.

Called at the end of ``build_author_profiles.py``. The index is the entry
point for both readers and machines: a script that wants a lane should be able
to start at ``stylometry/index.json`` and never guess at a path.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from stylo import delta as delta_mod
from stylo.corpus import ROOT
from stylo.features import REGISTRY
from stylo.profile import AuthorProfile
from stylo.voice_notes import notes_for

STYLOMETRY = ROOT / "stylometry"

#: The comparison table's spine. Enough to see the authors separate, short
#: enough to read on one screen.
COMPARISON_METRICS = (
    "narr_sent_median",
    "sent_cv",
    "sent_very_short_pct",
    "sent_long_pct",
    "para_median_words",
    "para_one_sentence_narration_pct",
    "dialogue_word_pct",
    "utterance_median_words",
    "tag_said_pct",
    "narr_comma_per_1k",
    "narr_semicolon_per_1k",
    "narr_emdash_per_1k",
    "narr_exclamation_per_1k",
    "subordinate_sentence_pct",
    "narr_first_person_per_1k",
    "narr_third_person_per_1k",
    "mattr_50",
    "lexical_density",
    "long_word_pct",
    "sensory_per_1k",
    "emotion_label_per_1k",
    "abstract_noun_per_1k",
    "filter_phrase_per_1k",
)


def _rel(path: Path, start: Path) -> str:
    import os
    return os.path.relpath(path, start)


# ---------------------------------------------------------------------------
# Machine index
# ---------------------------------------------------------------------------


def write_machine_index(profiles: dict[str, AuthorProfile], attribution: dict) -> None:
    """``stylometry/index.json`` — the one file a script needs to find."""
    payload = {
        "schema": "stylometry-index/1",
        "generated_on": date.today().isoformat(),
        "generated_by": "scripts/build_author_profiles.py",
        "root_relative_paths": True,
        "description": (
            "Index of author style profiles built from the public-domain corpus "
            "in authors/*/works/. Each author has a machine profile (profile.json) "
            "carrying per-feature lanes, a compact style card for prompting, and "
            "a full report. Load profile.json to audit prose; load the style card "
            "to steer generation."
        ),
        "usage": {
            "audit_a_draft": "python3 scripts/check_prose.py DRAFT.md --author SLUG",
            "audit_json": "python3 scripts/check_prose.py DRAFT.md --author SLUG --json",
            "rebuild": "python3 scripts/build_author_profiles.py",
            "python_api": (
                "from stylo.profile import AuthorProfile; "
                "p = AuthorProfile.load('authors/SLUG/profile/profile.json'); "
                "lane = p.lanes['narr_sent_median']; lane.verdict(14.0)"
            ),
        },
        "validation": attribution,
        "shared_reference": {
            "delta_model": "stylometry/reference/delta-model.json",
            "cross_author_metrics": "stylometry/reference/cross-author-metrics.csv",
            "delta_matrix": "stylometry/reference/delta-matrix.csv",
        },
        "metric_registry": {
            key: {
                "label": metric.label,
                "family": metric.family,
                "unit": metric.unit,
                "reliability": metric.reliability,
                "promptable": metric.promptable,
            }
            for key, metric in REGISTRY.items()
        },
        "authors": {},
    }
    for slug, profile in profiles.items():
        notes = notes_for(slug)
        payload["authors"][slug] = {
            "name": profile.name,
            "genre": profile.genre,
            "period": profile.period,
            "single_author": profile.single_author,
            "style_lane": notes["lane"],
            "scene_types": notes["scenes"],
            "words_profiled": profile.words_profiled,
            "chunks": profile.chunk_count,
            "pov": profile.pov_note,
            "caution": profile.caution,
            "paths": {
                "profile_json": f"authors/{slug}/profile/profile.json",
                "style_card": f"authors/{slug}/profile/{slug}-style-card.md",
                "report": f"authors/{slug}/profile/{slug}-stylometry-report.md",
                "chunk_metrics_csv": f"authors/{slug}/profile/chunk-metrics.csv",
                "work_metrics_csv": f"authors/{slug}/profile/work-metrics.csv",
                "works_folder": f"authors/{slug}/works/",
            },
            "hard_targets": [
                {
                    "key": lane.key,
                    "label": REGISTRY[lane.key].label,
                    "median": round(lane.median, 3),
                    "normal_lane": [round(lane.p25, 3), round(lane.p75, 3)],
                    "distinct_z": round(lane.distinct_z or 0, 2),
                }
                for lane in sorted(
                    profile.hard_targets(),
                    key=lambda l: abs(l.distinct_z or 0),
                    reverse=True,
                )[:10]
            ],
        }
    (STYLOMETRY / "index.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Human index
# ---------------------------------------------------------------------------


def write_index_md(profiles: dict[str, AuthorProfile], attribution: dict) -> None:
    out: list[str] = []
    add = out.append

    add("---")
    add("type: stylometry-index")
    add("schema: stylometry-index/1")
    add(f"authors: {len(profiles)}")
    add("machine_index: index.json")
    add("generated_by: scripts/build_author_profiles.py")
    add(f"generated_on: {date.today().isoformat()}")
    add("---")
    add("")
    add("# Stylometry Index")
    add("")
    add("Style profiles for the authors in `authors/`. Each "
        "profile is built from that author's own Markdown works and describes "
        "the author's **lane** — a median, a normal range, and a wider "
        "acceptable range for every feature — rather than a single average.")
    add("")
    add("> **Generated.** Rebuild everything with "
        "`python3 scripts/build_author_profiles.py`. Hand edits to any file "
        "listed below will be overwritten. Curated craft notes live in "
        "`scripts/stylo/voice_notes.py`; they survive rebuilds.")
    add("")

    add("## Start here")
    add("")
    add("| I want to… | Use |")
    add("|---|---|")
    add("| **Steer a model before it writes** | the author's **style card** — "
        "10–18 controls, short enough to paste into a prompt |")
    add("| **Check prose that has been written** | "
        "`python3 scripts/check_prose.py draft.md --author SLUG` |")
    add("| **Read the evidence behind a number** | the author's **report** |")
    add("| **Load lanes from a script** | `index.json`, then each author's "
        "`profile.json` |")
    add("| **Compare authors** | "
        "[CROSS-AUTHOR-COMPARISON.md](CROSS-AUTHOR-COMPARISON.md) |")
    add("| **Understand the method** | [README.md](README.md) and "
        "[the guide](../STYLOMETRY_FOR_AI_FICTION_GUIDE.md) |")
    add("")

    add("## Authors")
    add("")
    add("| Author | Style lane | Words | Chunks | Card | Report | Data |")
    add("|---|---|---:|---:|---|---|---|")
    for slug, profile in sorted(profiles.items(), key=lambda kv: kv[1].name):
        notes = notes_for(slug)
        base = f"../authors/{slug}/profile"
        flag = "" if profile.single_author else " ⚠︎"
        add(
            f"| **{profile.name}**{flag} | {notes['lane']} "
            f"| {profile.words_profiled:,} | {profile.chunk_count} "
            f"| [card]({base}/{slug}-style-card.md) "
            f"| [report]({base}/{slug}-stylometry-report.md) "
            f"| [json]({base}/profile.json) · "
            f"[csv]({base}/chunk-metrics.csv) |"
        )
    add("")
    add("⚠︎ **Publishing byline, not a person.** Nancy Drew and the Hardy Boys "
        "were produced by the Stratemeyer Syndicate. Those two profiles describe "
        "a *house style* — which is real, learnable and unusually consistent, "
        "but is not one writer's signature.")
    add("")

    add("## Point of view, measured")
    add("")
    add("| Author | Narration | Speech share (median) | Median narration sentence |")
    add("|---|---|---:|---:|")
    for slug, profile in sorted(profiles.items(), key=lambda kv: kv[1].name):
        add(f"| {profile.name} | {profile.pov_note} "
            f"| {profile.lanes['dialogue_word_pct'].median:.0f}% "
            f"| {profile.lanes['narr_sent_median'].median:.0f} words |")
    add("")

    add("## What each file is")
    add("")
    add("```text")
    add("authors/<slug>/profile/")
    add("├── <slug>-style-card.md        compact controls — paste into a writing prompt")
    add("├── <slug>-stylometry-report.md full evidence — lanes, stability, limits")
    add("├── profile.json                machine profile — every lane, Delta centroid")
    add("├── chunk-metrics.csv           one row per ~2,000-word chunk")
    add("└── work-metrics.csv            one row per book")
    add("")
    add("stylometry/")
    add("├── INDEX.md                    this file")
    add("├── index.json                  machine index — paths, lanes, hard targets")
    add("├── CROSS-AUTHOR-COMPARISON.md  how the authors differ")
    add("├── README.md                   how the toolkit works")
    add("└── reference/")
    add("    ├── delta-model.json        shared Burrows's Delta space")
    add("    ├── cross-author-metrics.csv  every metric × every author")
    add("    └── delta-matrix.csv        author-to-author Delta distances")
    add("```")
    add("")

    add("## The loop this supports")
    add("")
    add("```text")
    add("style card ──▶ AI drafts a scene ──▶ check_prose.py measures it locally")
    add("                     ▲                          │")
    add("                     │                          ▼")
    add("             rewrite brief ◀──────── only the drifting passages")
    add("```")
    add("")
    add("Python reads the whole manuscript for free. The model only ever sees the "
        "style card, the flagged passage, and a short brief — never the corpus, "
        "never the whole draft again.")
    add("")

    add("## Does it work?")
    add("")
    add(f"On every rebuild, all {attribution['chunks']:,} passages in the corpus "
        f"are attributed by nearest author centroid, leave-one-out. "
        f"**{attribution['accuracy'] * 100:.1f}%** land on the author who "
        f"actually wrote them, against a {attribution['baseline'] * 100:.1f}% "
        f"chance baseline. Per-author results are in "
        f"[CROSS-AUTHOR-COMPARISON.md](CROSS-AUTHOR-COMPARISON.md).")
    add("")
    add("That validates **recognition**, which is the narrow thing it "
        "validates. It says the lanes are built on a signal that really "
        "separates these authors. It says nothing about whether prose written "
        "to a lane is any good.")
    add("")

    add("## Honest limits")
    add("")
    add("- Features marked `~` in a report are **rule-based estimates**, not "
        "parser output — this toolkit has no dependencies, which is a deliberate "
        "trade. Tense, passive voice and tag attribution are the softest of them.")
    add("- Features marked `≈` are **lexicon proxies**. Counting sensory words is "
        "not the same as measuring sensory writing.")
    add("- Burrows's Delta and character n-grams **recognise** style; they cannot "
        "steer it. They belong in the checker, never in a writing prompt.")
    add("- No measurement here reaches subtext, irony, or whether a scene earns "
        "its climax. Those need a reader.")
    add("- These are **contrast authors and craft components**. If the goal is to "
        "write like you, your own finished books are the primary corpus; these "
        "others are genre history and alternative lanes.")
    add("")
    (STYLOMETRY / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-author comparison
# ---------------------------------------------------------------------------


def _attribution_section(
    profiles: dict[str, AuthorProfile], attribution: dict
) -> list[str]:
    """The self-check: can any of this actually tell the authors apart?"""
    lines = [
        "## Does the recognition actually work?",
        "",
        "A fair test, run on every rebuild. Take each of the "
        f"{attribution['chunks']:,} passages in the corpus and ask which of the "
        "author centroids it is closest to — scoring each passage against "
        "its own author's centre **with that passage removed**, so nothing is "
        "graded against itself.",
        "",
        f"> **{attribution['correct']:,} of {attribution['chunks']:,} passages "
        f"({attribution['accuracy'] * 100:.1f}%) are attributed to the author "
        f"who wrote them.** Chance would be "
        f"{attribution['baseline'] * 100:.1f}%.",
        "",
        "This is why the thresholds in each report mean something. It is also "
        "the ceiling on what the validators can claim: they recognise, and they "
        "recognise well, but a recognition score still cannot tell a draft what "
        "to change.",
        "",
        "| Author | Attributed correctly | Accuracy | Most often mistaken for |",
        "|---|---:|---:|---|",
    ]
    order = sorted(
        attribution["per_author"].items(),
        key=lambda kv: kv[1]["accuracy"],
        reverse=True,
    )
    for slug, row in order:
        confused = row["most_confused_with"]
        confused_name = profiles[confused].name if confused in profiles else "—"
        lines.append(
            f"| {profiles[slug].name} | {row['correct']}/{row['chunks']} "
            f"| {row['accuracy'] * 100:.1f}% | {confused_name} |"
        )
    lines.append("")
    worst = order[-1]
    lines.append(
        f"The weakest is {profiles[worst[0]].name} at "
        f"{worst[1]['accuracy'] * 100:.1f}%, which is a finding rather than a "
        "fault: the authors who lose passages are the ones whose corpora mix "
        "narrators, registers or decades. A profile built across two lanes is "
        "a wider target than one built across a single lane."
    )
    lines.append("")
    return lines


def write_comparison(profiles: dict[str, AuthorProfile], attribution: dict) -> None:
    slugs = sorted(profiles, key=lambda s: profiles[s].name)
    shorts = {slug: profiles[slug].name.split()[-1] for slug in slugs}

    out: list[str] = []
    add = out.append
    add("---")
    add("type: cross-author-comparison")
    add(f"authors: {len(profiles)}")
    add("generated_by: scripts/build_author_profiles.py")
    add(f"generated_on: {date.today().isoformat()}")
    add("---")
    add("")
    add("# Cross-Author Comparison")
    add("")
    add("How the authors separate. Every cell is the author's **median "
        "across their own ~2,000-word chunks**. Use this to pick contrast "
        "authors, to build hybrid craft lanes, or to see which features actually "
        "distinguish anyone.")
    add("")
    add("> These authors span 1895–1930 and several genres, and two of them are "
        "syndicate bylines. **Do not blend them into one generic \"good fiction\" "
        "profile.** The differences below are the point.")
    add("")

    add("## Feature medians")
    add("")
    header = "| Feature | " + " | ".join(shorts[s] for s in slugs) + " |"
    add(header)
    add("|---" * (len(slugs) + 1) + "|")
    for key in COMPARISON_METRICS:
        metric = REGISTRY[key]
        cells = []
        for slug in slugs:
            lane = profiles[slug].lanes.get(key)
            cells.append(metric.format(lane.median) if lane else "—")
        add(f"| {metric.label} | " + " | ".join(cells) + " |")
    add("")
    add("Full table, every metric: "
        "[`reference/cross-author-metrics.csv`](reference/cross-author-metrics.csv).")
    add("")

    add("## Burrows's Delta between authors")
    add("")
    add("Distance between author centroids in the shared 150-most-frequent-word "
        "space. Larger means more different. This measures **recognition**, not "
        "quality or influence — and it is the one number here that should never "
        "go into a writing prompt.")
    add("")
    add("| | " + " | ".join(shorts[s] for s in slugs) + " |")
    add("|---" * (len(slugs) + 1) + "|")
    for a in slugs:
        cells = []
        for b in slugs:
            if a == b:
                cells.append("—")
                continue
            distance = delta_mod.delta_distance(
                profiles[a].delta.centroid, profiles[b].delta.centroid
            )
            cells.append(f"{distance:.2f}")
        add(f"| **{shorts[a]}** | " + " | ".join(cells) + " |")
    add("")

    add("### Nearest and furthest neighbour")
    add("")
    add("| Author | Closest | Distance | Furthest | Distance |")
    add("|---|---|---:|---|---:|")
    for a in slugs:
        distances = sorted(
            (
                (
                    delta_mod.delta_distance(
                        profiles[a].delta.centroid, profiles[b].delta.centroid
                    ),
                    shorts[b],
                )
                for b in slugs
                if b != a
            )
        )
        add(f"| {profiles[a].name} | {distances[0][1]} | {distances[0][0]:.2f} "
            f"| {distances[-1][1]} | {distances[-1][0]:.2f} |")
    add("")

    out.extend(_attribution_section(profiles, attribution))

    add("## Where each author is most extreme")
    add("")
    add("The single feature on which each author sits furthest from the other "
        "eight, among features that are also stable across their own books.")
    add("")
    add("| Author | Most distinctive stable feature | Value | Distance |")
    add("|---|---|---:|---:|")
    for slug in slugs:
        profile = profiles[slug]
        candidates = [
            lane for lane in profile.lanes.values()
            if lane.stability == "stable" and lane.distinct_z is not None
        ]
        if not candidates:
            add(f"| {profile.name} | *(nothing stable and distinctive)* | — | — |")
            continue
        best = max(candidates, key=lambda l: abs(l.distinct_z or 0))
        metric = REGISTRY[best.key]
        add(f"| {profile.name} | {metric.label} | {metric.format(best.median)} "
            f"| {best.distinct_z:+.1f} σ |")
    add("")

    add("## Building a hybrid craft lane")
    add("")
    add("The guide's example is a lane weighted across three authors:")
    add("")
    add("```text")
    add("Target craft lane:")
    add("- 45% Edith Wharton: social observation and syntactic layering")
    add("- 30% Agatha Christie: dialogue movement and information control")
    add("- 25% E. Nesbit: narrative warmth and ensemble energy")
    add("```")
    add("")
    add("Build that by **taking compatible measurements from each profile**, not "
        "by averaging the corpora. Concretely: take the syntax and punctuation "
        "lanes from Wharton, the dialogue architecture from Christie, and the "
        "narrator's stance from Nesbit — then check the result against each "
        "source lane separately:")
    add("")
    add("```bash")
    add("python3 scripts/check_prose.py draft.md --author edith-wharton \\")
    add("    --families syntax,punctuation")
    add("python3 scripts/check_prose.py draft.md --author agatha-christie \\")
    add("    --families dialogue")
    add("```")
    add("")
    add("Concatenating all the authors and averaging would produce a profile "
        "that describes nobody: Wharton's semicolons and Dixon's exclamation "
        "marks cancel out into a lane neither author ever wrote in.")
    add("")
    (STYLOMETRY / "CROSS-AUTHOR-COMPARISON.md").write_text(
        "\n".join(out) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Author READMEs
# ---------------------------------------------------------------------------

BEGIN = "<!-- stylometry:begin -->"
END = "<!-- stylometry:end -->"


def _readme_section(profile: AuthorProfile) -> str:
    slug = profile.slug
    notes = notes_for(slug)
    included = [w for w in profile.works if w.included]
    excluded = [w for w in profile.works if not w.included]

    lines = [
        BEGIN,
        "",
        "## Style profile",
        "",
        f"Built from {len(included)} work{'s' if len(included) != 1 else ''} in "
        f"[`works/`](works/) — {profile.words_profiled:,} words measured across "
        f"{profile.chunk_count} chunks of about 2,000 words.",
        "",
        f"- [**Style card**](profile/{slug}-style-card.md) — the compact controls "
        "to paste into a writing prompt",
        f"- [**Stylometry report**](profile/{slug}-stylometry-report.md) — the "
        "evidence: every lane, its stability, and its limits",
        f"- [`profile.json`](profile/profile.json) · "
        f"[`chunk-metrics.csv`](profile/chunk-metrics.csv) · "
        f"[`work-metrics.csv`](profile/work-metrics.csv)",
        "",
        f"**Style lane:** {notes['lane']}  ",
        f"**Narration (measured):** {profile.pov_note}",
        "",
    ]

    if excluded:
        lines.append(
            f"Not every work in `works/` is measured. Excluded here: "
            + ", ".join(f"*{w.title}*" for w in excluded)
            + " — see the report for why."
        )
        lines.append("")
    if profile.caution:
        lines.append(f"> **Note.** {profile.caution}")
        lines.append("")

    hard = sorted(
        profile.hard_targets(), key=lambda l: abs(l.distinct_z or 0), reverse=True
    )[:4]
    if hard:
        lines.append("Most distinctive habits that are also stable across their "
                     "own books:")
        lines.append("")
        lines.append("| Feature | Value | vs. the other eight authors |")
        lines.append("|---|---:|---:|")
        for lane in hard:
            metric = REGISTRY[lane.key]
            lines.append(
                f"| {metric.label} | {metric.format(lane.median)} "
                f"| {lane.distinct_z:+.1f} σ |"
            )
        lines.append("")

    lines += [
        "Check a draft against this author:",
        "",
        "```bash",
        f"python3 scripts/check_prose.py draft.md --author {slug}",
        "```",
        "",
        f"All authors: [`stylometry/INDEX.md`](../../stylometry/INDEX.md). "
        f"Regenerate: `python3 scripts/build_author_profiles.py --author {slug}`.",
        "",
        END,
    ]
    return "\n".join(lines)


def update_author_readmes(profiles: dict[str, AuthorProfile]) -> None:
    """Refresh the generated block in each author README, in place.

    The rest of the file is hand-written and is never touched: only the text
    between the two markers is replaced, so this stays in sync on every
    rebuild without eating anyone's prose.
    """
    for slug, profile in profiles.items():
        path = ROOT / "authors" / slug / "README.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        section = _readme_section(profile)
        if BEGIN in text and END in text:
            start = text.index(BEGIN)
            end = text.index(END) + len(END)
            text = text[:start] + section + text[end:]
        else:
            text = text.rstrip("\n") + "\n\n" + section + "\n"
        path.write_text(text, encoding="utf-8")


def write_indexes(profiles: dict[str, AuthorProfile], attribution: dict) -> None:
    STYLOMETRY.mkdir(parents=True, exist_ok=True)
    write_machine_index(profiles, attribution)
    write_index_md(profiles, attribution)
    write_comparison(profiles, attribution)
    update_author_readmes(profiles)
    from stylo.html_report import markdown_page
    import re
    from html import escape
    from urllib.parse import unquote
    for source in STYLOMETRY.glob("*.md"):
        html = markdown_page(source.stem, source.read_text(encoding="utf-8"))
        def human_link(match):
            target, label = match.group(1), match.group(2)
            if target.startswith(("https://", "http://", "#")):
                return match.group(0)
            changed = re.sub(r"\.md(?=#|$)", ".html", target)
            if (source.parent / unquote(changed.split("#")[0])).exists():
                return '<a href="' + changed + '">' + label + '</a>'
            return label + ' <span class="small">(not generated in this build)</span>'
        html = re.sub(r'<a href="([^"]+)">(.*?)</a>', human_link, html)
        source.with_suffix(".html").write_text(html, encoding="utf-8")
