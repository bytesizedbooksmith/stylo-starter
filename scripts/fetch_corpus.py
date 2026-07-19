#!/usr/bin/env python3
"""Download the reference corpus from Project Gutenberg and convert it to the
Markdown the profiler reads.

    python3 scripts/fetch_corpus.py                 # every work in catalog.csv
    python3 scripts/fetch_corpus.py --author h-g-wells
    python3 scripts/fetch_corpus.py --force         # re-download and re-convert

For each catalogue row with a Project Gutenberg id, this fetches the plain-text
ebook, strips Gutenberg's licence header and footer, adds the front matter,
title and byline the profiler expects, and marks the chapter headings it can
recognise. The result lands at the row's ``markdown_path`` inside
``authors/<slug>/works/``; the raw download is kept under ``sources/`` so you
can see exactly what was trimmed.

The conversion is deliberately conservative and best-effort. It gets ordinary
chapter-per-heading novels right on its own. Collections, translated editions
and books with a long title page may need a hand-trim afterwards — read the
converted file, then add a line-range entry to ``WORK_FILTERS`` in
``scripts/stylo/corpus.py`` (there is a worked example in that file). Nothing
here is sent anywhere except a GET to gutenberg.org, and no manuscript of your
own is ever touched.

Standard library only. Requires a network connection for the download step.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stylo.corpus import ROOT  # single source of truth for the data root

CATALOG = ROOT / "catalog.csv"

# Gutenberg's canonical UTF-8 plain-text URL for an ebook id.
TEXT_URL = "https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt"

# A descriptive User-Agent is polite and avoids the default urllib agent being
# refused. Fetch a handful of books, not the whole library, and keep the delay.
USER_AGENT = (
    "stylo-starter/1.0 (personal stylometry corpus builder; "
    "one-time fetch, not a crawler)"
)

# Gutenberg wraps every modern ebook between these markers. THE/THIS and
# EBOOK/E-BOOK both occur across the archive's vintages.
START_RE = re.compile(
    r"^\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG E-?BOOK.*?\*\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
END_RE = re.compile(
    r"^\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG E-?BOOK.*?\*\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# A line that opens a chapter (or part/book). Bare roman numerals are left
# alone on purpose: the profiler already drops numeral-only paragraphs, and
# treating every "II" as a heading would mangle books that never use the word.
CHAPTER_RE = re.compile(
    r"^\s*(chapter|part|book)\s+([ivxlcdm]+|\d+)\b.*$",
    re.IGNORECASE,
)


def log(message: str) -> None:
    print(message, flush=True)


def download(gid: str) -> str:
    url = TEXT_URL.format(gid=gid)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    # The cache/epub text is UTF-8; fall back permissively for old scans.
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def strip_wrapper(text: str) -> str:
    """Return only the body between Gutenberg's START and END markers."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    start = START_RE.search(text)
    body = text[start.end():] if start else text
    end = END_RE.search(body)
    if end:
        body = body[: end.start()]
    return body.strip("\n")


def mark_chapters(body: str) -> str:
    """Turn recognisable chapter headings into ``## `` and drop the title page.

    If any chapter heading is found, everything before the first one (a title
    page, a dedication, a table of contents) is dropped, because measurement
    should begin at the first line of prose — exactly the trim a collected
    edition needs. If none is found, the body is returned unchanged and the
    profiler's own junk-paragraph filter handles stray title lines.
    """
    lines = body.split("\n")
    marked: list[str] = []
    first_heading: int | None = None
    for line in lines:
        if CHAPTER_RE.match(line.strip()):
            if first_heading is None:
                first_heading = len(marked)
            marked.append(f"## {line.strip()}")
        else:
            marked.append(line)
    if first_heading is not None:
        marked = marked[first_heading:]

    # Drop a *run* of headings separated only by blank lines — a table of
    # contents. A real chapter heading is isolated: it has prose before and
    # after it, so both its heading neighbours being headings marks it as part
    # of a contents list, not a chapter. (Bare-numeral body headings — "I.",
    # "II." — are not matched at all, so a book that heads its chapters that way
    # simply ends up with no chapter labels, which is honest.)
    out: list[str] = []
    for i, line in enumerate(marked):
        if line.startswith("## "):
            j = i + 1
            while j < len(marked) and not marked[j].strip():
                j += 1
            next_is_heading = j < len(marked) and marked[j].startswith("## ")
            k = i - 1
            while k >= 0 and not marked[k].strip():
                k -= 1
            prev_is_heading = k >= 0 and marked[k].startswith("## ")
            if next_is_heading or prev_is_heading:
                continue
        out.append(line)
    return "\n".join(out).strip("\n")


def front_matter(row: dict[str, str]) -> str:
    fields = [
        ("series", row.get("series", "")),
        ("series_number", row.get("series_number", "")),
        ("title", row["title"]),
        ("credited_author", row["author"]),
        ("genre", row.get("genre", "")),
        ("original_publication_year", row.get("original_publication_year", "")),
        ("edition", "original text"),
        ("public_domain_basis", "U.S. publication-year term; original text only"),
        ("project_gutenberg_id", row.get("project_gutenberg_id", "")),
        ("source_url", row.get("source_url", "")),
        ("processing", "Project Gutenberg wrapper removed; converted by fetch_corpus.py"),
        ("chapter_count", row.get("chapter_count", "")),
    ]
    body = "\n".join(f"{k}: {v}" for k, v in fields if v != "")
    return f"---\n{body}\n---\n"


def to_markdown(raw: str, row: dict[str, str]) -> str:
    body = mark_chapters(strip_wrapper(raw))
    year = row.get("original_publication_year", "")
    byline = f"*{row['author']}; original {year} text.*" if year else f"*{row['author']}.*"
    return "\n\n".join([
        front_matter(row).rstrip("\n"),
        f"# {row['title']}",
        byline,
        body,
    ]) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--author", help="fetch one author only (folder slug)")
    parser.add_argument("--force", action="store_true",
                        help="re-download and re-convert works already present")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="seconds to wait between downloads (default 2)")
    parser.add_argument("--keep-raw", action="store_true", default=True,
                        help="keep the raw .txt under sources/ (default on)")
    args = parser.parse_args()

    if not CATALOG.exists():
        parser.error(f"No catalog at {CATALOG}")

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    fetched = skipped = failed = 0
    for row in rows:
        slug = row["author_folder"].split("/")[-1]
        if args.author and slug != args.author:
            continue

        gid = (row.get("project_gutenberg_id") or "").strip()
        md_path = ROOT / row["markdown_path"]
        if not gid:
            log(f"  skip   {row['title'][:50]:52} (no Gutenberg id — your own work)")
            skipped += 1
            continue
        if md_path.exists() and not args.force:
            log(f"  have   {row['title'][:50]:52} {row['markdown_path']}")
            skipped += 1
            continue

        try:
            log(f"  get    {row['title'][:50]:52} pg{gid}")
            raw = download(gid)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            log(f"  FAIL   {row['title'][:50]:52} {exc}")
            failed += 1
            continue

        if args.keep_raw and row.get("raw_source_path"):
            raw_path = ROOT / row["raw_source_path"]
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(raw, encoding="utf-8")

        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(raw, row), encoding="utf-8")
        fetched += 1
        time.sleep(max(0.0, args.delay))

    log(f"\nDone. {fetched} fetched, {skipped} skipped, {failed} failed.")
    if fetched:
        log("Next: python3 scripts/build_stylo_profiles.py")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
