# Setup for the AI
Read machine/START.md. Explain only the next necessary step to the human.

## First check
Find an available Python 3 interpreter using the tool's documented runtime or the system. For a new installation choose a currently supported Python 3 release. Check its actual version; a Windows Store alias may not be a working interpreter. Never say “nothing to install” unless a usable runtime is already available.

If no interpreter is available, show guide/demo.html. Offer the official Python downloads page linked in guide/setup.html, explain the single necessary installation, and ask before installing system software. If no code execution is available, do not estimate numbers and call them measured.

## Exact first run
From the kit root, use the actual interpreter path with:
python scripts/stylo_explore.py --demo --output <NEW-session-report-folder>

Replace python with the resolved executable. Quote filesystem arguments, especially Windows paths with spaces. The output folder must not exist. The script uses included examples and writes report.html, report.md, voice-notes.html, voice-notes.md and measurements.json. Open report.html for the human. Do not overwrite old results.

## Own samples
python scripts/stylo_explore.py <sample-copy.md> --output <NEW-report-folder>
python scripts/stylo_explore.py <sample-A.md> <sample-B.md> --output <NEW-report-folder>

Inputs must be UTF-8 plain text or Markdown. If given DOCX/PDF, create a prose-only text copy with available document tools, preserving original paragraphs and dialogue; do not rename the file extension. Keep originals. Remove headings/front matter only from working copies and show exclusions.

## Return codes
Exploration: 0 means results saved, 2 means setup/input/output needs attention. The basic mode never uses “drift” as a failure.
Advanced stylo_check.py: 0 means no selected drift, 1 means differences were found, 2 means an operational problem. Code 1 is NOT a crashed run or a bad author.

## Recovery
- Missing file: name the exact missing input and ask for its location; do not request the whole library.
- Empty/non-prose input: ask for a short passage of ordinary prose.
- Existing output folder: choose a new folder. Do not delete the old one to retry.
- Unsupported format or decoding: make an authorized plain-text copy; explain what was excluded.
- Missing author profile: this affects only optional full profiling, not exploration. See machine/modules/profiles.md.
