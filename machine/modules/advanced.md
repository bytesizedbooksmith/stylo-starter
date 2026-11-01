# Optional: detailed comparison
Read machine/START.md and profiles.md. Use only an existing, suitable profile and its matching reference model. Run scripts/stylo_check.py <draft-copy.md> --author <slug> --output-dir <NEW-report-folder>. Set STYLO_DATA_ROOT to that profile collection when needed.

Add --families or --scene only to address a specific author question; read --help for supported options. Code 1 means differences found, not an operational failure. Show report.html. AI evidence is in report.md and measurements.json. Reference distance, nearest-author labels and statistical ranges describe the comparison setup; they are not quality scores or proof of who wrote something. Never auto-apply the rewrite brief.
