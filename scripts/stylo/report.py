"""Markdown rendering: the full report and the compact style card.

Two audiences, deliberately kept apart, per sections 3 and 6 of the guide:

* The **report** is the evidence. Everything measured, with its lane, its
  stability across books, its distance from the other authors, and a plain
  statement of how much to trust it.
* The **style card** is what a model is actually given before it writes.
  Ten to eighteen controls, expressed as ranges and tendencies. If it grows
  into a spreadsheet the model starts performing the statistics instead of
  the prose, so the card stays short on purpose.
"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from .features import FAMILY_LABELS, REGISTRY, Metric
from .profile import AuthorProfile, Lane
from .voice_notes import notes_for

RELIABILITY_MARK = {"exact": "", "estimate": " ~", "proxy": " ≈"}

RELIABILITY_LEGEND = (
    "| Mark | Meaning |\n"
    "|---|---|\n"
    "| *(none)* | **Exact.** Deterministic counting. No interpretation involved. |\n"
    "| `~` | **Estimate.** A rule stands in for a parser. Reliable in bulk, wrong "
    "on individual hard cases (fragments, historical syntax, heavy dialect). |\n"
    "| `≈` | **Proxy.** A word list stands in for a judgement. Treat as a weak "
    "directional signal only. |\n"
)


def _fmt(metric: Metric, value: float | None) -> str:
    return metric.format(value)


def _digits(metric: Metric) -> int:
    return 0 if metric.unit == "%" and abs(0) == 0 else 2


def _range(metric: Metric, low: float, high: float) -> str:
    if metric.unit == "%":
        return f"{low:.1f}–{high:.1f}%"
    if metric.unit in {"ratio"}:
        return f"{low:.2f}–{high:.2f}"
    if metric.unit == "count":
        return f"{low:.1f}–{high:.1f}"
    return f"{low:.1f}–{high:.1f}"


def _distinct_cell(lane: Lane) -> str:
    if lane.distinct_z is None:
        return "—"
    direction = "high" if lane.distinct_z > 0 else "low"
    if not lane.distinctive:
        return f"{lane.distinct_z:+.1f} σ"
    return f"**{lane.distinct_z:+.1f} σ ({direction})**"


def _stability_cell(lane: Lane) -> str:
    if lane.book_cv is None:
        return "—"
    return f"{lane.stability} ({lane.book_cv:.2f})"


def _family_table(profile: AuthorProfile, family: str) -> str:
    rows = [
        "| Feature | Median | Normal lane (p25–p75) | Wide (p10–p90) | Across books | Stability (CV) | vs. other authors |",
        "|---|---:|---:|---:|---:|---|---:|",
    ]
    for key, metric in REGISTRY.items():
        if metric.family != family:
            continue
        lane = profile.lanes.get(key)
        if lane is None:
            continue
        label = metric.label + RELIABILITY_MARK[metric.reliability]
        rows.append(
            f"| {label} | {_fmt(metric, lane.median)} "
            f"| {_range(metric, lane.p25, lane.p75)} "
            f"| {_range(metric, lane.p10, lane.p90)} "
            f"| {_range(metric, lane.book_low, lane.book_high)} "
            f"| {_stability_cell(lane)} "
            f"| {_distinct_cell(lane)} |"
        )
    return "\n".join(rows)


def _notes_for_family(family: str) -> str:
    notes = []
    for key, metric in REGISTRY.items():
        if metric.family == family and metric.note:
            notes.append(f"- **{metric.label}** — {metric.note}")
    return "\n".join(notes)


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------


def render_report(profile: AuthorProfile) -> str:
    notes = notes_for(profile.slug)
    included = [w for w in profile.works if w.included]
    excluded = [w for w in profile.works if not w.included]
    hard = profile.hard_targets()

    out: list[str] = []
    add = out.append

    # Machine-readable header so a script can route on this file without
    # parsing the prose.
    add("---")
    add("type: stylometry-report")
    add(f"author: {profile.name}")
    add(f"slug: {profile.slug}")
    add(f"genre: {profile.genre}")
    add(f"period: {profile.period}")
    add(f"single_author: {str(profile.single_author).lower()}")
    add(f"words_profiled: {profile.words_profiled}")
    add(f"chunks: {profile.chunk_count}")
    add(f"chunk_target_words: {profile.chunk_target_words}")
    add(f"profile_json: profile.json")
    add(f"style_card: {profile.slug}-style-card.md")
    add(f"chunk_metrics_csv: chunk-metrics.csv")
    add(f"work_metrics_csv: work-metrics.csv")
    add(f"generated_by: scripts/build_stylo_profiles.py")
    add(f"generated_on: {date.today().isoformat()}")
    add("---")
    add("")
    add(f"# {profile.name} — Stylometry Report")
    add("")
    add(f"*{profile.genre} · {profile.period} · "
        f"{profile.words_profiled:,} words profiled in {profile.chunk_count} chunks "
        f"of about {profile.chunk_target_words:,} words each.*")
    add("")
    add("> **Generated file.** Every number here comes from "
        "`scripts/build_stylo_profiles.py` reading the Markdown in `works/`. "
        "Edits made by hand will be overwritten on the next build. The "
        "qualitative craft notes live in `scripts/stylo/voice_notes.py`.")
    add("")

    if profile.caution:
        add("## Read this first")
        add("")
        add(profile.caution)
        add("")

    # -- how to use -------------------------------------------------------
    add("## How to use this report")
    add("")
    add("This report is evidence, not a prompt. Do not paste it into a model — "
        "it is far too long and a model handed a hundred measurements starts "
        "performing the statistics instead of writing the prose.")
    add("")
    add(f"- **To steer a draft:** use [`{profile.slug}-style-card.md`]"
        f"({profile.slug}-style-card.md), which carries only the controls worth "
        "prompting on.")
    add("- **To check a draft:** run "
        f"`python3 scripts/check_prose.py <draft.md> --author {profile.slug}`. "
        "It measures the draft locally, compares it to the lanes below, and "
        "prints only the passages that drifted.")
    add("- **To read a specific habit:** find the family below and look at the "
        "*Normal lane* column.")
    add("")

    # -- corpus -----------------------------------------------------------
    add("## Corpus profiled")
    add("")
    add("| Work | Year | Words | Chunks | Narration | Notes |")
    add("|---|---:|---:|---:|---|---|")
    for work in included:
        add(f"| *{work.title}* | {work.year} | {work.words:,} | {work.chunks} "
            f"| {work.narration or '—'} | {work.note or '—'} |")
    add("")
    add("Narration is read per work from the rate of first-person pronouns in "
        "narration, which is sharply bimodal in this corpus. Where the column "
        "disagrees with itself from book to book, the author's pronoun and POV "
        "lanes are an average across two different modes — read them with that "
        "in mind.")
    add("")
    if excluded:
        add("### Excluded from this profile")
        add("")
        add("Present in the corpus folder, deliberately not measured here:")
        add("")
        for work in excluded:
            add(f"- ***{work.title}*** — {work.note}")
        add("")

    # -- reading the numbers ----------------------------------------------
    add("## Reading the numbers")
    add("")
    add("Each feature is reported as a **lane**, never as a single average:")
    add("")
    add("| Column | Meaning |")
    add("|---|---|")
    add("| **Median** | The middle of the author's own passages. |")
    add("| **Normal lane (p25–p75)** | Half of the author's passages sit here. "
        "This is the target. |")
    add("| **Wide (p10–p90)** | Eighty percent sit here. Outside this is a real "
        "departure worth flagging. |")
    add("| **Across books** | Lowest and highest *book* median. A wide spread "
        "means the author varies this by book, so a draft may too. |")
    add("| **Stability (CV)** | Coefficient of variation across books. "
        "≤0.15 stable · ≤0.30 moderate · above that variable. |")
    add("| **vs. other authors** | Standard deviations from the mean of all the other "
        "author medians. Bold marks ≥1σ — a genuine fingerprint rather than a "
        "trait every author here shares. |")
    add("")
    add("Trust marks on feature names:")
    add("")
    add(RELIABILITY_LEGEND)
    add("")

    # -- headline ---------------------------------------------------------
    add("## What makes this author measurably different")
    add("")
    if hard:
        add("These features are **stable across the author's own books** *and* "
            "**at least 1σ from the other eight authors** *and* expressible as a "
            "writing instruction. They are the ones worth holding a draft to:")
        add("")
        add("| Feature | This author | Cross-author distance | Normal lane |")
        add("|---|---:|---:|---:|")
        ranked = sorted(hard, key=lambda l: abs(l.distinct_z or 0), reverse=True)
        for lane in ranked[:14]:
            metric = REGISTRY[lane.key]
            add(f"| {metric.label} | {_fmt(metric, lane.median)} "
                f"| {lane.distinct_z:+.1f} σ "
                f"| {_range(metric, lane.p25, lane.p75)} |")
        add("")
    else:
        add("No feature clears all three bars for this author. That itself is a "
            "finding: this voice is defined by its combination of ordinary "
            "traits rather than by any single extreme habit.")
        add("")

    add(f"**Point of view (measured):** {profile.pov_note}.")
    add("")
    if profile.dialogue_heavy_lane[1]:
        add(f"**Dialogue varies by scene.** Across all passages the speech share "
            f"runs {profile.lanes['dialogue_word_pct'].p25:.0f}–"
            f"{profile.lanes['dialogue_word_pct'].p75:.0f}% (median "
            f"{profile.lanes['dialogue_word_pct'].median:.0f}%). But the "
            f"conversation-heavy quarter of passages runs "
            f"{profile.dialogue_heavy_lane[0]:.0f}–{profile.dialogue_heavy_lane[1]:.0f}%, "
            f"and the narration-heavy quarter runs "
            f"{profile.narration_heavy_lane[0]:.0f}–{profile.narration_heavy_lane[1]:.0f}%. "
            f"A confrontation and a reflective passage are not supposed to hit "
            f"the same number.")
        add("")

    # -- families ---------------------------------------------------------
    add("## Measurements by family")
    add("")
    for family, label in FAMILY_LABELS.items():
        add(f"### {label}")
        add("")
        add(_family_table(profile, family))
        add("")
        family_notes = _notes_for_family(family)
        if family_notes:
            add(family_notes)
            add("")

    # -- signature words --------------------------------------------------
    add("## Signature function words")
    add("")
    add("The interpretable end of Burrows's Delta: the most-frequent words this "
        "author uses most unlike the rest of the corpus, in standard deviations "
        "from the corpus mean. Read these as diagnosis, not as quotas — a prompt "
        "that says \"use *the* 58.4 times per thousand words\" produces "
        "mechanical pastiche.")
    add("")
    add("| Word | z | Direction |")
    add("|---|---:|---|")
    for entry in profile.signature_words:
        add(f"| `{entry['word']}` | {entry['z']:+.2f} | uses it "
            f"{'more' if entry['direction'] == 'over' else 'less'} than the corpus |")
    add("")

    if profile.signature_phrases:
        add("## Signature phrases")
        add("")
        add("Three-word sequences this author uses far more than the other eight, "
            "with proper names filtered out. Frequency ratio against the rest of "
            "the corpus.")
        add("")
        add("| Phrase | Uses | × corpus rate |")
        add("|---|---:|---:|")
        for entry in profile.signature_phrases:
            add(f"| “{entry['phrase']}” | {entry['count']} | {entry['ratio']:.0f}× |")
        add("")

    if profile.top_tags:
        add("## Dialogue tags actually used")
        add("")
        add(", ".join(f"`{tag}` ({count})" for tag, count in profile.top_tags))
        add("")

    # -- validators -------------------------------------------------------
    add("## Validators")
    add("")
    add("These two answer *\"is this passage in the same statistical "
        "neighbourhood?\"* and nothing more. They cannot tell a draft how to fix "
        "itself — when one fires, read the interpretable families above to find "
        "out why. They are calibrated by leave-one-out: each of this author's own "
        "passages was scored against the centroid of the author's *other* "
        "passages, which is what makes the thresholds mean something.")
    add("")
    add("### Burrows's Delta")
    add("")
    add("| Threshold | Value | Reading |")
    add("|---|---:|---|")
    add(f"| Typical own-passage distance | {profile.delta.loo_median:.3f} "
        "| A passage this close is indistinguishable from the author's own work. |")
    add(f"| 90th percentile | {profile.delta.loo_p90:.3f} "
        "| Still the author. Beyond this, only one passage in ten of their own. |")
    add(f"| Furthest own passage | {profile.delta.loo_max:.3f} "
        "| The author's own outer edge. A draft past this is outside the corpus. |")
    add("")
    add("### Character 4-gram cosine similarity")
    add("")
    add("| Threshold | Value | Reading |")
    add("|---|---:|---|")
    add(f"| Typical own-passage similarity | {profile.delta.ngram_loo_median:.3f} | Normal. |")
    add(f"| 10th percentile | {profile.delta.ngram_loo_p10:.3f} "
        "| Low but still inside the author's range. |")
    add(f"| Least similar own passage | {profile.delta.ngram_loo_min:.3f} "
        "| Below this, the draft is unlike anything in the corpus. |")
    add("")

    # -- limits -----------------------------------------------------------
    add("## Limits of this report")
    add("")
    add("- **It measures the corpus present, not the author entire.** "
        f"{profile.words_profiled:,} words of "
        f"{len(included)} work{'s' if len(included) != 1 else ''} is a sample.")
    add("- **Estimates are estimates.** Features marked `~` come from rules, not "
        "a syntactic parser. Tense, passive voice, participial openings and tag "
        "attribution are the weakest of them, and historical punctuation and "
        "dialect make them weaker.")
    add("- **Proxies are weaker still.** Features marked `≈` count word-list hits. "
        "\"Sensory density\" is a count of sensory words, which is not the same "
        "thing as writing that engages the senses.")
    add("- **Nothing here is a literary judgement.** Whether the irony works, "
        "whether the dialogue has subtext, whether the restraint is earned, "
        "whether a metaphor is fresh — no counter can reach any of it. The "
        "checker flags candidates for a human reader.")
    add("- **Content and style are not fully separable.** Proper nouns and topical "
        "vocabulary contaminate authorship signals, which is why names are "
        "filtered out of the signature phrases and why the function-word profile "
        "carries more weight than the vocabulary.")
    if not profile.single_author:
        add("- **This byline is not a person.** Delta similarity to this profile "
            "means \"resembles the syndicate house style,\" not \"resembles an "
            "author.\"")
    add("")

    add("---")
    add("")
    add(f"*See also: [style card]({profile.slug}-style-card.md) · "
        f"[machine profile](profile.json) · "
        f"[per-chunk metrics](chunk-metrics.csv) · "
        f"[per-work metrics](work-metrics.csv) · "
        f"[cross-author comparison](../../../stylometry/CROSS-AUTHOR-COMPARISON.md)*")
    add("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Style card
# ---------------------------------------------------------------------------


def _pct_range(lane: Lane, digits: int = 0) -> str:
    return f"{lane.p25:.{digits}f}–{lane.p75:.{digits}f}%"


def _num_range(lane: Lane, digits: int = 0) -> str:
    return f"{lane.p25:.{digits}f}–{lane.p75:.{digits}f}"


def render_style_card(profile: AuthorProfile) -> str:
    L = profile.lanes
    notes = notes_for(profile.slug)

    short = L["sent_very_short_pct"].median + L["sent_short_pct"].median
    long_pct = L["sent_long_pct"].median + L["sent_very_long_pct"].median

    out: list[str] = []
    add = out.append

    add("---")
    add("type: style-card")
    add(f"author: {profile.name}")
    add(f"slug: {profile.slug}")
    add(f"lane: {notes['lane']}")
    add(f"report: {profile.slug}-stylometry-report.md")
    add("profile_json: profile.json")
    add(f"scene_types: [{', '.join(notes['scenes'])}]")
    add(f"generated_by: scripts/build_stylo_profiles.py")
    add(f"generated_on: {date.today().isoformat()}")
    add("---")
    add("")
    add(f"# {profile.name} — Style Card")
    add("")
    add("*Paste the block below into a writing prompt. It is deliberately short: "
        "ranges and tendencies, not quotas. A model given a hundred measurements "
        "starts performing the statistics instead of writing the prose.*")
    add("")
    if not profile.single_author:
        add(f"> **This is a house style, not a person.** {profile.caution}")
        add("")

    add("```text")
    add(f"STYLE LANE: {notes['lane']}")
    add("")
    add("POV AND TENSE")
    add(f"- Measured: {profile.pov_note}.")
    for line in _pov_lines(profile):
        add(f"- {line}")
    add("")
    add("RHYTHM")
    add(f"- Median narration sentence: {L['narr_sent_median'].p25:.0f}–"
        f"{L['narr_sent_median'].p75:.0f} words.")
    add(f"- About {short:.0f}% of sentences are 10 words or fewer; "
        f"{long_pct:.0f}% run 25 words or longer.")
    add(f"- Vary cadence: adjacent sentences differ by "
        f"{L['sent_adjacent_delta'].median:.0f} words on average.")
    add(f"- Do not run more than about {L['sent_longest_band_run'].p75:.0f} "
        f"sentences of similar length in a row.")
    add("")
    add("PARAGRAPHS")
    add(f"- Narration paragraphs typically {L['para_narration_mean_words'].p25:.0f}–"
        f"{L['para_narration_mean_words'].p75:.0f} words, "
        f"{L['para_mean_sentences'].p25:.1f}–{L['para_mean_sentences'].p75:.1f} "
        f"sentences.")
    add(f"- One-sentence narration paragraphs: "
        f"{_pct_range(L['para_one_sentence_narration_pct'])} — reserve them for "
        f"reversals and blows.")
    add(f"- Paragraphs over 100 words: {_pct_range(L['para_over_100_pct'])}.")
    add("")
    add("DIALOGUE")
    add(f"- Speech share: {_pct_range(L['dialogue_word_pct'])} overall; "
        f"{profile.dialogue_heavy_lane[0]:.0f}–{profile.dialogue_heavy_lane[1]:.0f}% "
        f"in conversation-driven scenes, "
        f"{profile.narration_heavy_lane[0]:.0f}–{profile.narration_heavy_lane[1]:.0f}% "
        f"in reflective ones.")
    add(f"- Median speech {L['utterance_median_words'].median:.0f} words; "
        f"{L['utterance_short_pct'].median:.0f}% are three words or fewer; "
        f"{L['utterance_long_pct'].median:.0f}% run past 40.")
    add(f"- Vary speech length — do not write a run of same-sized replies.")
    add(f"- Tags: {L['tag_said_pct'].median:.0f}% of tags are \"said\"; "
        f"{L['tag_marked_pct'].median:.0f}% are marked alternatives; "
        f"{L['tag_adverb_pct'].median:.0f}% carry an -ly adverb.")
    add(f"- {L['unattributed_utterance_pct'].median:.0f}% of speeches carry no tag "
        f"and no beat.")
    add("")
    add("PUNCTUATION (per 1,000 narration words)")
    add(f"- Commas {L['narr_comma_per_1k'].p25:.0f}–{L['narr_comma_per_1k'].p75:.0f}; "
        f"semicolons {L['narr_semicolon_per_1k'].median:.1f}; "
        f"colons {L['narr_colon_per_1k'].median:.1f}.")
    add(f"- Em dashes {L['narr_emdash_per_1k'].median:.1f} — "
        f"{_emdash_advice(L['narr_emdash_per_1k'].median)}")
    add(f"- Exclamation marks {L['narr_exclamation_per_1k'].median:.1f}.")
    add("")
    add("SYNTAX")
    add(f"- {L['subordinate_sentence_pct'].median:.0f}% of sentences carry "
        f"subordination.")
    add(f"- Openings: {_opening_summary(L)}.")
    add(f"- Only {L['open_name_action_pct'].median:.0f}% of sentences open "
        f"Name + simple action. Do not let that pattern take over.")
    add("")
    add("LEXICAL TEXTURE")
    add(f"- Lexical diversity (MATTR-50) around {L['mattr_50'].median:.2f}; "
        f"{L['long_word_pct'].median:.0f}% of words run 8+ letters.")
    add(f"- Named emotions {L['emotion_label_per_1k'].median:.1f} per 1,000 words; "
        f"sensory terms {L['sensory_per_1k'].median:.0f}; "
        f"abstract nouns {L['abstract_noun_per_1k'].median:.0f}.")
    add(f"- Filter phrases (she saw, he felt, began to) "
        f"{L['filter_phrase_per_1k'].median:.1f} per 1,000 words.")
    add("")
    add("CRAFT")
    for line in notes["craft"]:
        add(f"- {_wrap(line)}")
    add("")
    add("AVOID")
    for line in notes["avoid"]:
        add(f"- {_wrap(line)}")
    add(f"- Modern crutch phrases (\"a sense of\", \"in that moment\", "
        f"\"couldn't help but\", \"let out a breath\"). Measured rate in this "
        f"corpus: {L['crutch_phrase_per_1k'].median:.2f} per 1,000 words.")
    add("```")
    add("")

    add("## Why these controls")
    add("")
    hard = profile.hard_targets()
    if hard:
        add("The numbers above are not arbitrary. Each one below is stable across "
            f"{profile.name}'s own books *and* at least 1σ away from the other "
            "eight authors in the collection — meaning it is a real fingerprint, "
            "not a trait shared by everyone writing in English:")
        add("")
        for lane in sorted(hard, key=lambda l: abs(l.distinct_z or 0), reverse=True)[:8]:
            metric = REGISTRY[lane.key]
            direction = "higher" if (lane.distinct_z or 0) > 0 else "lower"
            add(f"- **{metric.label}** — {metric.format(lane.median)}, "
                f"{abs(lane.distinct_z or 0):.1f}σ {direction} than the "
                f"corpus average.")
        add("")
    add("Features that move a lot between this author's own books are **not** in "
        "the card. Holding a draft to a number the author does not hold "
        "themselves to is how you get mechanical pastiche. The full evidence, "
        f"including every unstable feature, is in "
        f"[`{profile.slug}-stylometry-report.md`]({profile.slug}-stylometry-report.md).")
    add("")

    add("## Using this card with exemplars")
    add("")
    add("A style card describes the lane; exemplars demonstrate it. When you add "
        "passages from the corpus to a prompt, pick them by **narrative job** — "
        f"{', '.join(notes['scenes'][:3]).lower()} — not by subject matter, and "
        "tell the model:")
    add("")
    add("> The excerpts below demonstrate rhythm, narrative distance, dialogue "
        "pressure, and paragraph movement. Do not copy their situations, wording, "
        "imagery, or character actions.")
    add("")

    add("## Checking the result")
    add("")
    add("```bash")
    add(f"python3 scripts/check_prose.py draft.md --author {profile.slug}")
    add("```")
    add("")
    add("The checker measures the draft locally and returns only the passages "
        "that left the lane, plus a rewrite brief. The model never has to reread "
        "the corpus.")
    add("")
    return "\n".join(out)


def _wrap(text: str, width: int = 76) -> str:
    """Soft-wrap a craft line for the fenced block."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = "  " + word
        else:
            current = f"{current} {word}".strip()
    lines.append(current)
    return "\n  ".join(lines)


