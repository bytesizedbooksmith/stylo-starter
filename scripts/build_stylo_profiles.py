#!/usr/bin/env python3
"""Build every author profile, report, style card and index from the corpus.

    python3 scripts/build_stylo_profiles.py

Reads the Markdown in ``authors/*/works/``. Writes to ``authors/*/profile/``
and ``stylometry/``. Never modifies a source manuscript.

Standard library only - no spaCy, no numpy, no pandas, nothing to install.
The trade-off is documented in every report: syntax features are rule-based
estimates rather than parser output.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stylo import delta as delta_mod
from stylo.corpus import AUTHORS, ROOT, Chunk, Work, build_chunks, load_catalog
from stylo.features import PRIMARY_METRICS, REGISTRY, measure, percentile, tag_counter
from stylo.profile import (
    AuthorProfile,
    WorkSummary,
    apply_distinctiveness,
    attribution_report,
    build_delta_model,
    build_lanes,
    pov_note,
    signature_phrases,
    signature_words,
    work_narration,
)
from stylo.report import render_report, render_style_card
from stylo.segment import tokens, word_count

MFW_COUNT = 150
NGRAM_KEYS = 1000
CHUNK_WORDS = 2000
TRIGRAM_PRUNE_AT = 400_000

STYLOMETRY = ROOT / "stylometry"
REFERENCE = STYLOMETRY / "reference"


def log(message: str) -> None:
    print(message, flush=True)


# ---------------------------------------------------------------------------
# Pass 1: measure
# ---------------------------------------------------------------------------


def collect(catalog: list[Work]) -> dict[str, dict]:
    """Chunk and measure every included work, author by author."""
    data: dict[str, dict] = {}
    for slug, meta in AUTHORS.items():
        works = [w for w in catalog if w.author_slug == slug]
        entry: dict = {
            "meta": meta,
            "chunks": [],
            "works": [],
            "tags": Counter(),
            "trigrams": Counter(),
            "names": set(),
        }
        for work in works:
            if not work.included:
                entry["works"].append(
                    WorkSummary(
                        title=work.title, year=work.year, words=0, chunks=0,
                        included=False, note=work.exclusion_reason,
                    )
                )
                continue

            document = work.load()
            names = document.proper_names()
            entry["names"].update(names)
            chunks = build_chunks(work, target_words=CHUNK_WORDS)
            for chunk in chunks:
                chunk.metrics = measure(chunk.paragraphs, names)
                chunk.tokens = tokens(chunk.text)
                entry["chunks"].append(chunk)
                entry["tags"].update(tag_counter(chunk.paragraphs))
                toks = chunk.tokens
                entry["trigrams"].update(
                    tuple(toks[i:i + 3]) for i in range(max(0, len(toks) - 2))
                )
            if len(entry["trigrams"]) > TRIGRAM_PRUNE_AT:
                entry["trigrams"] = Counter(
                    {g: c for g, c in entry["trigrams"].items() if c > 1}
                )

            work_metrics = {
                key: float(median([c.metrics[key] for c in chunks]))
                for key in REGISTRY
            } if chunks else {}
            entry["works"].append(
                WorkSummary(
                    title=work.title,
                    year=work.year,
                    words=document.word_count,
                    chunks=len(chunks),
                    included=True,
                    note=work.filter_reason,
                    work_type=work.work_type,
                    narration=work_narration(
                        work_metrics.get("narr_first_person_per_1k", 0.0),
                        work.work_type,
                    ),
                    metrics=work_metrics,
                )
            )
            log(f"  {meta.short:12} {work.title[:44]:46} "
                f"{document.word_count:>7,} words  {len(chunks):>3} chunks")
        data[slug] = entry
    return data


# ---------------------------------------------------------------------------
# Pass 2: cross-corpus recognition model
# ---------------------------------------------------------------------------


def build_reference(data: dict[str, dict]) -> tuple[delta_mod.Standardiser, list[str]]:
    """Fit the shared Delta space and character n-gram key set.

    Both are fitted across *all* authors: standardising against the whole
    collection is what makes a per-author z-score mean "unusual here".
    """
    all_chunks = [c for entry in data.values() for c in entry["chunks"]]
    mfw = delta_mod.most_frequent_words([c.tokens for c in all_chunks], MFW_COUNT)
    vectors = [delta_mod.frequency_vector(c.tokens, mfw) for c in all_chunks]
    standardiser = delta_mod.Standardiser.fit(vectors, mfw)

    total: Counter[str] = Counter()
    for chunk in all_chunks:
        total.update(delta_mod.char_ngrams(chunk.text, 4))
    keys = [gram for gram, _ in total.most_common(NGRAM_KEYS)]
    return standardiser, keys


# ---------------------------------------------------------------------------
# Pass 3: profiles
# ---------------------------------------------------------------------------


def build_profiles(
    data: dict[str, dict],
    standardiser: delta_mod.Standardiser,
    ngram_keys: list[str],
) -> tuple[dict[str, AuthorProfile], dict]:
    corpus_trigrams: Counter = Counter()
    for entry in data.values():
        corpus_trigrams.update(entry["trigrams"])
    corpus_trigram_total = sum(corpus_trigrams.values()) or 1

    profiles: dict[str, AuthorProfile] = {}
    z_by_slug: dict[str, list[list[float]]] = {}
    for slug, entry in data.items():
        meta = entry["meta"]
        chunks: list[Chunk] = entry["chunks"]
        included = [w for w in entry["works"] if w.included]

        book_medians: dict[str, list[float]] = {
            key: [w.metrics[key] for w in included if key in w.metrics]
            for key in REGISTRY
        }
        lanes = build_lanes(chunks, book_medians)

        z_vectors = [standardiser.z_from_tokens(c.tokens) for c in chunks]
        z_by_slug[slug] = z_vectors
        ngram_vectors = [
            delta_mod.ngram_vector(delta_mod.char_ngrams(c.text, 4), ngram_keys)
            for c in chunks
        ]
        delta_model = build_delta_model(z_vectors, ngram_vectors)

        dialogue_values = sorted(c.metrics["dialogue_word_pct"] for c in chunks)
        quarter = max(1, len(dialogue_values) // 4)
        top = dialogue_values[-quarter:]
        bottom = dialogue_values[:quarter]

        author_trigram_total = sum(entry["trigrams"].values()) or 1
        profile = AuthorProfile(
            slug=slug,
            name=meta.name,
            genre=meta.genre,
            period=meta.period,
            single_author=meta.single_author,
            caution=meta.caution,
            words_profiled=sum(w.words for w in included),
            chunk_count=len(chunks),
            chunk_target_words=CHUNK_WORDS,
            lanes=lanes,
            works=entry["works"],
            delta=delta_model,
            signature_words=signature_words(delta_model.centroid, standardiser.mfw),
            signature_phrases=signature_phrases(
                entry["trigrams"], author_trigram_total,
                corpus_trigrams, corpus_trigram_total,
                entry["names"],
            ),
            dialogue_heavy_lane=(percentile(top, 25), percentile(top, 75)),
            narration_heavy_lane=(percentile(bottom, 25), percentile(bottom, 75)),
            top_tags=entry["tags"].most_common(12),
        )
        profile.pov_note = pov_note(lanes, entry["works"])
        profiles[slug] = profile

    apply_distinctiveness(profiles)
    return profiles, attribution_report(z_by_slug)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def write_chunk_csv(path: Path, chunks: list[Chunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(REGISTRY)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["work", "chunk_index", "chapter", "words", *keys])
        for chunk in chunks:
            writer.writerow(
                [chunk.work_title, chunk.index, chunk.chapter, chunk.words,
                 *[f"{chunk.metrics[k]:.4f}" for k in keys]]
            )


def write_work_csv(path: Path, works: list[WorkSummary]) -> None:
    keys = list(REGISTRY)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["title", "year", "words", "chunks", *keys])
        for work in works:
            if not work.included:
                continue
            writer.writerow(
                [work.title, work.year, work.words, work.chunks,
                 *[f"{work.metrics.get(k, 0.0):.4f}" for k in keys]]
            )


def write_author_outputs(profile: AuthorProfile, chunks: list[Chunk]) -> None:
    folder = ROOT / "authors" / profile.slug / "profile"
    folder.mkdir(parents=True, exist_ok=True)
    from stylo.html_report import markdown_page
    report_md = render_report(profile)
    card_md = render_style_card(profile)
    (folder / f"{profile.slug}-stylometry-report.html").write_text(
        markdown_page(f"{profile.name} — measured profile", report_md), encoding="utf-8")
    (folder / f"{profile.slug}-style-card.html").write_text(
        markdown_page(f"{profile.name} — provisional style card",
            "> Author review needed. Observed patterns are not automatically preferred targets.\n\n" + card_md), encoding="utf-8")
    profile.save(folder / "profile.json")
    write_chunk_csv(folder / "chunk-metrics.csv", chunks)
    write_work_csv(folder / "work-metrics.csv", profile.works)
    (folder / f"{profile.slug}-stylometry-report.md").write_text(
        render_report(profile), encoding="utf-8"
    )
    (folder / f"{profile.slug}-style-card.md").write_text(
        render_style_card(profile), encoding="utf-8"
    )


def write_reference(
    profiles: dict[str, AuthorProfile],
    standardiser: delta_mod.Standardiser,
    ngram_keys: list[str],
) -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    model = {
        "description": (
            "Shared Burrows's Delta space and character 4-gram key set, fitted "
            "across every included chunk of all authors. stylo_check.py "
            "loads this to place a draft in the same space."
        ),
        "mfw_count": MFW_COUNT,
        "chunk_target_words": CHUNK_WORDS,
        "standardiser": standardiser.to_dict(),
        "ngram_keys": ngram_keys,
        "authors": {
            slug: {
                "name": p.name,
                "centroid": p.delta.centroid,
                "loo_median": p.delta.loo_median,
                "loo_p90": p.delta.loo_p90,
                "loo_max": p.delta.loo_max,
                "ngram_centroid": p.delta.ngram_centroid,
                "ngram_loo_median": p.delta.ngram_loo_median,
                "ngram_loo_p10": p.delta.ngram_loo_p10,
                "ngram_loo_min": p.delta.ngram_loo_min,
            }
            for slug, p in profiles.items()
        },
    }
    (REFERENCE / "delta-model.json").write_text(
        json.dumps(model), encoding="utf-8"
    )

    # Cross-author medians, one row per metric.
    with (REFERENCE / "cross-author-metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        slugs = list(profiles)
        writer.writerow(["metric", "family", "reliability", "promptable", *slugs])
        for key, metric in REGISTRY.items():
            writer.writerow(
                [key, metric.family, metric.reliability, int(metric.promptable),
                 *[f"{profiles[s].lanes[key].median:.4f}" if key in profiles[s].lanes
                   else "" for s in slugs]]
            )

    # Author-to-author Delta distance matrix.
    with (REFERENCE / "delta-matrix.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        slugs = list(profiles)
        writer.writerow(["author", *slugs])
        for a in slugs:
            row = [a]
            for b in slugs:
                distance = delta_mod.delta_distance(
                    profiles[a].delta.centroid, profiles[b].delta.centroid
                )
                row.append(f"{distance:.4f}")
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", choices=sorted(AUTHORS), help="write this author profile only; shared reference still requires all configured sources")
    args = parser.parse_args()

    if not AUTHORS:
        parser.error("No authors are configured. For a first try, use scripts/stylo_explore.py --demo.")
    try:
        catalog = load_catalog()
    except (OSError, UnicodeError, KeyError, ValueError) as error:
        parser.error(f"Cannot read the source catalog: {error}. The no-download demo is scripts/stylo_explore.py --demo.")
    missing = [w.rel_path for w in catalog if w.included and w.author_slug in AUTHORS and not w.path.is_file()]
    empty = [slug for slug in AUTHORS if not any(w.author_slug == slug and w.included for w in catalog)]
    if missing or empty:
        details = "; ".join(["missing sources: " + ", ".join(missing[:3])] if missing else [])
        if empty:
            details += "; no included works for: " + ", ".join(empty)
        parser.error("The full profile build needs its configured source collection. " + details +
                     ". Nothing was downloaded. Use scripts/stylo_explore.py --demo for a first try; see guide/profiles.html for optional profile setup.")
    log("Measuring corpus…")
    data = collect(catalog)

    log("Fitting shared Delta space…")
    standardiser, ngram_keys = build_reference(data)

    log("Building profiles…")
    profiles, attribution = build_profiles(data, standardiser, ngram_keys)
    log(f"  leave-one-out attribution: {attribution['correct']}/"
        f"{attribution['chunks']} chunks "
        f"({attribution['accuracy'] * 100:.1f}%) — chance is "
        f"{attribution['baseline'] * 100:.1f}%")

    log("Writing outputs…")
    for slug, profile in profiles.items():
        if args.author and slug != args.author:
            continue
        write_author_outputs(profile, data[slug]["chunks"])
        log(f"  authors/{slug}/profile/")

    write_reference(profiles, standardiser, ngram_keys)
    log(f"  stylometry/reference/")

    from build_stylo_indexes import write_indexes  # local import: shares the profiles

    write_indexes(profiles, attribution)
    log("  stylometry/INDEX.md")
    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
