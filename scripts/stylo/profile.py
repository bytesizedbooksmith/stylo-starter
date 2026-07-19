"""Author profiles: lanes, not averages.

Section 8 of the guide is the design brief for this module. An author is not
one number per feature. For every feature we keep a median, a normal range, a
wider acceptable range, and how much the feature moves between books - because
a feature that swings wildly inside the author's own work is not something a
draft can be held to.

Two extra judgements are attached to each feature:

``stability``       how consistent it is across the author's own books
``distinctiveness`` how far the author sits from the other eight authors

Only a feature that is both stable and distinctive earns the right to be a
hard target in a style card.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Iterable, Sequence

from . import delta as delta_mod
from .corpus import AUTHORS, AuthorMeta, Chunk, Work
from .features import PRIMARY_METRICS, REGISTRY, percentile

STABLE_CV = 0.15
MODERATE_CV = 0.30
DISTINCT_Z = 1.0


@dataclass(slots=True)
class Lane:
    """One feature's lane for one author."""

    key: str
    median: float
    p10: float
    p25: float
    p75: float
    p90: float
    mean: float
    sd: float
    book_low: float = 0.0
    book_high: float = 0.0
    book_cv: float | None = None
    stability: str = "unknown"
    distinct_z: float | None = None
    distinctive: bool = False

    @property
    def normal_range(self) -> tuple[float, float]:
        """The lane proper: half the author's own passages live here."""
        return (self.p25, self.p75)

    @property
    def wide_range(self) -> tuple[float, float]:
        """Acceptable but notable: 80% of passages live here."""
        return (self.p10, self.p90)

    def verdict(self, value: float) -> str:
        """Where a draft's value falls relative to this lane."""
        if self.p25 <= value <= self.p75:
            return "in_lane"
        if self.p10 <= value <= self.p90:
            return "wide"
        return "out"

    def drift(self, value: float) -> float:
        """How far outside the wide range, in units of the wide range's width.

        0 means inside p10-p90. 1 means a full lane-width beyond the edge.
        """
        width = self.p90 - self.p10
        if width <= 0:
            width = abs(self.median) * 0.1 or 1.0
        if value < self.p10:
            return (self.p10 - value) / width
        if value > self.p90:
            return (value - self.p90) / width
        return 0.0


@dataclass(slots=True)
class WorkSummary:
    title: str
    year: str
    words: int
    chunks: int
    included: bool
    note: str = ""
    work_type: str = "novel"
    narration: str = ""
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class DeltaModel:
    """Everything needed to place a new passage in the Delta space."""

    centroid: list[float] = field(default_factory=list)
    loo_median: float = 0.0
    loo_p90: float = 0.0
    loo_max: float = 0.0
    ngram_centroid: list[float] = field(default_factory=list)
    ngram_loo_median: float = 0.0
    ngram_loo_p10: float = 0.0
    ngram_loo_min: float = 0.0


