# Optional: build a fuller profile
Read machine/START.md. Only after a successful small trial, help the author choose authorized writing representative of the pen name and period they want to study. Preserve originals; separate cleaning decisions from source files.

The full engine uses registry.json and catalog.csv under its data root, plus included source files. The supplied 13-author catalog does NOT contain downloaded books or profiles. --author controls which profile is written; it still measures the full configured collection for its shared reference model.

If a reference collection is wanted, discuss its scope before downloading. Use scripts/fetch_corpus.py only for the chosen, authorized download. Consult the relevant edition/source information for rights questions; do not assume every edition or location is equivalent.

For a personal setup, create a separate data root, copy authorized prose, prepare its registry and catalog internally, and use STYLO_DATA_ROOT for that process. Do not overwrite the kit's registry or merge distinct pens without agreement. Read scripts/stylo/corpus.py for the exact catalog contract. Check that every configured author has usable included prose before building. Explain that stable ranges and cross-author comparisons need suitable data, not just one short scene.

Run scripts/build_stylo_profiles.py with the chosen data root. Use generated HTML report/card and indexes for humans. The generated Markdown card is provisional until the author reviews it; distinguish measured tendencies from preferences. Do not claim validated authorship recognition from a small or unrepresentative corpus.
