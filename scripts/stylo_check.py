#!/usr/bin/env python3
"""Audit a draft against a public-domain author's measured style lane.

    python3 scripts/stylo_check.py draft.md --author edith-wharton
    python3 scripts/stylo_check.py draft.md --author agatha-christie --scene conversation
    python3 scripts/stylo_check.py draft.md --author e-nesbit --json

Reads the draft locally and prints only what drifted, plus a rewrite brief.
Nothing is sent anywhere; no corpus text is loaded into the output. The point
is that a model never has to reread the manuscript or the reference books.

Exit status is 0 when the draft is inside the lane on every primary
measurement and 1 when something drifted, so this can gate a build.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stylo.audit import audit, render
from stylo.corpus import AUTHORS, ROOT
from stylo.features import FAMILIES, PRIMARY_METRICS, REGISTRY
from stylo.profile import AuthorProfile
from stylo.segment import make_document

REFERENCE = ROOT / "stylometry" / "reference" / "delta-model.json"


def profile_path(slug: str) -> Path:
    return ROOT / "authors" / slug / "profile" / "profile.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("draft", help="Markdown or plain-text file to check ('-' for stdin)")
    parser.add_argument(
        "--author", choices=sorted(AUTHORS),
        help="target profile slug to audit against. Required, unless the "
             "STYLO_DEFAULT_TARGET environment variable names one.",
    )
    parser.add_argument(
        "--scene", default="any",
        choices=["any", "conversation", "reflection"],
        help="swap the dialogue lane for a scene type. A confrontation is "
             "allowed to be talk-heavy and a reflective passage is not; "
             "default 'any' uses the author's overall lane.",
    )
    parser.add_argument(
        "--families", default="",
        help="comma-separated families to check instead of the primary set. "
             f"Available: {', '.join(FAMILIES)}",
    )
    parser.add_argument("--all", action="store_true",
                        help="check every measurement, not just the primary set")
    parser.add_argument("--pov", default="", choices=["", "first", "third"],
                        help="intended narration person; enables slip detection")
    parser.add_argument("--tense", default="", choices=["", "past", "present"],
                        help="intended narration tense; enables slip detection")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--output-dir", type=Path, help="write HTML and AI reports into a NEW folder")
    args = parser.parse_args()

    # Resolve the target. A draft is always measured against exactly one
    # profile; there is no library-wide default in the standalone kit, so the
    # caller must name one (via --author or STYLO_DEFAULT_TARGET).
    if not args.author:
        args.author = os.environ.get("STYLO_DEFAULT_TARGET", "")
    if not args.author:
        parser.error(
            "No target profile. Pass --author <slug>, or set STYLO_DEFAULT_TARGET. "
            f"Available: {', '.join(sorted(AUTHORS)) or '(none yet — run build first)'}"
        )
    if args.author not in AUTHORS:
        parser.error(f"No profile '{args.author}'. Available: {', '.join(sorted(AUTHORS))}")

    path = profile_path(args.author)
    if not path.exists():
        parser.error(
            f"No profile for {args.author}. Run: "
            f"python3 scripts/build_author_profiles.py"
        )
    if not REFERENCE.exists():
        parser.error(
            "Missing stylometry/reference/delta-model.json. Run: "
            "python3 scripts/build_author_profiles.py"
        )

    if args.draft == "-":
        text = sys.stdin.read()
        title = "stdin"
    else:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            parser.error(f"No such file: {draft_path}")
        text = draft_path.read_text(encoding="utf-8")
        title = draft_path.name

    document = make_document(text, title=title)
    if not document.paragraphs:
        parser.error("The draft has no prose paragraphs in it.")

    profile = AuthorProfile.load(path)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))

    if args.families:
        wanted = {f.strip() for f in args.families.split(",")}
        unknown = wanted - set(FAMILIES)
        if unknown:
            parser.error(
                f"Unknown families: {', '.join(sorted(unknown))}. "
                f"Available: {', '.join(FAMILIES)}"
            )
        keys = [k for k, m in REGISTRY.items() if m.family in wanted]
    elif args.all:
        keys = list(REGISTRY)
    else:
        keys = list(PRIMARY_METRICS)

    result = audit(
        document, profile, reference,
        keys=keys, scene=args.scene, pov=args.pov, tense=args.tense,
    )

    if args.output_dir:
        from stylo.html_report import audit_page
        try:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            (args.output_dir / "report.html").write_text(audit_page(result, profile), encoding="utf-8")
            (args.output_dir / "report.md").write_text("# Profile comparison — AI evidence\n\n" + render(result, profile), encoding="utf-8")
            (args.output_dir / "measurements.json").write_text(json.dumps(result.as_dict(), indent=2), encoding="utf-8")
        except OSError as error:
            parser.exit(2, f"Could not save the reading report: {error}. Use a new output folder. Source prose was not changed.\n")
        if not args.json:
            print(f"Your reading page: {(args.output_dir / 'report.html').resolve()}")
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(render(result, profile))

    return 1 if result.drifts else 0


if __name__ == "__main__":
    raise SystemExit(main())
