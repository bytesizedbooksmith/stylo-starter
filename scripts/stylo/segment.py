"""Text loading and segmentation.

Turns a Markdown work into paragraphs, sentences, dialogue spans and tokens.
No third-party dependencies. The sentence splitter is fiction-aware: it knows
about honorifics, initials, ellipses and speech punctuation, which a naive
split-on-period would mangle in every one of these books.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Sequence

from .lexicons import ABBREVIATIONS, COMMON_SENTENCE_STARTERS

# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

# A word is letters, optionally with internal apostrophes/hyphens.
WORD_RE = re.compile(r"[A-Za-z]+(?:[’'\-][A-Za-z]+)*")

# Straight and curly double quotes both open dialogue in this corpus.
_OPEN_Q = "“"   # “
_CLOSE_Q = "”"  # ”
DIALOGUE_RE = re.compile(
    r"“[^“”]*”"   # “...”
    r"|\"[^\"]*\"",                   # "..."
    re.DOTALL,
)

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
CHAPTER_HEADING_RE = re.compile(r"^##\s+(.*)$")
ITALIC_LINE_RE = re.compile(r"^\*[^*]+\*$")

# Sentence-final punctuation, optionally followed by closing quotes/brackets.
_SENT_END_RE = re.compile(r"([.!?…]+)([\"”’')\]]*)(\s+)")


def normalise(text: str) -> str:
    """Normalise whitespace inside a paragraph without touching punctuation."""
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    """Lowercased word tokens."""
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def word_count(text: str) -> int:
    return sum(1 for _ in WORD_RE.finditer(text))


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Split ``---`` YAML-ish front matter from the body.

    Only flat ``key: value`` pairs are supported, which is all this corpus uses.
    """
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        return {}, raw
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, raw[match.end():]


# ---------------------------------------------------------------------------
# Paragraphs
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Paragraph:
    """One prose paragraph.

    ``index`` is its position among prose paragraphs in the work (0-based),
    which is what the audit tool reports as a location.
    """

    index: int
    text: str
    chapter: str = ""
    line_no: int = 0


ROMAN_OR_NUMBER_RE = re.compile(r"^(?:[IVXLCDM]+|\d+)\.?$")


