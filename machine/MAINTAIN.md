# Maintain Stylo
Human HTML sources are in docs-src/. Shared AI instructions are in machine/. Python measurement code lives in scripts/. JSON and CSV support calculations but are not human operating guides.

Run build-docs.py with an available Python 3 interpreter to rebuild the offline guide and the included measured demo. The Book Machine design has been copied into this kit; the build does not depend on an external Book Machine folder.

After changing measurement code, run scripts/test_stylo.py and scripts/test_explore.py. Validate fresh reports, invalid inputs, HTML escaping and source preservation. Check generated full-profile and audit HTML when changing their output hooks. Preserve the MIT license and FFA acknowledgment. Keep optional reference downloads out of the starter ZIP; include the original demonstration passages.

Do not call a platform live-tested unless its actual workflow ran there. Keep any limitations visible in the human guide.
