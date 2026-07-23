"""Audit a draft against an author's lanes.

This is the module that saves tokens. Python reads the whole draft locally,
decides which passages left the author's lane, and emits a short brief. The
model then sees the style card, the flagged passage, a little surrounding
context and the brief - never the corpus, never the whole manuscript again.

The output deliberately follows the shape the guide specifies:

    OVERALL RESULT / LARGEST DRIFTS / LOCATIONS / REWRITE BRIEF
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Sequence

from . import delta as delta_mod
from . import lexicons as lex
from .features import (
    PRIMARY_METRICS,
    REGISTRY,
    _CRUTCH_RES,
    _EMDASH_RE,
    _FILTER_RES,
    Metric,
    build_sample,
    measure,
)
from .profile import AuthorProfile, Lane
from .segment import Document, dialogue_spans, split_sentences, tokens, word_count

SHORT_DRAFT_WORDS = 800

# ---------------------------------------------------------------------------
# How to say "fix this" for each measurement
# ---------------------------------------------------------------------------
# (too high, too low). Written as instructions to a writer, not as numbers -
# the numbers are already in the drift table above the brief.
#
# An empty string means that direction is not a fault. Nobody needs to be told
# to lengthen their longest run of same-sized sentences, or to add more filter
# phrases. Those drifts are dropped rather than dressed up as advice.

ADVICE: dict[str, tuple[str, str]] = {
    "narr_sent_median": (
        "Narration sentences are longer than this author's. Break the "
        "accumulating ones at their natural joint rather than trimming words "
        "evenly.",
        "Narration sentences are too short. Combine adjacent statements into "
        "more layered sentences — let a qualification or consequence ride "
        "inside the sentence that raised it. Do not lengthen every sentence.",
    ),
    "sent_cv": (
        "Sentence lengths swing more wildly than this author's. Some of the "
        "very short sentences are doing work a clause could do.",
        "Sentence lengths are too uniform. Vary the cadence: the reading "
        "experience of a steady 16 words is nothing like 4 words against 30.",
    ),
    "sent_very_short_pct": (
        "Too many very short sentences. They are load-bearing for this author "
        "only at reversals; used constantly they flatten into a tic.",
        "Too few very short sentences. This author lands beats with them.",
    ),
    "sent_long_pct": (
        "Too many long sentences. Not every thought needs to accumulate.",
        "Too few long sentences. This author lets observation and thought "
        "gather across 25–35 words before closing.",
    ),
    "sent_longest_band_run": (
        "There is a long run of similarly sized sentences. Break it with a "
        "sentence of a different weight.",
        "",
    ),
    "para_median_words": (
        "Paragraphs run long for this author.",
        "Paragraphs run short for this author. Let a thought finish before "
        "breaking.",
    ),
    "para_mean_sentences": (
        "Paragraphs carry more sentences than this author's typically do.",
        "Paragraphs are thin. This author's narrative paragraphs carry more "
        "sentences before the break.",
    ),
    "para_one_sentence_narration_pct": (
        "One-sentence paragraphs are overused. Reserve them for reversals, "
        "revelations, and emotional blows — a page of them reads as a tic and "
        "is one of the clearest generic-AI tells.",
        "One-sentence paragraphs are rarer than this author's. There may be a "
        "beat that deserves isolating.",
    ),
    "para_short_run_max": (
        "There is a run of consecutive short paragraphs. Vary paragraph "
        "weight through the passage.",
        "",
    ),
    "para_over_100_pct": (
        "Too many paragraphs over 100 words.",
        "This author allows more substantial paragraphs than the draft does.",
    ),
    "dialogue_word_pct": (
        "The passage is more dialogue-driven than this author's typical scene. "
        "Check the scene type — a confrontation is allowed to be talk-heavy.",
        "The passage is more narration-driven than this author's typical "
        "scene. Check the scene type before forcing speech into it.",
    ),
    "utterance_median_words": (
        "Speeches run long. Long speeches should require a genuine shift in "
        "power, or a confession.",
        "Speeches run short. Some replies can carry more than a beat.",
    ),
    "utterance_length_cv": (
        "",
        "Speeches are too symmetrical — reply after reply of nearly the same "
        "size. Real exchanges are lopsided: someone evades, someone runs on, "
        "someone answers in two words.",
    ),
    "tag_said_pct": (
        "\"Said\" is doing more work than in this author's dialogue.",
        "Too few plain tags. Marked alternatives (exclaimed, retorted, "
        "murmured) are carrying attribution that \"said\", an action beat, or "
        "no tag at all should carry.",
    ),
    "tag_adverb_pct": (
        "Too many tags carry an -ly adverb. Prefer a physical action beat to "
        "an explanatory adverb.",
        "",
    ),
    "narr_comma_per_1k": (
        "Comma density is above this author's narration.",
        "Comma density is below this author's narration — the sentences may "
        "be doing less shaping than the voice expects.",
    ),
    "narr_semicolon_per_1k": (
        "More semicolons than this author uses.",
        "This author uses semicolons to hold a qualification against the "
        "claim that provoked it. The draft is not doing that.",
    ),
    "narr_emdash_per_1k": (
        "Em dashes are overused in narration. This is the single most common "
        "model habit. Most of them want to be commas, a full stop, or nothing.",
        "",
    ),
    "narr_exclamation_per_1k": (
        "Exclamation marks are above this author's narration.",
        "",
    ),
    "narr_modal_per_1k": (
        "Modal phrasing is heavy — characters keep considering what they could "
        "or might do. Let them act or refuse.",
        "",
    ),
    "subordinate_sentence_pct": (
        "Subordination is heavier than this author's.",
        "Too little subordination. This author holds qualifications and "
        "conflicts inside the sentence rather than in a following one.",
    ),
    "open_repeat_pct": (
        "Sentence openings repeat. Vary among character action, prepositional "
        "framing, dialogue, and subordinate clauses.",
        "",
    ),
    "open_name_action_pct": (
        "Too many sentences open Name + simple action. This is the flattest "
        "available rhythm and it compounds fast.",
        "",
    ),
    "mattr_50": (
        "Vocabulary is more varied than this author's — check for "
        "conspicuously rare synonyms.",
        "Vocabulary is repeating. Prefer specific nouns and verbs; natural "
        "repetition of concrete objects is fine, but the same emotional "
        "adjective twice on a page is not.",
    ),
    "lexical_density": (
        "Content-word density is high; the prose may be over-packed.",
        "Content-word density is low — a lot of function words carrying "
        "little.",
    ),
    "filter_phrase_per_1k": (
        "Filter phrases (she saw, he felt, she realized, began to) are heavy. "
        "Use them only when the act of noticing is itself the point; "
        "otherwise report the thing noticed.",
        "",
    ),
    "sensory_per_1k": (
        "Sensory vocabulary is heavier than this author's.",
        "Sensory attention is thinner than this author's.",
    ),
    "emotion_label_per_1k": (
        "Emotions are being named. This author more often conveys them "
        "through physical choice, bodily sensation, dialogue pressure, or "
        "attention to a concrete object.",
        "",
    ),
    "abstract_noun_per_1k": (
        "Abstraction is heavy — a lot of -ness, -ment and -tion nouns where "
        "concrete things could stand.",
        "",
    ),
    "repeat_4gram_per_1k": (
        "Phrases are repeating within the passage.",
        "",
    ),
    "crutch_phrase_per_1k": (
        "Modern crutch phrases appear. These are effectively absent from every "
        "author in this corpus and read as generic model prose.",
        "",
    ),
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass()
class Drift:
    key: str
    label: str
    family: str
    draft: float
    median: float
    lane_low: float
    lane_high: float
    wide_low: float
    wide_high: float
    severity: float
    direction: str
    reliability: str
    advice: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass()
class Location:
    kind: str
    where: str
    detail: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass()
class AuditResult:
    author: str
    author_slug: str
    draft_title: str
    words: int
    paragraphs: int
    primary_total: int
    primary_in_lane: int
    drifts: list[Drift] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)
    delta_distance: float = 0.0
    delta_verdict: str = ""
    ngram_similarity: float = 0.0
    ngram_verdict: str = ""
    nearest_author: str = ""
    warnings: list[str] = field(default_factory=list)
    brief: str = ""

    def as_dict(self) -> dict:
        return {
            "author": self.author,
            "author_slug": self.author_slug,
            "draft_title": self.draft_title,
            "words": self.words,
            "paragraphs": self.paragraphs,
            "primary_total": self.primary_total,
            "primary_in_lane": self.primary_in_lane,
            "drifts": [d.as_dict() for d in self.drifts],
            "locations": [l.as_dict() for l in self.locations],
            "validators": {
                "delta_distance": self.delta_distance,
                "delta_verdict": self.delta_verdict,
                "ngram_similarity": self.ngram_similarity,
                "ngram_verdict": self.ngram_verdict,
                "nearest_author": self.nearest_author,
            },
            "warnings": self.warnings,
            "rewrite_brief": self.brief,
        }


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def _advice_for(key: str, direction: str, lane: Lane) -> str | None:
    """The instruction for this drift, or ``None`` if it is not a fault."""
    if key in ADVICE:
        high, low = ADVICE[key]
        text = high if direction == "high" else low
        return text or None
    metric = REGISTRY[key]
    return (
        f"{'Reduce' if direction == 'high' else 'Raise'} {metric.label.lower()} "
        f"toward {metric.format(lane.median)}."
    )


def find_drifts(
    metrics: dict[str, float],
    profile: AuthorProfile,
    keys: Sequence[str],
) -> list[Drift]:
    drifts: list[Drift] = []
    for key in keys:
        lane = profile.lanes.get(key)
        if lane is None:
            continue
        value = metrics[key]
        if lane.verdict(value) != "out":
            continue
        direction = "high" if value > lane.p90 else "low"
        advice = _advice_for(key, direction, lane)
        if advice is None:
            continue
        metric = REGISTRY[key]
        drifts.append(
            Drift(
                key=key,
                label=metric.label,
                family=metric.family,
                draft=value,
                median=lane.median,
                lane_low=lane.p25,
                lane_high=lane.p75,
                wide_low=lane.p10,
                wide_high=lane.p90,
                severity=lane.drift(value),
                direction=direction,
                reliability=metric.reliability,
                advice=advice,
            )
        )
    drifts.sort(key=lambda d: d.severity, reverse=True)
    return drifts


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


def _span(indices: Sequence[int]) -> str:
    """A contiguous run, written as a range."""
    if not indices:
        return ""
    if len(indices) == 1:
        return f"Paragraph {indices[0] + 1}"
    return f"Paragraphs {indices[0] + 1}–{indices[-1] + 1}"


def _list(indices: Sequence[int], limit: int = 8) -> str:
    """Scattered paragraphs, written as a list.

    A range would lie here: "Paragraphs 15–28" reads as fourteen consecutive
    paragraphs when the hits are actually four spread across that stretch.
    """
    ordered = sorted(set(indices))
    if not ordered:
        return ""
    shown = ", ".join(f"¶{i + 1}" for i in ordered[:limit])
    if len(ordered) > limit:
        shown += f", +{len(ordered) - limit} more"
    return shown


def _runs(flags: Sequence[bool], minimum: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= minimum:
                out.append((start, i - 1))
            start = None
    if start is not None and len(flags) - start >= minimum:
        out.append((start, len(flags) - 1))
    return out


def find_locations(
    document: Document,
    profile: AuthorProfile,
    drift_keys: set[str],
) -> list[Location]:
    """Point at the actual paragraphs. A drift with no location is unactionable."""
    locations: list[Location] = []
    paras = document.paragraphs
    sample = build_sample(paras, document.proper_names())

    # Runs of short paragraphs.
    limit = max(3, int(profile.lanes["para_short_run_max"].p90) + 1)
    for start, end in _runs([n <= 25 for n in sample.para_words], limit):
        locations.append(
            Location(
                kind="short_paragraph_run",
                where=_span(list(range(start, end + 1))),
                detail=f"{end - start + 1} consecutive short paragraphs "
                       f"(this author's own longest run is typically "
                       f"{profile.lanes['para_short_run_max'].p90:.0f}).",
            )
        )

    # One-sentence narration paragraphs, when the rate itself drifted.
    if "para_one_sentence_narration_pct" in drift_keys:
        indices = [
            i for i, (count, speech) in enumerate(
                zip(sample.para_sentences, sample.para_has_speech)
            )
            if count == 1 and not speech
        ]
        for start, end in _runs(
            [i in set(indices) for i in range(len(paras))], 3
        ):
            locations.append(
                Location(
                    kind="one_sentence_paragraph_cluster",
                    where=_span(list(range(start, end + 1))),
                    detail=f"{end - start + 1} one-sentence narration paragraphs "
                           f"in a row.",
                )
            )

    # Long runs of same-band sentences.
    if "sent_longest_band_run" in drift_keys or "sent_cv" in drift_keys:
        from .features import _band
        bands = [(_band(s.words), s.para_index) for s in sample.sentences]
        limit = max(4, int(profile.lanes["sent_longest_band_run"].p90) + 1)
        run_start = 0
        for i in range(1, len(bands) + 1):
            if i < len(bands) and bands[i][0] == bands[run_start][0]:
                continue
            if i - run_start >= limit:
                first = bands[run_start][1]
                last = bands[i - 1][1]
                locations.append(
                    Location(
                        kind="uniform_sentence_run",
                        where=_span(sorted({first, last})),
                        detail=f"{i - run_start} consecutive "
                               f"{bands[run_start][0].replace('_', ' ')} sentences.",
                    )
                )
            run_start = i

    # Repeated sentence openings.
    openings: dict[str, list[int]] = {}
    for sentence in sample.sentences:
        toks = tokens(sentence.text)[:2]
        if len(toks) == 2:
            openings.setdefault(" ".join(toks), []).append(sentence.para_index)
    for opening, indices in sorted(
        openings.items(), key=lambda kv: len(kv[1]), reverse=True
    ):
        if len(indices) < 3:
            continue
        locations.append(
            Location(
                kind="repeated_opening",
                where=_list(indices),
                detail=f"“{opening}…” opens {len(indices)} sentences.",
            )
        )
        if len([l for l in locations if l.kind == "repeated_opening"]) >= 3:
            break

    # Em-dash clusters.
    if "narr_emdash_per_1k" in drift_keys:
        heavy = [
            i for i, para in enumerate(paras)
            if len(_EMDASH_RE.findall(para.text)) >= 2
        ]
        if heavy:
            locations.append(
                Location(
                    kind="em_dash_cluster",
                    where=_list(heavy),
                    detail=f"{len(heavy)} paragraphs carry two or more em dashes.",
                )
            )

    # Filter phrases.
    if "filter_phrase_per_1k" in drift_keys:
        hits: list[tuple[int, str]] = []
        for i, para in enumerate(paras):
            for regex in _FILTER_RES:
                for match in regex.finditer(para.text):
                    hits.append((i, match.group(0)))
        if hits:
            sample_hits = ", ".join(
                f"“{text}” (¶{i + 1})" for i, text in hits[:6]
            )
            locations.append(
                Location(
                    kind="filter_phrases",
                    where=_list([i for i, _ in hits]),
                    detail=f"{len(hits)} filter phrases. {sample_hits}",
                )
            )

    # Crutch phrases are always reported, drift or not.
    crutch_hits: list[tuple[int, str]] = []
    for i, para in enumerate(paras):
        for regex in _CRUTCH_RES:
            for match in regex.finditer(para.text):
                crutch_hits.append((i, match.group(0)))
    if crutch_hits:
        listed = ", ".join(f"“{text}” (¶{i + 1})" for i, text in crutch_hits[:8])
        locations.append(
            Location(
                kind="crutch_phrases",
                where=_list([i for i, _ in crutch_hits]),
                detail=f"{len(crutch_hits)} modern crutch phrases, absent from "
                       f"this corpus: {listed}",
            )
        )

    # Symmetrical dialogue: consecutive speeches of near-identical length.
    utterances: list[tuple[int, int]] = []
    for para in paras:
        for start, end in dialogue_spans(para.text):
            utterances.append((para.index, word_count(para.text[start + 1:end - 1])))
    run_start = 0
    for i in range(1, len(utterances) + 1):
        if (
            i < len(utterances)
            and abs(utterances[i][1] - utterances[run_start][1]) <= 2
            and utterances[i][1] > 3
        ):
            continue
        if i - run_start >= 4:
            indices = [utterances[j][0] for j in range(run_start, i)]
            locations.append(
                Location(
                    kind="symmetrical_dialogue",
                    where=_span(sorted(set(indices))),
                    detail=f"{i - run_start} consecutive speeches of nearly "
                           f"identical length "
                           f"({utterances[run_start][1]}–{utterances[i - 1][1]} words).",
                )
            )
        run_start = i

    # Repeated phrases.
    if "repeat_4gram_per_1k" in drift_keys:
        from collections import Counter
        toks = sample.all_tokens
        grams = Counter(
            tuple(toks[i:i + 4]) for i in range(max(0, len(toks) - 3))
        )
        worst = [(g, c) for g, c in grams.most_common(6) if c > 1]
        if worst:
            locations.append(
                Location(
                    kind="repeated_phrases",
                    where="throughout",
                    detail="; ".join(
                        f"“{' '.join(g)}” ×{c}" for g, c in worst
                    ),
                )
            )
    return locations


# ---------------------------------------------------------------------------
# POV and tense checks
# ---------------------------------------------------------------------------


def check_pov(document: Document, pov: str, tense: str) -> list[Location]:
    """Rule-based POV and tense slip detection.

    The checker has to be *told* the intended POV and tense. Without that it
    cannot tell a deliberate choice from a mistake, so this runs only when the
    caller supplies one.
    """
    out: list[Location] = []
    sample = build_sample(document.paragraphs, document.proper_names())
    narration = [s for s in sample.sentences if not s.has_speech]

    if pov == "third":
        slips = [
            s for s in narration
            if any(t in lex.FIRST_PERSON for t in tokens(s.text))
        ]
        if slips:
            out.append(
                Location(
                    kind="pov_slip",
                    where=_list([s.para_index for s in slips]),
                    detail=f"{len(slips)} narration sentences carry first-person "
                           f"pronouns in a third-person draft. First: "
                           f"“{slips[0].text[:80]}…”",
                )
            )
    elif pov == "first":
        slips = [
            s for s in narration
            if not any(t in lex.FIRST_PERSON for t in tokens(s.text))
        ]
        rate = len(slips) / len(narration) if narration else 0
        if rate > 0.85:
            out.append(
                Location(
                    kind="pov_note",
                    where="throughout",
                    detail=f"{rate * 100:.0f}% of narration sentences contain no "
                           f"first-person pronoun. The narrator may have receded "
                           f"further than a first-person draft intends.",
                )
            )

    if tense == "past":
        slips = [
            s for s in narration
            if any(t in lex.PRESENT_MARKERS for t in tokens(s.text))
        ]
        if slips:
            out.append(
                Location(
                    kind="tense_slip",
                    where=_list([s.para_index for s in slips]),
                    detail=f"{len(slips)} narration sentences carry present-tense "
                           f"markers in a past-tense draft. Some will be "
                           f"legitimate (habitual truths, free indirect thought) "
                           f"— check them. First: “{slips[0].text[:80]}…”",
                )
            )
    return out


# ---------------------------------------------------------------------------
# Rewrite brief
# ---------------------------------------------------------------------------


def build_brief(result: AuditResult, profile: AuthorProfile) -> str:
    if not result.drifts:
        return (
            "No rewrite needed. The passage is inside "
            f"{profile.name}'s lane on every primary measurement checked. "
            "Whether the scene works as fiction is a separate question this "
            "checker cannot answer."
        )
    lines = [
        "Preserve the scene events, the dialogue intentions, and the "
        "characters' choices. Change only the prose surface.",
        "",
    ]
    for i, drift in enumerate(result.drifts[:5], 1):
        lines.append(f"{i}. {drift.advice}")
    lines.append("")
    lines.append(
        "Do not compensate by overcorrecting — a draft that swings past the "
        "lane in the other direction is not closer to the author. Leave "
        "everything already inside the lane alone."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def audit(
    document: Document,
    profile: AuthorProfile,
    reference: dict,
    *,
    keys: Sequence[str] | None = None,
    scene: str = "any",
    pov: str = "",
    tense: str = "",
) -> AuditResult:
    names = document.proper_names()
    metrics = measure(document.paragraphs, names)
    words = document.word_count

    check_keys = list(keys or PRIMARY_METRICS)

    # A conversation scene and a reflective scene are not supposed to hit the
    # same dialogue number, so swap the lane rather than flagging the scene.
    if scene in {"conversation", "reflection"} and "dialogue_word_pct" in profile.lanes:
        lane = profile.lanes["dialogue_word_pct"]
        low, high = (
            profile.dialogue_heavy_lane if scene == "conversation"
            else profile.narration_heavy_lane
        )
        width = (high - low) or 1.0
        profile.lanes["dialogue_word_pct"] = Lane(
            key=lane.key, median=(low + high) / 2,
            p10=low - width * 0.5, p25=low, p75=high, p90=high + width * 0.5,
            mean=lane.mean, sd=lane.sd, book_low=lane.book_low,
            book_high=lane.book_high, book_cv=lane.book_cv,
            stability=lane.stability, distinct_z=lane.distinct_z,
            distinctive=lane.distinctive,
        )

    drifts = find_drifts(metrics, profile, check_keys)
    checked = len([k for k in check_keys if k in profile.lanes])
    # Counted against the drifts actually reported, so the headline and the
    # list below it always agree.
    in_lane = checked - len(drifts)

    result = AuditResult(
        author=profile.name,
        author_slug=profile.slug,
        draft_title=document.title,
        words=words,
        paragraphs=len(document.paragraphs),
        primary_total=checked,
        primary_in_lane=in_lane,
        drifts=drifts,
    )

    result.locations = find_locations(document, profile, {d.key for d in drifts})
    if pov or tense:
        result.locations = check_pov(document, pov, tense) + result.locations

    # Validators.
    standardiser = delta_mod.Standardiser.from_dict(reference["standardiser"])
    draft_tokens = tokens(document.text)
    z = standardiser.z_from_tokens(draft_tokens)
    result.delta_distance = delta_mod.delta_distance(z, profile.delta.centroid)
    if result.delta_distance <= profile.delta.loo_p90:
        result.delta_verdict = "inside the author's own range"
    elif result.delta_distance <= profile.delta.loo_max:
        result.delta_verdict = "at the edge of the author's own range"
    else:
        result.delta_verdict = "outside anything in the author's corpus"

    ngram_keys = reference["ngram_keys"]
    vector = delta_mod.ngram_vector(delta_mod.char_ngrams(document.text, 4), ngram_keys)
    result.ngram_similarity = delta_mod.cosine(vector, profile.delta.ngram_centroid)
    if result.ngram_similarity >= profile.delta.ngram_loo_p10:
        result.ngram_verdict = "inside the author's own range"
    elif result.ngram_similarity >= profile.delta.ngram_loo_min:
        result.ngram_verdict = "at the edge of the author's own range"
    else:
        result.ngram_verdict = "outside anything in the author's corpus"

    distances = sorted(
        (
            delta_mod.delta_distance(z, data["centroid"]), data["name"]
        )
        for data in reference["authors"].values()
    )
    result.nearest_author = f"{distances[0][1]} ({distances[0][0]:.2f})"

    if words < SHORT_DRAFT_WORDS:
        result.warnings.append(
            f"The draft is {words:,} words. Lanes were built from ~2,000-word "
            f"chunks, so distribution features (percentiles, coefficients of "
            f"variation, longest runs) are noisy at this length. Treat single "
            f"flags as questions, not verdicts."
        )
    if not profile.single_author:
        result.warnings.append(
            f"{profile.name} is a publishing byline, not a person. Matching "
            f"this profile means matching a syndicate house style."
        )

    result.brief = build_brief(result, profile)
    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(result: AuditResult, profile: AuthorProfile) -> str:
    out: list[str] = []
    add = out.append

    add("=" * 72)
    add(f"STYLE AUDIT — {result.draft_title}")
    add(f"Target: {result.author} · {result.words:,} words · "
        f"{result.paragraphs} paragraphs")
    add("=" * 72)
    add("")
    add("OVERALL RESULT")
    add(f"The passage is inside the target lane on {result.primary_in_lane} of "
        f"{result.primary_total} primary measurements.")
    add("")
    add(f"Burrows's Delta to {result.author}: {result.delta_distance:.3f} "
        f"— {result.delta_verdict}")
    add(f"  (this author's own passages sit at "
        f"{profile.delta.loo_median:.3f} typical, "
        f"{profile.delta.loo_p90:.3f} at the 90th percentile)")
    add(f"Character 4-gram similarity: {result.ngram_similarity:.3f} "
        f"— {result.ngram_verdict}")
    add(f"Closest author in the collection: {result.nearest_author}")
    add("")

    if result.warnings:
        add("NOTES")
        for warning in result.warnings:
            add(f"! {_wrap(warning)}")
        add("")

    if result.drifts:
        add("LARGEST DRIFTS")
        for i, drift in enumerate(result.drifts[:8], 1):
            metric = REGISTRY[drift.key]
            mark = {"exact": "", "estimate": " [estimate]", "proxy": " [proxy]"}[
                drift.reliability
            ]
            add(f"{i}. {drift.label}{mark}")
            add(f"   Target lane: {metric.format(drift.lane_low)}–"
                f"{metric.format(drift.lane_high)}  "
                f"(median {metric.format(drift.median)})")
            add(f"   Draft:       {metric.format(drift.draft)}  "
                f"— {drift.direction}")
            add(f"   {_wrap(drift.advice, indent=3)}")
            add("")
    else:
        add("LARGEST DRIFTS")
        add("None. Every primary measurement is inside the lane.")
        add("")

    if result.locations:
        add("LOCATIONS")
        for location in result.locations:
            where = location.where or "throughout"
            add(f"- {where}: {_wrap(location.detail, indent=2)}")
        add("")

    add("REWRITE BRIEF")
    add(result.brief)
    add("")
    add("-" * 72)
    add("This checker measures surfaces. It cannot tell you whether the "
        "dialogue has subtext, whether the irony lands, or whether the scene "
        "earns its climax. Those need a reader.")
    return "\n".join(out)


def _wrap(text: str, width: int = 68, indent: int = 0) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    pad = " " * indent
    return f"\n{pad}".join(lines)