@dataclass(slots=True)
class AuthorProfile:
    slug: str
    name: str
    genre: str
    period: str
    single_author: bool
    caution: str
    words_profiled: int
    chunk_count: int
    chunk_target_words: int
    lanes: dict[str, Lane] = field(default_factory=dict)
    works: list[WorkSummary] = field(default_factory=list)
    delta: DeltaModel = field(default_factory=DeltaModel)
    signature_words: list[dict] = field(default_factory=list)
    signature_phrases: list[dict] = field(default_factory=list)
    dialogue_heavy_lane: tuple[float, float] = (0.0, 0.0)
    narration_heavy_lane: tuple[float, float] = (0.0, 0.0)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    pov_note: str = ""

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "genre": self.genre,
            "period": self.period,
            "single_author": self.single_author,
            "caution": self.caution,
            "words_profiled": self.words_profiled,
            "chunk_count": self.chunk_count,
            "chunk_target_words": self.chunk_target_words,
            "pov_note": self.pov_note,
            "dialogue_heavy_lane": list(self.dialogue_heavy_lane),
            "narration_heavy_lane": list(self.narration_heavy_lane),
            "top_tags": [list(t) for t in self.top_tags],
            "signature_words": self.signature_words,
            "signature_phrases": self.signature_phrases,
            "works": [asdict(w) for w in self.works],
            "lanes": {k: asdict(v) for k, v in self.lanes.items()},
            "delta": asdict(self.delta),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorProfile":
        profile = cls(
            slug=data["slug"],
            name=data["name"],
            genre=data["genre"],
            period=data["period"],
            single_author=data["single_author"],
            caution=data["caution"],
            words_profiled=data["words_profiled"],
            chunk_count=data["chunk_count"],
            chunk_target_words=data["chunk_target_words"],
        )
        profile.pov_note = data.get("pov_note", "")
        profile.dialogue_heavy_lane = tuple(data.get("dialogue_heavy_lane", (0, 0)))  # type: ignore[assignment]
        profile.narration_heavy_lane = tuple(data.get("narration_heavy_lane", (0, 0)))  # type: ignore[assignment]
        profile.top_tags = [tuple(t) for t in data.get("top_tags", [])]  # type: ignore[misc]
        profile.signature_words = data.get("signature_words", [])
        profile.signature_phrases = data.get("signature_phrases", [])
        profile.works = [WorkSummary(**w) for w in data.get("works", [])]
        profile.lanes = {k: Lane(**v) for k, v in data.get("lanes", {}).items()}
        profile.delta = DeltaModel(**data.get("delta", {}))
        return profile

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "AuthorProfile":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # -- convenience ------------------------------------------------------
    def hard_targets(self) -> list[Lane]:
        return [
            lane for key, lane in self.lanes.items()
            if lane.distinctive
            and lane.stability == "stable"
            and REGISTRY[key].promptable
        ]


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def _cv(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    m = mean(values)
    if abs(m) < 1e-9:
        return None
    return pstdev(values) / abs(m)


def _stability(book_cv: float | None) -> str:
    if book_cv is None:
        return "unknown"
    if book_cv <= STABLE_CV:
        return "stable"
    if book_cv <= MODERATE_CV:
        return "moderate"
    return "variable"


def build_lanes(chunks: Sequence[Chunk], book_medians: dict[str, list[float]]) -> dict[str, Lane]:
    """Turn per-chunk measurements into per-feature lanes."""
    lanes: dict[str, Lane] = {}
    for key in REGISTRY:
        values = [c.metrics[key] for c in chunks if key in c.metrics]
        if not values:
            continue
        per_book = book_medians.get(key, [])
        book_cv = _cv(per_book)
        lanes[key] = Lane(
            key=key,
            median=float(median(values)),
            p10=percentile(values, 10),
            p25=percentile(values, 25),
            p75=percentile(values, 75),
            p90=percentile(values, 90),
            mean=float(mean(values)),
            sd=float(pstdev(values)) if len(values) > 1 else 0.0,
            book_low=min(per_book) if per_book else 0.0,
            book_high=max(per_book) if per_book else 0.0,
            book_cv=book_cv,
            stability=_stability(book_cv),
        )
    return lanes


def apply_distinctiveness(profiles: dict[str, AuthorProfile]) -> None:
    """Score each feature by how far the author sits from the other authors.

    A feature is distinctive when the author's median is at least one standard
    deviation away from the cross-author spread of medians. Without this, a
    style card would happily list features every author shares.
    """
    for key in REGISTRY:
        medians = {
            slug: profile.lanes[key].median
            for slug, profile in profiles.items()
            if key in profile.lanes
        }
        if len(medians) < 3:
            continue
        values = list(medians.values())
        centre = mean(values)
        spread = pstdev(values)
        for slug, value in medians.items():
            lane = profiles[slug].lanes[key]
            if spread < 1e-9:
                lane.distinct_z = 0.0
                lane.distinctive = False
                continue
            z = (value - centre) / spread
            lane.distinct_z = z
            lane.distinctive = abs(z) >= DISTINCT_Z


def signature_words(
    centroid: Sequence[float], mfw: Sequence[str], top: int = 12
) -> list[dict]:
    """The function words this author most over- and under-uses.

    These are the interpretable end of Burrows's Delta: the same z-scores the
    distance is computed from, read one word at a time.
    """
    pairs = sorted(
        zip(mfw, centroid), key=lambda item: abs(item[1]), reverse=True
    )[:top]
    return [
        {"word": word, "z": round(z, 2), "direction": "over" if z > 0 else "under"}
        for word, z in pairs
    ]


def signature_phrases(
    author_grams: dict[tuple[str, ...], int],
    author_total: int,
    corpus_grams: dict[tuple[str, ...], int],
    corpus_total: int,
    names: Iterable[str],
    top: int = 12,
    min_count: int = 8,
) -> list[dict]:
    """Word trigrams the author uses far more than the rest of the corpus.

    Proper names are filtered out: "at the abbey" is a fact about the plot,
    not about the prose.
    """
    name_set = set(names)
    scored: list[tuple[float, tuple[str, ...], int]] = []
    for gram, count in author_grams.items():
        if count < min_count:
            continue
        if any(token in name_set for token in gram):
            continue
        author_rate = count / author_total
        corpus_rate = corpus_grams.get(gram, 0) / corpus_total
        ratio = (author_rate + 1e-9) / (corpus_rate + 1e-9)
        scored.append((ratio, gram, count))
    scored.sort(reverse=True)
    return [
        {"phrase": " ".join(gram), "count": count, "ratio": round(ratio, 1)}
        for ratio, gram, count in scored[:top]
    ]


def build_delta_model(
    chunk_vectors: Sequence[Sequence[float]],
    ngram_vectors: Sequence[Sequence[float]],
) -> DeltaModel:
    """Author centroid plus the honest thresholds around it."""
    model = DeltaModel()
    if chunk_vectors:
        model.centroid = delta_mod.centroid(chunk_vectors)
        loo = delta_mod.leave_one_out_distances(chunk_vectors)
        if loo:
            model.loo_median = float(median(loo))
            model.loo_p90 = percentile(loo, 90)
            model.loo_max = float(max(loo))
    if ngram_vectors:
        model.ngram_centroid = delta_mod.centroid(ngram_vectors)
        sims = [delta_mod.cosine(v, model.ngram_centroid) for v in ngram_vectors]
        if sims:
            model.ngram_loo_median = float(median(sims))
            model.ngram_loo_p10 = percentile(sims, 10)
            model.ngram_loo_min = float(min(sims))
    return model


def attribution_report(z_by_slug: dict[str, list[list[float]]]) -> dict:
    """Leave-one-out authorship attribution over every chunk in the corpus.

    Ask of each passage: of the author centroids, which is closest? The
    passage's own author is scored with that passage removed from their
    centroid, so nothing is graded against itself.

    This is the honest check on whether any of the recognition machinery
    works. If Delta could not tell these authors apart, no threshold built
    from it would mean anything, and the reports should not be trusted.
    """
    centroids = {
        slug: delta_mod.centroid(vectors) for slug, vectors in z_by_slug.items()
    }
    counts = {slug: len(vectors) for slug, vectors in z_by_slug.items()}
    confusion: dict[str, Counter] = {slug: Counter() for slug in z_by_slug}

    per_author: dict[str, dict] = {}
    total = correct_total = 0
    for slug, vectors in z_by_slug.items():
        correct = 0
        n = counts[slug]
        for vector in vectors:
            best_slug = ""
            best_distance = float("inf")
            for other, other_centroid in centroids.items():
                if other == slug:
                    if n < 2:
                        continue
                    # Rebuild this author's centre without the passage itself.
                    other_centroid = [
                        (other_centroid[i] * n - vector[i]) / (n - 1)
                        for i in range(len(vector))
                    ]
                distance = delta_mod.delta_distance(vector, other_centroid)
                if distance < best_distance:
                    best_distance = distance
                    best_slug = other
            confusion[slug][best_slug] += 1
            if best_slug == slug:
                correct += 1
        per_author[slug] = {
            "chunks": n,
            "correct": correct,
            "accuracy": correct / n if n else 0.0,
            "most_confused_with": (
                [s for s, _ in confusion[slug].most_common() if s != slug][:1] or [""]
            )[0],
        }
        total += n
        correct_total += correct

    return {
        "method": "leave-one-out nearest centroid, Burrows's Delta over the "
                  "150 most frequent words",
        "chunks": total,
        "correct": correct_total,
        "accuracy": correct_total / total if total else 0.0,
        "baseline": 1 / len(z_by_slug) if z_by_slug else 0.0,
        "per_author": per_author,
    }


#: First-person pronouns per 1,000 narration words, measured per work.
#: The corpus is sharply bimodal: third-person novels run 0.0-1.6 and
#: first-person novels run 38-70. The band between is not noise - it is
#: Nesbit's fantasies (21-26), third-person stories whose narrator keeps
#: turning round to address the reader as "I".
FIRST_PERSON_RATE = 36.0
INTRUSIVE_NARRATOR_RATE = 12.0


def work_narration(rate: float, work_type: str = "novel") -> str:
    """Label one work's narration from its first-person pronoun rate.

    Decided on the *absolute* rate, never by comparing first-person to
    third-person pronouns: a first-person narrator still calls everyone else
    he and she, so third-person pronouns stay high in both modes and Hastings
    gets misread as an omniscient camera.
    """
    if work_type == "collection":
        if rate >= FIRST_PERSON_RATE:
            return "first-person tales"
        if rate >= INTRUSIVE_NARRATOR_RATE:
            return "mixed tales"
        return "third-person tales"
    if rate >= FIRST_PERSON_RATE:
        return "first person"
    if rate >= INTRUSIVE_NARRATOR_RATE:
        return "third person, intrusive “I” narrator"
    return "third person"


def pov_note(lanes: dict[str, Lane], works: Sequence[WorkSummary]) -> str:
    """A one-line reading of the narration's person and tense.

    Person is decided book by book and then summarised, because most of these
    authors do not use one mode. A whole-corpus average would report Christie
    as third person, which is wrong for three of her five books here.
    """
    labels = [w.narration for w in works if w.included and w.narration]
    counts = Counter(labels)
    total = len(labels)

    if not total:
        person = "unknown"
    elif len(counts) == 1:
        person = labels[0]
    else:
        # Kept short on purpose: this line goes in the index table and the
        # style card. The per-work breakdown is in the report's corpus table.
        ranked = counts.most_common()
        parts = [f"{count} of {total} {label}" for label, count in ranked[:2]]
        if len(ranked) > 2:
            parts.append(f"+{len(ranked) - 2} more")
        person = "mixed across works — " + "; ".join(parts)

    past = lanes["narr_past_marker_per_1k"].median
    present = lanes["narr_present_marker_per_1k"].median
    tense = "past tense" if past > present * 1.5 else "mixed or present tense"
    return f"{person}, {tense}"