def _is_structural(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if HEADING_RE.match(stripped):
        return True
    if ITALIC_LINE_RE.match(stripped):  # the "*Author; original text.*" line
        return True
    if stripped in {"---", "***", "* * *"}:
        return True
    return False


def _is_junk_paragraph(text: str) -> bool:
    """Section numerals and unmarked tale titles are not prose.

    Ethan Frome's section breaks are bare roman numerals, and the Poe volumes
    title each tale in full caps with no Markdown heading. Left in, both would
    register as one-sentence paragraphs and as verbless fragments.
    """
    if ROMAN_OR_NUMBER_RE.match(text):
        return True
    if not any(c.islower() for c in text) and word_count(text) <= 10 and text[-1:] not in "?!":
        return True
    return False


def paragraphs(
    body: str,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    drop_headings: bool = True,
) -> list[Paragraph]:
    """Split a work body into prose paragraphs.

    Blank lines separate paragraphs. Hard-wrapped lines inside a block are
    joined, which matters for the Poe and later Nesbit files - those keep the
    source line breaks so verse is not flattened.

    ``start_line``/``end_line`` are 1-based line numbers into the *original
    file* (front matter included) and let a caller trim editorial front matter
    such as the biography sitting in front of Poe's tales.
    """
    out: list[Paragraph] = []
    buffer: list[str] = []
    buffer_line = 0
    chapter = ""
    idx = 0

    def flush() -> None:
        nonlocal buffer, buffer_line, idx
        if not buffer:
            return
        text = normalise(" ".join(buffer))
        buffer = []
        if not text:
            return
        # Ignore fragments with no letters at all (rules, page numbers).
        if not WORD_RE.search(text):
            return
        if _is_junk_paragraph(text):
            return
        out.append(Paragraph(index=idx, text=text, chapter=chapter, line_no=buffer_line))
        idx += 1

    for lineno, line in enumerate(body.splitlines(), start=1):
        if start_line is not None and lineno < start_line:
            continue
        if end_line is not None and lineno >= end_line:
            break

        stripped = line.strip()
        heading = CHAPTER_HEADING_RE.match(stripped)
        if heading:
            flush()
            chapter = heading.group(1).strip()
            continue
        if _is_structural(line):
            flush()
            continue
        if not buffer:
            buffer_line = lineno
        buffer.append(stripped)

    flush()
    if drop_headings:
        pass
    return out


# ---------------------------------------------------------------------------
# Sentences
# ---------------------------------------------------------------------------


def _looks_like_abbreviation(text: str, dot_pos: int) -> bool:
    """True if the period at ``dot_pos`` closes an abbreviation, not a sentence."""
    # Walk back over the word preceding the period.
    start = dot_pos
    while start > 0 and (text[start - 1].isalpha() or text[start - 1] == "."):
        start -= 1
    word = text[start:dot_pos].strip(".").lower()
    if not word:
        return False
    if word in ABBREVIATIONS:
        return True
    # Single initials: "J. R. Smith"
    if len(word) == 1 and word.isalpha():
        return True
    return False


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of each sentence in ``text``.

    Deliberately conservative: a break requires terminal punctuation followed
    by whitespace and then something that can plausibly open a sentence
    (capital letter, opening quote, digit, or dash).

    Offsets are returned rather than strings because callers need to know
    whether a sentence falls inside quoted speech, and that can only be
    decided positionally - a long speech splits into sentences that each
    carry an unbalanced quote mark.
    """
    if not text.strip():
        return []

    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENT_END_RE.finditer(text):
        end = match.end(2)
        punct = match.group(1)
        closers = match.group(2)
        after = text[match.end():]
        if not after:
            break

        # "Mr." / initials do not end a sentence.
        if punct == "." and not closers and _looks_like_abbreviation(text, match.start(1)):
            continue

        nxt = after[0]
        # A lowercase continuation means the mark was internal: “...,” he said.
        if not (nxt.isupper() or nxt.isdigit() or nxt in "“‘\"'—-([…"):
            continue

        # An ellipsis followed by a capital is usually still one sentence when
        # it trails inside speech; require a closing quote or a real stop.
        if punct == "…" and not closers:
            continue

        if text[start:end].strip():
            spans.append((start, end))
        start = match.end()

    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def split_sentences(text: str) -> list[str]:
    """Split a paragraph into sentences."""
    return [text[a:b].strip() for a, b in sentence_spans(text) if text[a:b].strip()]


# ---------------------------------------------------------------------------
# Dialogue / narration split
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Utterance:
    """One quoted speech span."""

    text: str          # including the quote marks
    inner: str         # without the quote marks
    para_index: int
    start: int
    end: int

    @property
    def words(self) -> int:
        return word_count(self.inner)


def dialogue_spans(text: str) -> list[tuple[int, int]]:
    """Character spans of quoted speech within ``text``."""
    return [(m.start(), m.end()) for m in DIALOGUE_RE.finditer(text)]


def split_dialogue_narration(text: str) -> tuple[str, str]:
    """Return ``(dialogue_text, narration_text)`` for one paragraph.

    Dialogue keeps its quote marks stripped; narration is everything outside
    the quotes, joined with spaces.
    """
    spans = dialogue_spans(text)
    if not spans:
        return "", text
    dialogue_parts: list[str] = []
    narration_parts: list[str] = []
    cursor = 0
    for start, end in spans:
        narration_parts.append(text[cursor:start])
        dialogue_parts.append(text[start + 1:end - 1])
        cursor = end
    narration_parts.append(text[cursor:])
    return (
        " ".join(p.strip() for p in dialogue_parts if p.strip()),
        " ".join(p.strip() for p in narration_parts if p.strip()),
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Document:
    """A parsed work or draft, ready for measurement."""

    title: str
    paragraphs: list[Paragraph]
    meta: dict[str, str] = field(default_factory=dict)
    path: str = ""

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)

    @property
    def word_count(self) -> int:
        return sum(word_count(p.text) for p in self.paragraphs)

    def sentences(self) -> Iterator[tuple[int, str]]:
        for para in self.paragraphs:
            for sentence in split_sentences(para.text):
                yield para.index, sentence

    def utterances(self) -> list[Utterance]:
        out: list[Utterance] = []
        for para in self.paragraphs:
            for start, end in dialogue_spans(para.text):
                span = para.text[start:end]
                out.append(
                    Utterance(
                        text=span,
                        inner=span[1:-1],
                        para_index=para.index,
                        start=start,
                        end=end,
                    )
                )
        return out

    def proper_names(self, min_count: int = 3) -> frozenset[str]:
        """Capitalised words that behave like names in this document.

        A token counts only when it appears capitalised somewhere other than
        the first position of a sentence, which is the only way to tell
        "Elizabeth" from "Every" without a tagger.
        """
        counts: dict[str, int] = {}
        for _, sentence in self.sentences():
            words = list(WORD_RE.finditer(sentence))
            for position, match in enumerate(words):
                word = match.group(0)
                if position == 0:
                    continue
                if not word[0].isupper():
                    continue
                lower = word.lower()
                if lower in COMMON_SENTENCE_STARTERS or lower in ABBREVIATIONS:
                    continue
                if len(lower) < 3:
                    continue
                # Skip words that only follow an opening quote (still initial).
                preceding = sentence[: match.start()].rstrip()
                if preceding and preceding[-1] in "“‘\"":
                    continue
                counts[lower] = counts.get(lower, 0) + 1
        return frozenset(w for w, c in counts.items() if c >= min_count)


def load_document(path, *, start_line: int | None = None, end_line: int | None = None) -> Document:
    """Read a Markdown file into a :class:`Document`."""
    from pathlib import Path

    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)

    # start_line/end_line are given against the whole file; convert to body
    # coordinates by subtracting the front-matter line count.
    offset = raw[: len(raw) - len(body)].count("\n")
    body_start = start_line - offset if start_line else None
    body_end = end_line - offset if end_line else None

    paras = paragraphs(body, start_line=body_start, end_line=body_end)
    title = meta.get("title") or p.stem
    return Document(title=title, paragraphs=paras, meta=meta, path=str(p))


def make_document(text: str, title: str = "draft") -> Document:
    """Build a :class:`Document` from a raw string (used for drafts)."""
    meta, body = parse_front_matter(text)
    return Document(title=meta.get("title", title), paragraphs=paragraphs(body), meta=meta)


def chunk_paragraphs(
    paras: Sequence[Paragraph], target_words: int = 2000, min_words: int = 1000
) -> list[list[Paragraph]]:
    """Group paragraphs into paragraph-aligned chunks of ~``target_words``.

    The guide's recommended unit for stable author profiling is 1,500-3,000
    words. A trailing chunk shorter than ``min_words`` is merged backwards so
    short tails do not distort the distribution.
    """
    chunks: list[list[Paragraph]] = []
    current: list[Paragraph] = []
    count = 0
    for para in paras:
        current.append(para)
        count += word_count(para.text)
        if count >= target_words:
            chunks.append(current)
            current = []
            count = 0
    if current:
        if chunks and count < min_words:
            chunks[-1].extend(current)
        else:
            chunks.append(current)
    return chunks
