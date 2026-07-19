"""The measurement engine.

``measure(paragraphs)`` returns a flat ``dict[str, float]`` of every feature.
:data:`REGISTRY` describes each feature: which family it belongs to, how to
label and format it, and - importantly - how much to trust it.

Reliability levels mirror section 5 of the guide:

``exact``     deterministic counting; no interpretation involved.
``estimate``  rule-based approximation of something a parser would do better.
``proxy``     a lexicon stands in for a judgement; treat as a weak signal.

Nothing here needs a third-party package.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from statistics import mean, median, pstdev
from typing import Iterable, Sequence

from . import lexicons as lex
from .segment import (
    Paragraph,
    WORD_RE,
    dialogue_spans,
    sentence_spans,
    split_dialogue_narration,
    split_sentences,
    tokens,
    word_count,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    label: str
    family: str
    unit: str = ""
    reliability: str = "exact"
    promptable: bool = False
    higher_is_more: str = ""
    note: str = ""

    def format(self, value: float | None) -> str:
        if value is None:
            return "—"
        if self.unit == "%":
            return f"{value:.1f}%"
        if self.unit == "per_1k":
            return f"{value:.2f}"
        if self.unit == "count":
            return f"{value:.0f}"
        return f"{value:.2f}"


_METRICS: list[Metric] = []


def _m(key, label, family, unit="", reliability="exact", promptable=False, note=""):
    metric = Metric(
        key=key,
        label=label,
        family=family,
        unit=unit,
        reliability=reliability,
        promptable=promptable,
        note=note,
    )
    _METRICS.append(metric)
    return metric


# --- 1/2. Sentence rhythm ---------------------------------------------------
_m("sent_mean", "Mean sentence length", "sentence_rhythm", "words", promptable=True)
_m("sent_median", "Median sentence length", "sentence_rhythm", "words", promptable=True)
_m("sent_p10", "Sentence length, 10th percentile", "sentence_rhythm", "words")
_m("sent_p25", "Sentence length, 25th percentile", "sentence_rhythm", "words")
_m("sent_p75", "Sentence length, 75th percentile", "sentence_rhythm", "words")
_m("sent_p90", "Sentence length, 90th percentile", "sentence_rhythm", "words")
_m("sent_sd", "Sentence length standard deviation", "sentence_rhythm", "words")
_m("sent_cv", "Sentence length coefficient of variation", "sentence_rhythm", "ratio", promptable=True)
_m("sent_very_short_pct", "Very short sentences (1–5 words)", "sentence_rhythm", "%", promptable=True)
_m("sent_short_pct", "Short sentences (6–10 words)", "sentence_rhythm", "%", promptable=True)
_m("sent_medium_pct", "Medium sentences (11–24 words)", "sentence_rhythm", "%", promptable=True)
_m("sent_long_pct", "Long sentences (25–39 words)", "sentence_rhythm", "%", promptable=True)
_m("sent_very_long_pct", "Very long sentences (40+ words)", "sentence_rhythm", "%", promptable=True)
_m("sent_adjacent_delta", "Mean length change between adjacent sentences", "sentence_rhythm", "words", promptable=True)
_m("sent_longest_band_run", "Longest run of sentences in one length band", "sentence_rhythm", "count", promptable=True)
_m("narr_sent_median", "Median narration sentence length", "sentence_rhythm", "words", promptable=True,
   note="A narration sentence is one that quotes nobody; mixed speech-plus-tag "
        "sentences are counted under dialogue instead.")
_m("narr_sent_mean", "Mean narration sentence length", "sentence_rhythm", "words")
_m("fragment_pct", "Fragments (no finite verb)", "sentence_rhythm", "%", "estimate", promptable=True,
   note="Rule-based; a parser would classify these more accurately.")
_m("question_pct", "Sentences ending in a question mark", "sentence_rhythm", "%")
_m("exclamation_pct", "Sentences ending in an exclamation mark", "sentence_rhythm", "%")

# --- 3/4. Paragraph rhythm --------------------------------------------------
_m("para_mean_words", "Mean paragraph length", "paragraph_rhythm", "words", promptable=True)
_m("para_median_words", "Median paragraph length", "paragraph_rhythm", "words", promptable=True)
_m("para_p90_words", "Paragraph length, 90th percentile", "paragraph_rhythm", "words")
_m("para_mean_sentences", "Mean sentences per paragraph", "paragraph_rhythm", "ratio", promptable=True)
_m("para_median_sentences", "Median sentences per paragraph", "paragraph_rhythm", "ratio", promptable=True)
_m("para_one_sentence_pct", "One-sentence paragraphs", "paragraph_rhythm", "%", promptable=True)
_m("para_one_sentence_narration_pct", "One-sentence narration paragraphs", "paragraph_rhythm", "%", promptable=True,
   note="Excludes paragraphs containing speech, where one sentence is normal.")
_m("para_over_100_pct", "Paragraphs over 100 words", "paragraph_rhythm", "%", promptable=True)
_m("para_over_150_pct", "Paragraphs over 150 words", "paragraph_rhythm", "%")
_m("para_short_run_max", "Longest run of short paragraphs (≤25 words)", "paragraph_rhythm", "count", promptable=True)
_m("para_long_run_max", "Longest run of long paragraphs (≥100 words)", "paragraph_rhythm", "count")
_m("para_dialogue_mean_words", "Mean length of paragraphs containing speech", "paragraph_rhythm", "words")
_m("para_narration_mean_words", "Mean length of narration-only paragraphs", "paragraph_rhythm", "words", promptable=True)

# --- 5/6/7. Dialogue architecture ------------------------------------------
_m("dialogue_word_pct", "Words inside direct speech", "dialogue", "%", promptable=True)
_m("dialogue_para_pct", "Paragraphs containing speech", "dialogue", "%", promptable=True)
_m("utterance_mean_words", "Mean speech length", "dialogue", "words", promptable=True)
_m("utterance_median_words", "Median speech length", "dialogue", "words", promptable=True)
_m("utterance_p90_words", "Speech length, 90th percentile", "dialogue", "words")
_m("utterance_short_pct", "Fragmentary replies (≤3 words)", "dialogue", "%", promptable=True)
_m("utterance_long_pct", "Long speeches (40+ words)", "dialogue", "%", promptable=True)
_m("utterance_length_cv", "Speech length coefficient of variation", "dialogue", "ratio", promptable=True,
   note="Low values mean every speech is the same size - a common AI tell.")
_m("dialogue_question_per_1k", "Questions per 1,000 dialogue words", "dialogue", "per_1k", promptable=True)
_m("dialogue_exclamation_per_1k", "Exclamations per 1,000 dialogue words", "dialogue", "per_1k", promptable=True)
_m("dialogue_contraction_per_1k", "Contractions per 1,000 dialogue words", "dialogue", "per_1k", promptable=True)
_m("narration_contraction_per_1k", "Contractions per 1,000 narration words", "dialogue", "per_1k", promptable=True)
_m("tagged_utterance_pct", "Speeches carrying a dialogue tag", "dialogue", "%", "estimate", promptable=True)
_m("tag_said_pct", "Tags using said/say", "dialogue", "%", "estimate", promptable=True)
_m("tag_neutral_pct", "Tags using said/asked/replied/answered", "dialogue", "%", "estimate", promptable=True)
_m("tag_marked_pct", "Tags using marked alternatives", "dialogue", "%", "estimate", promptable=True,
   note="exclaimed, retorted, murmured, and similar.")
_m("tag_adverb_pct", "Tags carrying an -ly adverb", "dialogue", "%", "estimate", promptable=True)
_m("tag_diversity", "Distinct tag verbs ÷ tagged speeches", "dialogue", "ratio", "estimate")
_m("unattributed_utterance_pct", "Speeches with no tag and no beat", "dialogue", "%", "estimate", promptable=True)
_m("action_beat_pct", "Speeches accompanied by an action beat", "dialogue", "%", "estimate", promptable=True)
_m("utterance_interrupt_pct", "Speeches broken off with an em dash", "dialogue", "%", promptable=True)
_m("utterance_trail_pct", "Speeches trailing off with an ellipsis", "dialogue", "%", promptable=True)
_m("dialogue_run_max", "Longest run of consecutive speech paragraphs", "dialogue", "count", promptable=True)
_m("dialogue_run_mean", "Mean turns per exchange", "dialogue", "ratio", promptable=True)

# --- 8. Punctuation ---------------------------------------------------------
for _side, _label in (("narr", "narration"), ("dlg", "dialogue")):
    _m(f"{_side}_comma_per_1k", f"Commas per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_semicolon_per_1k", f"Semicolons per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_colon_per_1k", f"Colons per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_emdash_per_1k", f"Em dashes per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_paren_per_1k", f"Parentheses per 1,000 {_label} words", "punctuation", "per_1k")
    _m(f"{_side}_ellipsis_per_1k", f"Ellipses per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_question_per_1k", f"Question marks per 1,000 {_label} words", "punctuation", "per_1k")
    _m(f"{_side}_exclamation_per_1k", f"Exclamation marks per 1,000 {_label} words", "punctuation", "per_1k", promptable=True)
    _m(f"{_side}_hyphen_per_1k", f"Hyphens per 1,000 {_label} words", "punctuation", "per_1k")
_m("apostrophe_per_1k", "Apostrophes per 1,000 words", "punctuation", "per_1k")

# --- 9. Function words ------------------------------------------------------
for _group, _ in lex.FUNCTION_WORD_GROUPS:
    _m(f"fw_{_group}_per_1k", f"{_group.replace('_', ' ').capitalize()} per 1,000 words",
       "function_words", "per_1k")
_m("fw_narr_demonstrative_opener_pct", "Sentences opening on a demonstrative", "function_words", "%", promptable=True,
   note="\"This was\", \"That was\" - a frequent model habit.")

# --- 10. Pronouns and POV ---------------------------------------------------
_m("narr_first_person_per_1k", "First-person pronouns per 1,000 narration words", "pov", "per_1k", promptable=True)
_m("narr_second_person_per_1k", "Second-person pronouns per 1,000 narration words", "pov", "per_1k")
_m("narr_third_person_per_1k", "Third-person pronouns per 1,000 narration words", "pov", "per_1k", promptable=True)
_m("narr_masculine_per_1k", "Masculine pronouns per 1,000 narration words", "pov", "per_1k")
_m("narr_feminine_per_1k", "Feminine pronouns per 1,000 narration words", "pov", "per_1k")
_m("narr_plural_third_per_1k", "Plural third-person pronouns per 1,000 narration words", "pov", "per_1k")
_m("narr_neuter_per_1k", "Neuter pronouns per 1,000 narration words", "pov", "per_1k")
_m("name_per_1k", "Proper-name tokens per 1,000 words", "pov", "per_1k", "estimate")
_m("name_to_pronoun_ratio", "Proper names ÷ third-person pronouns", "pov", "ratio", "estimate", promptable=True)

# --- 11. Verbs and tense ----------------------------------------------------
_m("narr_past_marker_per_1k", "Past-tense markers per 1,000 narration words", "verbs", "per_1k", "estimate", promptable=True)
_m("narr_present_marker_per_1k", "Present-tense markers per 1,000 narration words", "verbs", "per_1k", "estimate", promptable=True)
_m("narr_progressive_per_1k", "Progressives (was walking) per 1,000 narration words", "verbs", "per_1k", "estimate", promptable=True)
_m("narr_perfect_per_1k", "Perfects (had walked) per 1,000 narration words", "verbs", "per_1k", "estimate", promptable=True)
_m("narr_passive_per_1k", "Passives per 1,000 narration words", "verbs", "per_1k", "estimate", promptable=True)
_m("narr_modal_per_1k", "Modals per 1,000 narration words", "verbs", "per_1k", promptable=True)
_m("narr_be_per_1k", "Forms of be per 1,000 narration words", "verbs", "per_1k")
_m("narr_motion_verb_per_1k", "Motion verbs per 1,000 narration words", "verbs", "per_1k", "proxy")
_m("narr_perception_verb_per_1k", "Perception verbs per 1,000 narration words", "verbs", "per_1k", "proxy")
_m("narr_cognition_verb_per_1k", "Cognition verbs per 1,000 narration words", "verbs", "per_1k", "proxy", promptable=True)
_m("narr_emotion_verb_per_1k", "Emotion verbs per 1,000 narration words", "verbs", "per_1k", "proxy")

# --- 12/13. Syntax ----------------------------------------------------------
_m("subordination_per_sentence", "Subordinate clause markers per sentence", "syntax", "ratio", "estimate", promptable=True)
_m("subordinate_sentence_pct", "Sentences carrying subordination", "syntax", "%", "estimate", promptable=True)
_m("relative_clause_sentence_pct", "Sentences with a relative clause", "syntax", "%", "estimate", promptable=True)
_m("conditional_sentence_pct", "Sentences with a conditional clause", "syntax", "%", "estimate")
_m("coordination_per_sentence", "Clause coordination per sentence", "syntax", "ratio", "estimate", promptable=True)
_m("preposition_per_sentence", "Prepositions per sentence", "syntax", "ratio", promptable=True)
_m("appositive_per_1k", "Appositive-shaped commas per 1,000 words", "syntax", "per_1k", "estimate")
_m("open_name_pct", "Openings: character name", "openings", "%", "estimate", promptable=True)
_m("open_pronoun_pct", "Openings: pronoun", "openings", "%", "estimate", promptable=True)
_m("open_article_pct", "Openings: article + noun", "openings", "%", "estimate", promptable=True)
_m("open_preposition_pct", "Openings: prepositional phrase", "openings", "%", "estimate", promptable=True)
_m("open_subordinate_pct", "Openings: subordinate clause", "openings", "%", "estimate", promptable=True)
_m("open_participial_pct", "Openings: participial phrase", "openings", "%", "estimate", promptable=True)
_m("open_dialogue_pct", "Openings: dialogue", "openings", "%", "estimate", promptable=True)
_m("open_conjunction_pct", "Openings: coordinating conjunction", "openings", "%", "estimate", promptable=True)
_m("open_adverb_pct", "Openings: adverb", "openings", "%", "estimate", promptable=True)
_m("open_other_pct", "Openings: other", "openings", "%", "estimate")
_m("open_repeat_pct", "Sentences repeating another sentence's first two words", "openings", "%", promptable=True)
_m("open_name_action_pct", "Openings: name + immediate simple action", "openings", "%", "estimate", promptable=True,
   note="The \"Elizabeth turned…\" pattern the guide warns about.")

# --- 14/15. Lexis and repetition -------------------------------------------
_m("mattr_50", "MATTR (50-word window)", "lexis", "ratio", promptable=True)
_m("mattr_500", "MATTR (500-word window)", "lexis", "ratio")
_m("mtld", "MTLD", "lexis", "ratio")
_m("hapax_pct", "Words used exactly once", "lexis", "%")
_m("lexical_density", "Content words ÷ all words", "lexis", "ratio", promptable=True)
_m("mean_word_length", "Mean word length", "lexis", "characters")
_m("long_word_pct", "Words of 8+ letters", "lexis", "%", promptable=True)
_m("repeat_4gram_per_1k", "Repeated 4-word phrases per 1,000 words", "lexis", "per_1k", promptable=True)
_m("repeat_content_100w_per_1k", "Content words repeating within 100 words", "lexis", "per_1k", promptable=True)

# --- 16. Concreteness and senses -------------------------------------------
_m("sensory_per_1k", "Sensory terms per 1,000 words", "senses", "per_1k", "proxy", promptable=True)
for _mode in ("sight", "sound", "touch", "smell", "taste", "temperature", "body"):
    _m(f"sense_{_mode}_per_1k", f"Sensory: {_mode} per 1,000 words", "senses", "per_1k", "proxy")
_m("emotion_label_per_1k", "Named emotions per 1,000 words", "senses", "per_1k", "proxy", promptable=True)
_m("abstract_noun_per_1k", "Abstract nominalisations per 1,000 words", "senses", "per_1k", "proxy", promptable=True)
_m("spatial_per_1k", "Spatial terms per 1,000 words", "senses", "per_1k", "proxy")
_m("concrete_abstract_ratio", "Sensory+body ÷ abstract nouns", "senses", "ratio", "proxy", promptable=True)

# --- 17. Crutch and filter phrases -----------------------------------------
_m("filter_phrase_per_1k", "Filter phrases per 1,000 words", "crutches", "per_1k", promptable=True,
   note="she saw, he felt, she realized, seemed to, began to…")
_m("crutch_phrase_per_1k", "Modern crutch phrases per 1,000 words", "crutches", "per_1k", promptable=True,
   note="Near zero in every public-domain author. A one-directional alarm for drafts.")

REGISTRY: dict[str, Metric] = {m.key: m for m in _METRICS}
FAMILIES: tuple[str, ...] = tuple(dict.fromkeys(m.family for m in _METRICS))

FAMILY_LABELS = {
    "sentence_rhythm": "Sentence rhythm",
    "paragraph_rhythm": "Paragraph rhythm",
    "dialogue": "Dialogue architecture",
    "punctuation": "Punctuation habits",
    "function_words": "Function words",
    "pov": "Pronouns and point of view",
    "verbs": "Verbs and tense",
    "syntax": "Syntax and clause construction",
    "openings": "Sentence openings",
    "lexis": "Lexical diversity and repetition",
    "senses": "Concreteness and sensory attention",
    "crutches": "Filter and crutch phrases",
}

#: The compact set the audit reports on first - the guide's starter system.
PRIMARY_METRICS: tuple[str, ...] = (
    "narr_sent_median",
    "sent_cv",
    "sent_very_short_pct",
    "sent_long_pct",
    "sent_longest_band_run",
    "para_median_words",
    "para_mean_sentences",
    "para_one_sentence_narration_pct",
    "para_short_run_max",
    "dialogue_word_pct",
    "utterance_median_words",
    "utterance_length_cv",
    "tag_said_pct",
    "narr_comma_per_1k",
    "narr_semicolon_per_1k",
    "narr_emdash_per_1k",
    "narr_exclamation_per_1k",
    "narr_modal_per_1k",
    "subordinate_sentence_pct",
    "open_repeat_pct",
    "open_name_action_pct",
    "mattr_50",
    "lexical_density",
    "filter_phrase_per_1k",
    "sensory_per_1k",
    "emotion_label_per_1k",
    "abstract_noun_per_1k",
    "repeat_4gram_per_1k",
)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_FILTER_RES = [re.compile(rf"\b{p}\b", re.IGNORECASE) for p in lex.FILTER_PHRASES]
_CRUTCH_RES = [re.compile(rf"\b{p}\b", re.IGNORECASE) for p in lex.CRUTCH_PHRASES]
_EMDASH_RE = re.compile(r"—|--")
_ELLIPSIS_RE = re.compile(r"…|\.\.\.")
_APOSTROPHE_RE = re.compile(r"[A-Za-z][’'][A-Za-z]")
_CONTRACTION_RE = re.compile(
    r"\b\w+[’'](?:s|t|d|ll|re|ve|m|em)\b|\bcan[’']t\b|\bwon[’']t\b", re.IGNORECASE
)
_COMMA_COORD_RE = re.compile(r",\s+(?:and|but|or|nor|yet|so)\b", re.IGNORECASE)
_APPOSITIVE_RE = re.compile(r",\s+(?:a|an|the)\s+[a-z]+[^,.;:]{0,40},")
_ING_RE = re.compile(r"\b\w+ing\b")
_ED_RE = re.compile(r"\b\w+ed\b")
_LY_RE = re.compile(r"\b\w+ly\b")

_VERBISH = (
    lex.BE_FORMS | lex.HAVE_FORMS | lex.DO_FORMS | lex.MODALS | lex.IRREGULAR_PAST
    | lex.SPEECH_VERBS | lex.MOTION_VERBS | lex.PERCEPTION_VERBS
    | lex.COGNITION_VERBS | lex.EMOTION_VERBS
)

_SUBORD_MARKERS = lex.SUBORDINATE_OPENERS | {
    "because", "although", "though", "unless", "until", "whereas", "since",
    "while", "whilst", "if", "when", "whenever", "after", "before", "lest",
}
_RELATIVE_MARKERS = frozenset({"who", "whom", "whose", "which"})

_ING_STOP = frozenset(
    {"nothing", "something", "anything", "everything", "morning", "evening",
     "spring", "king", "thing", "during", "being", "ring", "string", "wing",
     "ceiling", "willing", "darling", "shilling", "building"}
)

# ---------------------------------------------------------------------------
# Small statistics helpers
# ---------------------------------------------------------------------------


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile. ``q`` in 0..100."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * (q / 100.0)
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    frac = pos - low
    return float(ordered[low] * (1 - frac) + ordered[high] * frac)


def _rate(count: float, words: float) -> float:
    return 0.0 if not words else count * 1000.0 / words


def _pct(count: float, total: float) -> float:
    return 0.0 if not total else count * 100.0 / total


def _safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return float(mean(vals)) if vals else 0.0


def _safe_median(values: Iterable[float]) -> float:
    vals = list(values)
    return float(median(vals)) if vals else 0.0


def mattr(word_tokens: Sequence[str], window: int) -> float:
    """Moving-average type-token ratio (Covington & McFall)."""
    n = len(word_tokens)
    if n == 0:
        return 0.0
    if n <= window:
        return len(set(word_tokens)) / n
    counts: Counter[str] = Counter(word_tokens[:window])
    total = len(counts) / window
    windows = 1
    for i in range(window, n):
        drop = word_tokens[i - window]
        counts[drop] -= 1
        if counts[drop] == 0:
            del counts[drop]
        counts[word_tokens[i]] += 1
        total += len(counts) / window
        windows += 1
    return total / windows


def _mtld_pass(word_tokens: Sequence[str], threshold: float = 0.72) -> float:
    factors = 0.0
    types: set[str] = set()
    count = 0
    for word in word_tokens:
        types.add(word)
        count += 1
        ttr = len(types) / count
        if ttr <= threshold:
            factors += 1
            types = set()
            count = 0
    if count:
        ttr = len(types) / count
        if (1 - threshold) != 0:
            factors += (1 - ttr) / (1 - threshold)
    return len(word_tokens) / factors if factors else float(len(word_tokens))


def mtld(word_tokens: Sequence[str], threshold: float = 0.72) -> float:
    """Measure of textual lexical diversity, forward and backward averaged."""
    if len(word_tokens) < 50:
        return 0.0
    forward = _mtld_pass(word_tokens, threshold)
    backward = _mtld_pass(list(reversed(word_tokens)), threshold)
    return (forward + backward) / 2


def _longest_run(labels: Sequence) -> int:
    best = current = 0
    previous = object()
    for label in labels:
        if label == previous:
            current += 1
        else:
            current = 1
            previous = label
        best = max(best, current)
    return best


def _band(length: int) -> str:
    if length <= 5:
        return "very_short"
    if length <= 10:
        return "short"
    if length <= 24:
        return "medium"
    if length <= 39:
        return "long"
    return "very_long"


# ---------------------------------------------------------------------------
# Sample assembly
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Sentence:
    text: str
    para_index: int
    words: int
    in_dialogue_para: bool
    has_speech: bool = False


@dataclass(slots=True)
class Sample:
    """Everything the feature functions need, computed once."""

    paragraphs: list[Paragraph]
    names: frozenset[str]

    text: str = ""
    dialogue_text: str = ""
    narration_text: str = ""
    all_tokens: list[str] = None          # type: ignore[assignment]
    narration_tokens: list[str] = None    # type: ignore[assignment]
    dialogue_tokens: list[str] = None     # type: ignore[assignment]
    sentences: list[Sentence] = None      # type: ignore[assignment]
    narration_sentences: list[str] = None  # type: ignore[assignment]
    utterances: list[str] = None          # type: ignore[assignment]
    para_words: list[int] = None          # type: ignore[assignment]
    para_sentences: list[int] = None      # type: ignore[assignment]
    para_has_speech: list[bool] = None    # type: ignore[assignment]

    def __post_init__(self) -> None:
        dialogue_parts: list[str] = []
        narration_parts: list[str] = []
        self.sentences = []
        self.para_words = []
        self.para_sentences = []
        self.para_has_speech = []
        self.utterances = []

        for para in self.paragraphs:
            dialogue, narration = split_dialogue_narration(para.text)
            has_speech = bool(dialogue_spans(para.text))
            if dialogue:
                dialogue_parts.append(dialogue)
            if narration:
                narration_parts.append(narration)
            for start, end in dialogue_spans(para.text):
                self.utterances.append(para.text[start + 1:end - 1])

            spans = sentence_spans(para.text)
            quote_spans = dialogue_spans(para.text)
            self.para_sentences.append(len(spans))
            self.para_words.append(word_count(para.text))
            self.para_has_speech.append(has_speech)
            for start, end in spans:
                sentence = para.text[start:end].strip()
                if not sentence:
                    continue
                overlap = sum(
                    max(0, min(end, qe) - max(start, qs)) for qs, qe in quote_spans
                )
                self.sentences.append(
                    Sentence(
                        text=sentence,
                        para_index=para.index,
                        words=word_count(sentence),
                        in_dialogue_para=has_speech,
                        has_speech=overlap > 0,
                    )
                )

        self.text = "\n\n".join(p.text for p in self.paragraphs)
        self.dialogue_text = " ".join(dialogue_parts)
        self.narration_text = " ".join(narration_parts)
        self.all_tokens = tokens(self.text)
        self.dialogue_tokens = tokens(self.dialogue_text)
        self.narration_tokens = tokens(self.narration_text)
        # Narration sentences are whole sentences that quote nobody. Re-splitting
        # the joined narration blob would stitch "he said," onto the next
        # paragraph's opening and inflate every length measure, so don't.
        self.narration_sentences = [x.text for x in self.sentences if not x.has_speech]

    @property
    def words(self) -> int:
        return len(self.all_tokens)


def build_sample(paras: Sequence[Paragraph], names: frozenset[str] = frozenset()) -> Sample:
    return Sample(paragraphs=list(paras), names=names)


# ---------------------------------------------------------------------------
# Feature families
# ---------------------------------------------------------------------------


def _has_verb(sentence: str) -> bool:
    toks = tokens(sentence)
    if any(t in _VERBISH for t in toks):
        return True
    if _ED_RE.search(sentence.lower()):
        return True
    return False


def _sentence_rhythm(s: Sample, out: dict[str, float]) -> None:
    lengths = [x.words for x in s.sentences if x.words]
    out["sent_mean"] = _safe_mean(lengths)
    out["sent_median"] = _safe_median(lengths)
    for q in (10, 25, 75, 90):
        out[f"sent_p{q}"] = percentile(lengths, q)
    out["sent_sd"] = float(pstdev(lengths)) if len(lengths) > 1 else 0.0
    out["sent_cv"] = out["sent_sd"] / out["sent_mean"] if out["sent_mean"] else 0.0

    bands = [_band(n) for n in lengths]
    total = len(lengths)
    counter = Counter(bands)
    out["sent_very_short_pct"] = _pct(counter["very_short"], total)
    out["sent_short_pct"] = _pct(counter["short"], total)
    out["sent_medium_pct"] = _pct(counter["medium"], total)
    out["sent_long_pct"] = _pct(counter["long"], total)
    out["sent_very_long_pct"] = _pct(counter["very_long"], total)
    out["sent_longest_band_run"] = float(_longest_run(bands))
    out["sent_adjacent_delta"] = _safe_mean(
        abs(b - a) for a, b in zip(lengths, lengths[1:])
    )

    narr_lengths = [word_count(x) for x in s.narration_sentences]
    narr_lengths = [n for n in narr_lengths if n]
    out["narr_sent_median"] = _safe_median(narr_lengths)
    out["narr_sent_mean"] = _safe_mean(narr_lengths)

    narr = s.narration_sentences
    out["fragment_pct"] = _pct(sum(1 for x in narr if not _has_verb(x)), len(narr))
    out["question_pct"] = _pct(
        sum(1 for x in s.sentences if x.text.rstrip("”\"' ").endswith("?")), len(s.sentences)
    )
    out["exclamation_pct"] = _pct(
        sum(1 for x in s.sentences if x.text.rstrip("”\"' ").endswith("!")), len(s.sentences)
    )


def _paragraph_rhythm(s: Sample, out: dict[str, float]) -> None:
    words = s.para_words
    out["para_mean_words"] = _safe_mean(words)
    out["para_median_words"] = _safe_median(words)
    out["para_p90_words"] = percentile(words, 90)
    out["para_mean_sentences"] = _safe_mean(s.para_sentences)
    out["para_median_sentences"] = _safe_median(s.para_sentences)
    out["para_one_sentence_pct"] = _pct(sum(1 for n in s.para_sentences if n == 1), len(words))
    narration_only = [
        n for n, speech in zip(s.para_sentences, s.para_has_speech) if not speech
    ]
    out["para_one_sentence_narration_pct"] = _pct(
        sum(1 for n in narration_only if n == 1), len(narration_only)
    )
    out["para_over_100_pct"] = _pct(sum(1 for n in words if n > 100), len(words))
    out["para_over_150_pct"] = _pct(sum(1 for n in words if n > 150), len(words))
    out["para_short_run_max"] = float(_longest_run_true([n <= 25 for n in words]))
    out["para_long_run_max"] = float(_longest_run_true([n >= 100 for n in words]))
    out["para_dialogue_mean_words"] = _safe_mean(
        [n for n, speech in zip(words, s.para_has_speech) if speech]
    )
    out["para_narration_mean_words"] = _safe_mean(
        [n for n, speech in zip(words, s.para_has_speech) if not speech]
    )


def _longest_run_true(flags: Sequence[bool]) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def _tag_info(para_text: str, span: tuple[int, int]) -> tuple[str | None, bool, bool]:
    """Inspect the narration around one speech span.

    Returns ``(tag_verb, has_adverb, has_action_beat)``.
    """
    start, end = span
    after = para_text[end:]
    before = para_text[:start]
    # A tag sits immediately after the closing quote, or just before the open.
    window_after = " ".join(tokens(after)[:6])
    window_before = " ".join(tokens(before)[-6:])
    tag: str | None = None
    for window in (window_after, window_before):
        for token in window.split():
            if token in lex.SPEECH_VERBS:
                tag = token
                break
        if tag:
            break
    has_adverb = False
    if tag:
        window = window_after if tag in window_after.split() else window_before
        has_adverb = bool(_LY_RE.search(window))
    # An action beat: narration in this paragraph that is not the tag.
    narration = (before + " " + after).strip()
    beat = bool(narration) and not tag and bool(WORD_RE.search(narration))
    if tag:
        # Narration well beyond the tag counts as a beat too.
        beat = word_count(narration) > 6
    return tag, has_adverb, beat


def _dialogue(s: Sample, out: dict[str, float]) -> None:
    total_words = s.words
    dialogue_words = len(s.dialogue_tokens)
    out["dialogue_word_pct"] = _pct(dialogue_words, total_words)
    out["dialogue_para_pct"] = _pct(sum(s.para_has_speech), len(s.paragraphs))

    lengths = [word_count(u) for u in s.utterances]
    lengths = [n for n in lengths if n]
    out["utterance_mean_words"] = _safe_mean(lengths)
    out["utterance_median_words"] = _safe_median(lengths)
    out["utterance_p90_words"] = percentile(lengths, 90)
    out["utterance_short_pct"] = _pct(sum(1 for n in lengths if n <= 3), len(lengths))
    out["utterance_long_pct"] = _pct(sum(1 for n in lengths if n >= 40), len(lengths))
    sd = float(pstdev(lengths)) if len(lengths) > 1 else 0.0
    out["utterance_length_cv"] = sd / out["utterance_mean_words"] if out["utterance_mean_words"] else 0.0

    out["dialogue_question_per_1k"] = _rate(s.dialogue_text.count("?"), dialogue_words)
    out["dialogue_exclamation_per_1k"] = _rate(s.dialogue_text.count("!"), dialogue_words)
    out["dialogue_contraction_per_1k"] = _rate(
        len(_CONTRACTION_RE.findall(s.dialogue_text)), dialogue_words
    )
    out["narration_contraction_per_1k"] = _rate(
        len(_CONTRACTION_RE.findall(s.narration_text)), len(s.narration_tokens)
    )

    tags: list[str] = []
    adverb_tags = 0
    beats = 0
    unattributed = 0
    utterance_count = 0
    for para in s.paragraphs:
        for span in dialogue_spans(para.text):
            utterance_count += 1
            tag, has_adverb, beat = _tag_info(para.text, span)
            if tag:
                tags.append(tag)
                if has_adverb:
                    adverb_tags += 1
            if beat:
                beats += 1
            if not tag and not beat:
                unattributed += 1

    out["tagged_utterance_pct"] = _pct(len(tags), utterance_count)
    out["tag_said_pct"] = _pct(sum(1 for t in tags if t in lex.NEUTRAL_TAGS), len(tags))
    neutral_extended = lex.NEUTRAL_TAGS | {
        "asked", "asks", "ask", "replied", "replies", "reply",
        "answered", "answers", "answer",
    }
    out["tag_neutral_pct"] = _pct(sum(1 for t in tags if t in neutral_extended), len(tags))
    out["tag_marked_pct"] = _pct(sum(1 for t in tags if t in lex.MARKED_TAGS), len(tags))
    out["tag_adverb_pct"] = _pct(adverb_tags, len(tags))
    out["tag_diversity"] = (len(set(tags)) / len(tags)) if tags else 0.0
    out["unattributed_utterance_pct"] = _pct(unattributed, utterance_count)
    out["action_beat_pct"] = _pct(beats, utterance_count)

    out["utterance_interrupt_pct"] = _pct(
        sum(1 for u in s.utterances if u.rstrip().endswith(("—", "--"))), len(s.utterances)
    )
    out["utterance_trail_pct"] = _pct(
        sum(1 for u in s.utterances if u.rstrip().endswith(("…", "..."))), len(s.utterances)
    )

    runs: list[int] = []
    current = 0
    for speech in s.para_has_speech:
        if speech:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    out["dialogue_run_max"] = float(max(runs)) if runs else 0.0
    out["dialogue_run_mean"] = _safe_mean(runs)


def _punctuation(s: Sample, out: dict[str, float]) -> None:
    for side, text, words in (
        ("narr", s.narration_text, len(s.narration_tokens)),
        ("dlg", s.dialogue_text, len(s.dialogue_tokens)),
    ):
        out[f"{side}_comma_per_1k"] = _rate(text.count(","), words)
        out[f"{side}_semicolon_per_1k"] = _rate(text.count(";"), words)
        out[f"{side}_colon_per_1k"] = _rate(text.count(":"), words)
        out[f"{side}_emdash_per_1k"] = _rate(len(_EMDASH_RE.findall(text)), words)
        out[f"{side}_paren_per_1k"] = _rate(text.count("("), words)
        out[f"{side}_ellipsis_per_1k"] = _rate(len(_ELLIPSIS_RE.findall(text)), words)
        out[f"{side}_question_per_1k"] = _rate(text.count("?"), words)
        out[f"{side}_exclamation_per_1k"] = _rate(text.count("!"), words)
        out[f"{side}_hyphen_per_1k"] = _rate(len(re.findall(r"\w-\w", text)), words)
    out["apostrophe_per_1k"] = _rate(len(_APOSTROPHE_RE.findall(s.text)), s.words)


def _function_words(s: Sample, out: dict[str, float]) -> None:
    counts = Counter(s.all_tokens)
    total = s.words
    for group, words in lex.FUNCTION_WORD_GROUPS:
        hits = sum(counts[w] for w in words)
        out[f"fw_{group}_per_1k"] = _rate(hits, total)
    demonstrative_openers = 0
    for sentence in s.narration_sentences:
        first = tokens(sentence)[:1]
        if first and first[0] in lex.DEMONSTRATIVES:
            demonstrative_openers += 1
    out["fw_narr_demonstrative_opener_pct"] = _pct(
        demonstrative_openers, len(s.narration_sentences)
    )


def _pov(s: Sample, out: dict[str, float]) -> None:
    counts = Counter(s.narration_tokens)
    words = len(s.narration_tokens)
    out["narr_first_person_per_1k"] = _rate(sum(counts[w] for w in lex.FIRST_PERSON), words)
    out["narr_second_person_per_1k"] = _rate(sum(counts[w] for w in lex.SECOND_PERSON), words)
    out["narr_third_person_per_1k"] = _rate(sum(counts[w] for w in lex.THIRD_PERSON), words)
    out["narr_masculine_per_1k"] = _rate(sum(counts[w] for w in lex.MASCULINE_PRONOUNS), words)
    out["narr_feminine_per_1k"] = _rate(sum(counts[w] for w in lex.FEMININE_PRONOUNS), words)
    out["narr_plural_third_per_1k"] = _rate(sum(counts[w] for w in lex.PLURAL_THIRD_PRONOUNS), words)
    out["narr_neuter_per_1k"] = _rate(sum(counts[w] for w in lex.NEUTER_PRONOUNS), words)

    all_counts = Counter(s.all_tokens)
    name_hits = sum(all_counts[n] for n in s.names)
    out["name_per_1k"] = _rate(name_hits, s.words)
    third = sum(all_counts[w] for w in lex.THIRD_PERSON)
    out["name_to_pronoun_ratio"] = (name_hits / third) if third else 0.0


def _verbs(s: Sample, out: dict[str, float]) -> None:
    toks = s.narration_tokens
    words = len(toks)
    counts = Counter(toks)
    text = s.narration_text.lower()

    past = sum(counts[w] for w in lex.IRREGULAR_PAST)
    past += sum(1 for t in toks if t.endswith("ed") and len(t) > 3 and t not in lex.IRREGULAR_PAST)
    out["narr_past_marker_per_1k"] = _rate(past, words)
    out["narr_present_marker_per_1k"] = _rate(
        sum(counts[w] for w in lex.PRESENT_MARKERS), words
    )

    progressive = 0
    perfect = 0
    passive = 0
    for i, token in enumerate(toks[:-1]):
        nxt = toks[i + 1]
        if token in lex.BE_FORMS and nxt.endswith("ing") and nxt not in _ING_STOP:
            progressive += 1
        if token in lex.HAVE_FORMS and (nxt in lex.PAST_PARTICIPLES or nxt.endswith("ed")):
            perfect += 1
        if token in lex.BE_FORMS and (nxt in lex.PAST_PARTICIPLES or nxt.endswith("ed")):
            passive += 1
    out["narr_progressive_per_1k"] = _rate(progressive, words)
    out["narr_perfect_per_1k"] = _rate(perfect, words)
    out["narr_passive_per_1k"] = _rate(passive, words)
    out["narr_modal_per_1k"] = _rate(sum(counts[w] for w in lex.MODALS), words)
    out["narr_be_per_1k"] = _rate(sum(counts[w] for w in lex.BE_FORMS), words)
    out["narr_motion_verb_per_1k"] = _rate(sum(counts[w] for w in lex.MOTION_VERBS), words)
    out["narr_perception_verb_per_1k"] = _rate(sum(counts[w] for w in lex.PERCEPTION_VERBS), words)
    out["narr_cognition_verb_per_1k"] = _rate(sum(counts[w] for w in lex.COGNITION_VERBS), words)
    out["narr_emotion_verb_per_1k"] = _rate(sum(counts[w] for w in lex.EMOTION_VERBS), words)


def _classify_opening(sentence: str, names: frozenset[str]) -> str:
    stripped = sentence.lstrip("—- ")
    if stripped[:1] in {"“", "\""}:
        return "dialogue"
    toks = tokens(stripped)
    if not toks:
        return "other"
    first = toks[0]
    if first in lex.COORDINATORS and first != "for":
        return "conjunction"
    if first in lex.SUBORDINATE_OPENERS:
        return "subordinate"
    if first in names:
        return "name"
    if first in lex.ALL_PRONOUNS:
        return "pronoun"
    if first in lex.ARTICLES:
        return "article"
    if first in lex.PREPOSITIONS:
        return "preposition"
    if first.endswith("ing") and first not in _ING_STOP and "," in stripped[:60]:
        return "participial"
    if first.endswith("ly") and len(first) > 3:
        return "adverb"
    return "other"


def _syntax(s: Sample, out: dict[str, float]) -> None:
    sentences = [x.text for x in s.sentences]
    n = len(sentences)
    subordination = 0
    subordinate_sentences = 0
    relative_sentences = 0
    conditional_sentences = 0
    prepositions = 0
    coordination = 0

    for sentence in sentences:
        toks = tokens(sentence)
        marks = sum(1 for t in toks if t in _SUBORD_MARKERS)
        marks += sum(1 for t in toks if t in _RELATIVE_MARKERS)
        subordination += marks
        if marks:
            subordinate_sentences += 1
        if any(t in _RELATIVE_MARKERS for t in toks):
            relative_sentences += 1
        if any(t in {"if", "unless"} for t in toks):
            conditional_sentences += 1
        prepositions += sum(1 for t in toks if t in lex.PREPOSITIONS)
        coordination += len(_COMMA_COORD_RE.findall(sentence))

    out["subordination_per_sentence"] = subordination / n if n else 0.0
    out["subordinate_sentence_pct"] = _pct(subordinate_sentences, n)
    out["relative_clause_sentence_pct"] = _pct(relative_sentences, n)
    out["conditional_sentence_pct"] = _pct(conditional_sentences, n)
    out["coordination_per_sentence"] = coordination / n if n else 0.0
    out["preposition_per_sentence"] = prepositions / n if n else 0.0
    out["appositive_per_1k"] = _rate(len(_APPOSITIVE_RE.findall(s.text)), s.words)

    categories = [_classify_opening(x, s.names) for x in sentences]
    counter = Counter(categories)
    for category in ("name", "pronoun", "article", "preposition", "subordinate",
                     "participial", "dialogue", "conjunction", "adverb", "other"):
        out[f"open_{category}_pct"] = _pct(counter[category], n)

    openings = Counter()
    for sentence in sentences:
        toks = tokens(sentence)[:2]
        if len(toks) == 2:
            openings[" ".join(toks)] += 1
    repeated = sum(c for c in openings.values() if c > 1)
    out["open_repeat_pct"] = _pct(repeated, n)

    name_action = 0
    for sentence, category in zip(sentences, categories):
        if category != "name":
            continue
        toks = tokens(sentence)
        if len(toks) < 2:
            continue
        second = toks[1]
        if second in lex.IRREGULAR_PAST or second in lex.MOTION_VERBS or (
            second.endswith("ed") and len(second) > 3
        ):
            name_action += 1
    out["open_name_action_pct"] = _pct(name_action, n)


def _lexis(s: Sample, out: dict[str, float]) -> None:
    toks = s.all_tokens
    total = len(toks)
    out["mattr_50"] = mattr(toks, 50)
    out["mattr_500"] = mattr(toks, 500)
    out["mtld"] = mtld(toks)
    counts = Counter(toks)
    out["hapax_pct"] = _pct(sum(1 for c in counts.values() if c == 1), len(counts) or 1)
    content = [t for t in toks if t not in lex.FUNCTION_WORDS]
    out["lexical_density"] = (len(content) / total) if total else 0.0
    out["mean_word_length"] = _safe_mean(len(t) for t in toks)
    out["long_word_pct"] = _pct(sum(1 for t in toks if len(t) >= 8), total)

    grams = Counter(tuple(toks[i:i + 4]) for i in range(max(0, total - 3)))
    repeated = sum(c for c in grams.values() if c > 1)
    out["repeat_4gram_per_1k"] = _rate(repeated, total)

    repeats = 0
    last_seen: dict[str, int] = {}
    for i, token in enumerate(toks):
        if token in lex.FUNCTION_WORDS:
            continue
        previous = last_seen.get(token)
        if previous is not None and i - previous <= 100:
            repeats += 1
        last_seen[token] = i
    out["repeat_content_100w_per_1k"] = _rate(repeats, total)


def _senses(s: Sample, out: dict[str, float]) -> None:
    counts = Counter(s.all_tokens)
    total = s.words
    sensory_total = 0
    for modality, words in lex.SENSORY.items():
        hits = sum(counts[w] for w in words)
        sensory_total += hits
        out[f"sense_{modality}_per_1k"] = _rate(hits, total)
    out["sensory_per_1k"] = _rate(sensory_total, total)
    out["emotion_label_per_1k"] = _rate(sum(counts[w] for w in lex.EMOTION_LABELS), total)
    abstract = sum(
        c for w, c in counts.items()
        if len(w) > 5 and w.endswith(lex.ABSTRACT_SUFFIXES)
    )
    out["abstract_noun_per_1k"] = _rate(abstract, total)
    out["spatial_per_1k"] = _rate(sum(counts[w] for w in lex.SPATIAL_TERMS), total)
    out["concrete_abstract_ratio"] = (sensory_total / abstract) if abstract else 0.0


def _crutches(s: Sample, out: dict[str, float]) -> None:
    text = s.text
    filters = sum(len(r.findall(text)) for r in _FILTER_RES)
    crutches = sum(len(r.findall(text)) for r in _CRUTCH_RES)
    out["filter_phrase_per_1k"] = _rate(filters, s.words)
    out["crutch_phrase_per_1k"] = _rate(crutches, s.words)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def measure(paras: Sequence[Paragraph], names: frozenset[str] = frozenset()) -> dict[str, float]:
    """Measure a passage. Returns every key in :data:`REGISTRY`."""
    sample = build_sample(paras, names)
    out: dict[str, float] = {}
    if not sample.sentences:
        return {key: 0.0 for key in REGISTRY}
    _sentence_rhythm(sample, out)
    _paragraph_rhythm(sample, out)
    _dialogue(sample, out)
    _punctuation(sample, out)
    _function_words(sample, out)
    _pov(sample, out)
    _verbs(sample, out)
    _syntax(sample, out)
    _lexis(sample, out)
    _senses(sample, out)
    _crutches(sample, out)
    for key in REGISTRY:
        out.setdefault(key, 0.0)
    return out


def tag_counter(paras: Sequence[Paragraph]) -> Counter:
    """Which verbs this passage actually uses to attribute speech."""
    counts: Counter = Counter()
    for para in paras:
        for span in dialogue_spans(para.text):
            tag, _, _ = _tag_info(para.text, span)
            if tag:
                counts[tag] += 1
    return counts


def function_word_rates(paras: Sequence[Paragraph], words: Sequence[str]) -> dict[str, float]:
    """Per-1,000 rates for a specific word list (used by the report)."""
    toks: list[str] = []
    for para in paras:
        toks.extend(tokens(para.text))
    counts = Counter(toks)
    total = len(toks)
    return {w: _rate(counts[w], total) for w in words}
