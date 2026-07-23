"""Recognition measures: Burrows's Delta and character n-gram similarity.

Per section 2 of the guide these belong in a *validator*, not in a writing
prompt. They answer "is this passage in the same statistical neighbourhood?"
and nothing more. When they fire, the interpretable metrics explain why.

Pure standard library: the vectors here are dicts and lists, not arrays. At
this corpus size (~2,600 chunks x 150 words) that is fast enough.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

_NON_WORD = re.compile(r"[^a-z ]+")


# ---------------------------------------------------------------------------
# Burrows's Delta
# ---------------------------------------------------------------------------


def most_frequent_words(token_lists: Sequence[Sequence[str]], top: int = 150) -> list[str]:
    """The corpus's most frequent words, which become the Delta feature set."""
    counts: Counter[str] = Counter()
    for toks in token_lists:
        counts.update(toks)
    return [word for word, _ in counts.most_common(top)]


def frequency_vector(toks: Sequence[str], mfw: Sequence[str]) -> list[float]:
    """Relative frequency (per 1,000 words) of each most-frequent word."""
    counts = Counter(toks)
    total = len(toks) or 1
    return [counts[w] * 1000.0 / total for w in mfw]


@dataclass()
class Standardiser:
    """Corpus-wide mean and standard deviation for each MFW frequency."""

    mfw: list[str]
    means: list[float]
    sds: list[float]

    @classmethod
    def fit(cls, vectors: Sequence[Sequence[float]], mfw: Sequence[str]) -> "Standardiser":
        n = len(vectors)
        width = len(mfw)
        means = [0.0] * width
        sds = [0.0] * width
        if n == 0:
            return cls(list(mfw), means, [1.0] * width)
        for i in range(width):
            column = [v[i] for v in vectors]
            m = sum(column) / n
            var = sum((x - m) ** 2 for x in column) / n
            means[i] = m
            sds[i] = math.sqrt(var) or 1.0
        return cls(list(mfw), means, sds)

    def z(self, vector: Sequence[float]) -> list[float]:
        return [(v - m) / sd for v, m, sd in zip(vector, self.means, self.sds)]

    def z_from_tokens(self, toks: Sequence[str]) -> list[float]:
        return self.z(frequency_vector(toks, self.mfw))

    def to_dict(self) -> dict:
        return {"mfw": self.mfw, "means": self.means, "sds": self.sds}

    @classmethod
    def from_dict(cls, data: dict) -> "Standardiser":
        return cls(list(data["mfw"]), list(data["means"]), list(data["sds"]))


def centroid(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        return []
    width = len(vectors[0])
    n = len(vectors)
    return [sum(v[i] for v in vectors) / n for i in range(width)]


def delta_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Burrows's Delta: the mean absolute difference of z-scores."""
    if not a or not b:
        return float("inf")
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def leave_one_out_distances(vectors: Sequence[Sequence[float]]) -> list[float]:
    """Each vector's Delta to the centroid of the *others*.

    This is what makes a threshold honest: it shows how far the author's own
    passages sit from the author's own centre, so a draft's distance has
    something real to be compared against.
    """
    n = len(vectors)
    if n < 2:
        return []
    width = len(vectors[0])
    totals = [sum(v[i] for v in vectors) for i in range(width)]
    out: list[float] = []
    for vector in vectors:
        others = [(totals[i] - vector[i]) / (n - 1) for i in range(width)]
        out.append(delta_distance(vector, others))
    return out


# ---------------------------------------------------------------------------
# Character n-grams
# ---------------------------------------------------------------------------


def char_ngrams(text: str, n: int = 4) -> Counter[str]:
    """Lowercased character n-grams over letters and spaces."""
    flat = _NON_WORD.sub(" ", text.lower())
    flat = re.sub(r" +", " ", flat)
    return Counter(flat[i:i + n] for i in range(max(0, len(flat) - n + 1)))


def top_ngrams(counters: Sequence[Counter[str]], top: int = 1000) -> list[str]:
    total: Counter[str] = Counter()
    for counter in counters:
        total.update(counter)
    return [gram for gram, _ in total.most_common(top)]


def ngram_vector(counter: Counter[str], keys: Sequence[str]) -> list[float]:
    total = sum(counter.values()) or 1
    return [counter[k] / total for k in keys]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)
