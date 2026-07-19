#!/usr/bin/env python3
"""Tests for the stylometry engine.

    python3 scripts/test_stylo.py

Plain asserts, no test framework, same as the rest of the toolkit: no
installs. These pin the behaviours that are easy to break silently and that
would quietly corrupt every number downstream - sentence splitting around
honorifics and speech, the dialogue/narration boundary, and lane arithmetic.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stylo.delta import (
    Standardiser,
    cosine,
    delta_distance,
    frequency_vector,
    leave_one_out_distances,
    most_frequent_words,
)
from stylo.features import build_sample, mattr, measure, mtld, percentile
from stylo.profile import Lane
from stylo.segment import (
    make_document,
    paragraphs,
    sentence_spans,
    split_dialogue_narration,
    split_sentences,
)

PASSED = 0


def check(condition: bool, label: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(label)
    PASSED += 1


# ---------------------------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------------------------


def test_sentences() -> None:
    text = "Mr. Frome drove to Mrs. J. R. Hale's door. Was he late? He was."
    check(len(split_sentences(text)) == 3, "honorifics and initials must not split")

    text = "“He's looked that way ever since,” Harmon said. She nodded."
    sentences = split_sentences(text)
    check(len(sentences) == 2, "a tag after a closing quote is one sentence")
    check(sentences[0].startswith("“He's"), "quote stays with its tag")

    text = "“Denis Eady! If that's all, I guess there's no hurry.”"
    check(len(split_sentences(text)) == 2, "a multi-sentence speech splits")

    text = "She waited... Nothing came."
    check(len(split_sentences(text)) >= 1, "ellipsis must not crash")

    # Spans must tile the text in order.
    spans = sentence_spans("One. Two. Three.")
    check(spans == sorted(spans), "spans are ordered")
    check(all(a < b for a, b in spans), "spans are non-empty")


def test_dialogue_split() -> None:
    text = '“You came,” she said, and turned to the window.'
    dialogue, narration = split_dialogue_narration(text)
    check(dialogue == "You came,", "dialogue excludes quote marks")
    check("turned to the window" in narration, "narration keeps the beat")
    check("You came" not in narration, "narration excludes the speech")

    dialogue, narration = split_dialogue_narration("She said nothing at all.")
    check(dialogue == "", "no quotes means no dialogue")


def test_multi_sentence_speech_is_not_narration() -> None:
    """The bug worth a permanent test.

    A long speech splits into sentences that each carry an unbalanced quote
    mark. Classifying those by looking for a *complete* quote inside the
    sentence counts them as narration, which inflates every narration
    measurement. They must be classified positionally instead.
    """
    text = '“Denis Eady! If that is all, I guess there is no such hurry to look round.”'
    sample = build_sample(paragraphs(text))
    check(len(sample.sentences) == 2, "speech splits into two sentences")
    check(all(s.has_speech for s in sample.sentences), "both are speech, not narration")
    check(sample.narration_sentences == [], "no narration sentences here")


def test_paragraphs() -> None:
    raw = "---\ntitle: X\n---\n\n# Heading\n\n*Author; original text.*\n\nOne two three.\n\nII\n\nFour five six.\n"
    document = make_document(raw)
    check(len(document.paragraphs) == 2, "headings, italic byline and numerals dropped")
    check(document.paragraphs[0].text == "One two three.", "text preserved")
    check(document.meta["title"] == "X", "front matter parsed")

    # Hard-wrapped lines inside one block join into one paragraph.
    document = make_document("The cat sat\non the mat.\n\nNext one.\n")
    check(len(document.paragraphs) == 2, "wrapped lines join")
    check(document.paragraphs[0].text == "The cat sat on the mat.", "join with a space")


def test_proper_names() -> None:
    text = (
        "Elizabeth turned to the window. The room was cold. "
        "Nobody spoke to Elizabeth. Every morning Elizabeth waited. "
        "Every evening was the same."
    )
    names = make_document(text).proper_names(min_count=2)
    check("elizabeth" in names, "mid-sentence capitals are names")
    check("every" not in names, "sentence-initial capitals are not names")
    check("the" not in names, "articles are not names")


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


def test_measure_shape() -> None:
    from stylo.features import REGISTRY

    document = make_document(
        "Elizabeth stepped into the room; the fire had gone out. "
        "“You came,” said Mrs. Carrington.\n\n"
        "“I came,” Elizabeth said. She had not meant to.\n"
    )
    metrics = measure(document.paragraphs, document.proper_names())
    check(set(metrics) == set(REGISTRY), "every registered metric is returned")
    check(all(isinstance(v, float) for v in metrics.values()), "all values are floats")

    empty = measure([])
    check(set(empty) == set(REGISTRY), "empty input still returns every metric")


def test_rates_and_counts() -> None:
    document = make_document("A short one. " * 10)
    metrics = measure(document.paragraphs)
    check(metrics["sent_very_short_pct"] == 100.0, "1-5 word sentences band correctly")
    check(metrics["sent_longest_band_run"] == 10, "a uniform run is detected")
    check(metrics["dialogue_word_pct"] == 0.0, "no speech means no dialogue share")

    document = make_document("She saw the door. He felt the cold. She realized it.")
    metrics = measure(document.paragraphs)
    check(metrics["filter_phrase_per_1k"] > 0, "filter phrases are counted")

    document = make_document("It was, in that moment, a sense of something.")
    metrics = measure(document.paragraphs)
    check(metrics["crutch_phrase_per_1k"] > 0, "crutch phrases are counted")

    document = make_document("The room was cold — very cold — and still.")
    metrics = measure(document.paragraphs)
    check(metrics["narr_emdash_per_1k"] > 0, "em dashes are counted in narration")


def test_punctuation_is_side_separated() -> None:
    document = make_document('“Well — yes,” she said. The room was quiet.')
    metrics = measure(document.paragraphs)
    check(metrics["dlg_emdash_per_1k"] > 0, "the dash inside speech lands in dialogue")
    check(metrics["narr_emdash_per_1k"] == 0.0, "and not in narration")


def test_lexical_measures() -> None:
    check(abs(mattr(["a"] * 100, 50) - 1 / 50) < 1e-9, "no variety gives the floor")
    check(abs(mattr([str(i) for i in range(100)], 50) - 1.0) < 1e-9, "all types gives 1.0")
    check(mattr([], 50) == 0.0, "empty is 0")
    check(mtld(["a"] * 10) == 0.0, "MTLD needs 50 tokens")
    varied = mtld([str(i % 40) for i in range(200)])
    repetitive = mtld(["a", "b"] * 100)
    check(varied > repetitive, "MTLD ranks variety above repetition")


def test_percentile() -> None:
    values = [1, 2, 3, 4, 5]
    check(percentile(values, 50) == 3, "median")
    check(percentile(values, 0) == 1, "minimum")
    check(percentile(values, 100) == 5, "maximum")
    check(percentile([], 50) == 0.0, "empty is 0")
    check(percentile([7], 90) == 7, "single value")


# ---------------------------------------------------------------------------
# Lanes
# ---------------------------------------------------------------------------


def test_lane_verdicts() -> None:
    lane = Lane(
        key="x", median=10, p10=5, p25=8, p75=12, p90=15, mean=10, sd=3,
    )
    check(lane.verdict(10) == "in_lane", "median is in lane")
    check(lane.verdict(8) == "in_lane", "lane edges are inclusive")
    check(lane.verdict(13) == "wide", "between p75 and p90 is wide")
    check(lane.verdict(20) == "out", "past p90 is out")
    check(lane.verdict(1) == "out", "below p10 is out")
    check(lane.drift(10) == 0.0, "no drift inside the wide range")
    check(lane.drift(15) == 0.0, "the wide edge is not drift")
    check(abs(lane.drift(25) - 1.0) < 1e-9, "a full lane-width past the edge is 1.0")
    check(lane.drift(0) > 0, "drift below the floor is positive")


# ---------------------------------------------------------------------------
# Delta
# ---------------------------------------------------------------------------


def test_delta() -> None:
    a = [["the", "cat", "sat", "on", "the", "mat"] * 20]
    b = [["a", "dog", "ran", "through", "a", "field"] * 20]
    mfw = most_frequent_words(a + b, 10)
    check(len(mfw) <= 10, "MFW is capped")

    vectors = [frequency_vector(t, mfw) for t in a + b]
    standardiser = Standardiser.fit(vectors, mfw)
    za, zb = standardiser.z(vectors[0]), standardiser.z(vectors[1])

    check(delta_distance(za, za) == 0.0, "distance to self is zero")
    check(delta_distance(za, zb) > 0, "different texts are apart")
    check(
        abs(delta_distance(za, zb) - delta_distance(zb, za)) < 1e-9,
        "distance is symmetric",
    )

    round_tripped = Standardiser.from_dict(standardiser.to_dict())
    check(round_tripped.z(vectors[0]) == za, "standardiser survives JSON round-trip")

    check(leave_one_out_distances([za]) == [], "LOO needs two vectors")
    loo = leave_one_out_distances([za, zb, za])
    check(len(loo) == 3, "LOO returns one distance per vector")

    check(abs(cosine([1, 0], [1, 0]) - 1.0) < 1e-9, "identical vectors")
    check(abs(cosine([1, 0], [0, 1])) < 1e-9, "orthogonal vectors")
    check(cosine([0, 0], [1, 1]) == 0.0, "zero vector is safe")


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def test_audit_against_built_profile() -> None:
    """Skipped unless the profiles have been built."""
    import json

    from stylo.audit import audit
    from stylo.corpus import ROOT
    from stylo.profile import AuthorProfile

    path = ROOT / "authors" / "edith-wharton" / "profile" / "profile.json"
    reference_path = ROOT / "stylometry" / "reference" / "delta-model.json"
    if not path.exists() or not reference_path.exists():
        print("  (skipping end-to-end test: run build_author_profiles.py first)")
        return

    profile = AuthorProfile.load(path)
    check(profile.name == "Edith Wharton", "profile loads")
    check(profile.lanes["narr_sent_median"].median > 15, "Wharton writes long narration")
    check(len(profile.delta.centroid) == 150, "centroid has one axis per MFW")

    draft = make_document(
        "Elizabeth stepped in. She saw the letter. She felt afraid.\n\n"
        "Her eyes narrowed — she couldn't help but wonder. In that moment, "
        "a sense of dread.\n\n"
        "\"You came,\" she said.\n\n\"I came,\" he said.\n"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    result = audit(draft, profile, reference, pov="third", tense="past")
    check(result.drifts, "generic model prose drifts from Wharton")
    check(
        any(l.kind == "crutch_phrases" for l in result.locations),
        "crutch phrases are located",
    )
    check(result.brief, "a rewrite brief is produced")
    check(result.primary_in_lane + len(result.drifts) == result.primary_total,
          "the headline count agrees with the drift list")


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{PASSED} checks passed in {len(tests)} tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
