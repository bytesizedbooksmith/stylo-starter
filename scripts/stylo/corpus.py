"""Corpus definition: which text actually enters an author's profile.

Section 9 of the guide is the reason this module exists. The collection is not
nine clean single-author fiction corpora:

* Poe's folder mixes tales, poetry, criticism and metaphysics, and the two
  Raven-edition volumes open with someone else's biography of him.
* "Franklin W. Dixon" and "Carolyn Keene" are syndicate bylines.
* The authors span 1895-1930 and several genres.

So the corpus is filtered before it is measured, and every exclusion is
recorded in the report rather than being silently applied.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .segment import Document, Paragraph, chunk_paragraphs, load_document

ROOT = (Path(os.environ["STYLO_DATA_ROOT"]).resolve()
        if os.environ.get("STYLO_DATA_ROOT")
        else Path(__file__).resolve().parents[2])
CATALOG = ROOT / "catalog.csv"


@dataclass(frozen=True)
class WorkFilter:
    """Line-range trim applied to one source file."""

    start_line: int | None = None
    end_line: int | None = None
    reason: str = ""


#: Works excluded from an author's *fiction* profile, with the reason shown
#: in the report. They stay in the corpus folder; they just do not vote.
EXCLUDED_WORKS: dict[str, str] = {
    "authors/edgar-allan-poe/works/03-the-complete-poetical-works-of-edgar-allan-poe.md":
        "Verse. Line-broken poetry has no meaningful sentence or paragraph rhythm, "
        "and mixing it into prose measurements corrupts every rhythm feature.",
    "authors/edgar-allan-poe/works/04-eureka-a-prose-poem.md":
        "Metaphysical essay, not fiction. It has almost no dialogue and a "
        "lecture register that would drag Poe's narration lane away from his tales.",
}

#: Editorial matter trimmed out of otherwise usable files, by 1-based line
#: number into the *converted .md* (front matter included). These offsets are
#: file-specific, so they are yours to fill in after you have looked at a work
#: and seen where the real prose starts and stops — a contents list, a
#: translator's preface, an appendix. Leave this empty until you need it.
#:
#: Example (uncomment and adjust the line numbers to match your own file):
#:
#: WORK_FILTERS = {
#:     "authors/some-author/works/01-a-collected-edition.md": WorkFilter(
#:         start_line=992,
#:         reason="Drops the front matter — a contents list and a biographical "
#:                "notice — none of which is the author's prose.",
#:     ),
#: }
WORK_FILTERS: dict[str, WorkFilter] = {}


@dataclass(frozen=True)
class AuthorMeta:
    slug: str
    name: str
    short: str
    genre: str
    period: str
    caution: str = ""
    single_author: bool = True


def _load_registry() -> dict[str, AuthorMeta]:
    """Author/pen metadata is DATA, not code: read it from the stylometry data
    root's registry.json so new pens are added without touching the engine."""
    reg = ROOT / "registry.json"
    if not reg.exists():
        return {}
    raw = json.loads(reg.read_text(encoding="utf-8"))
    return {
        slug: AuthorMeta(
            slug=d["slug"], name=d["name"], short=d.get("short", d["name"]),
            genre=d.get("genre", ""), period=d.get("period", ""),
            caution=d.get("caution", ""), single_author=d.get("single_author", True),
        )
        for slug, d in raw.items()
    }


AUTHORS: dict[str, AuthorMeta] = _load_registry()


@dataclass()
class Work:
    """One catalogue row plus its parsed text."""

    author_slug: str
    author: str
    title: str
    year: str
    path: Path
    rel_path: str
    work_type: str
    included: bool
    exclusion_reason: str = ""
    filter_reason: str = ""
    document: Document | None = None

    def load(self) -> Document:
        if self.document is None:
            work_filter = WORK_FILTERS.get(self.rel_path)
            self.document = load_document(
                self.path,
                start_line=work_filter.start_line if work_filter else None,
                end_line=work_filter.end_line if work_filter else None,
            )
        return self.document


@dataclass()
class Chunk:
    """A ~2,000-word paragraph-aligned analysis unit."""

    author_slug: str
    work_title: str
    index: int
    paragraphs: list[Paragraph]
    chapter: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    tokens: list[str] = field(default_factory=list)

    @property
    def words(self) -> int:
        from .segment import word_count
        return sum(word_count(p.text) for p in self.paragraphs)

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)


def load_catalog(catalog_path: Path | None = None) -> list[Work]:
    """Read ``catalog.csv`` and apply the corpus filters."""
    path = catalog_path or CATALOG
    works: list[Work] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rel = row["markdown_path"]
            slug = row["author_folder"].split("/")[-1]
            reason = EXCLUDED_WORKS.get(rel, "")
            work_filter = WORK_FILTERS.get(rel)
            works.append(
                Work(
                    author_slug=slug,
                    author=row["author"],
                    title=row["title"],
                    year=row["original_publication_year"],
                    path=ROOT / rel,
                    rel_path=rel,
                    work_type=row["work_type"],
                    included=not reason,
                    exclusion_reason=reason,
                    filter_reason=work_filter.reason if work_filter else "",
                )
            )
    return works


def author_works(slug: str, catalog: list[Work] | None = None) -> list[Work]:
    catalog = catalog or load_catalog()
    return [w for w in catalog if w.author_slug == slug]


def build_chunks(work: Work, target_words: int = 2000) -> list[Chunk]:
    """Split one work into analysis chunks."""
    document = work.load()
    groups = chunk_paragraphs(document.paragraphs, target_words=target_words)
    chunks: list[Chunk] = []
    for i, group in enumerate(groups):
        chapters = [p.chapter for p in group if p.chapter]
        chunks.append(
            Chunk(
                author_slug=work.author_slug,
                work_title=work.title,
                index=i,
                paragraphs=group,
                chapter=chapters[0] if chapters else "",
            )
        )
    return chunks