def _emdash_advice(rate: float) -> str:
    if rate < 2:
        return "rare. Almost never in narration."
    if rate < 6:
        return "occasional, chiefly for interrupted speech."
    return "frequent, and structural to the voice."


def _opening_summary(lanes: dict[str, Lane]) -> str:
    pairs = [
        ("character name", lanes["open_name_pct"].median),
        ("pronoun", lanes["open_pronoun_pct"].median),
        ("article + noun", lanes["open_article_pct"].median),
        ("prepositional phrase", lanes["open_preposition_pct"].median),
        ("subordinate clause", lanes["open_subordinate_pct"].median),
        ("dialogue", lanes["open_dialogue_pct"].median),
        ("conjunction", lanes["open_conjunction_pct"].median),
        ("adverb", lanes["open_adverb_pct"].median),
    ]
    pairs.sort(key=lambda p: p[1], reverse=True)
    return ", ".join(f"{name} {value:.0f}%" for name, value in pairs[:4])


def _pov_lines(profile: AuthorProfile) -> list[str]:
    L = profile.lanes
    lines: list[str] = []
    ratio = L["name_to_pronoun_ratio"].median
    if ratio:
        lines.append(
            f"Names to third-person pronouns runs about {ratio:.2f}:1 — "
            + ("lean on pronouns; name a character only when the reference "
               "would otherwise be unclear." if ratio < 0.5 else
               "names are used freely, not avoided.")
        )
    if L["narr_feminine_per_1k"].median > L["narr_masculine_per_1k"].median * 1.3:
        lines.append("Narration attends chiefly to women.")
    elif L["narr_masculine_per_1k"].median > L["narr_feminine_per_1k"].median * 1.3:
        lines.append("Narration attends chiefly to men.")
    lines.append(
        "Keep perception filtered through the viewpoint character; do not state "
        "another character's unspoken thoughts."
    )
    return lines
