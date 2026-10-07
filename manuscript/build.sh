#!/bin/bash
# Render manuscript/main.md + refs.bib to one self-contained HTML preprint (figures embedded, citations resolved).
#   bash manuscript/build.sh            -> docs/preprint/preprint.html
# Needs uv; pandoc comes from the pypandoc_binary wheel. A PDF can be made the same way with --pdf-engine, but the
# repo does not track PDFs: attach it to a GitHub release instead.
set -euo pipefail
cd "$(dirname "$0")"
uv run -q --no-project --with pypandoc_binary python - <<'PY'
import pypandoc
pypandoc.convert_file(
    "main.md", "html5", outputfile="../docs/preprint/preprint.html",
    extra_args=["--citeproc", "--standalone", "--embed-resources", "--resource-path=.",
                "--metadata", "link-citations=true",
                "--css", "preprint.css"])
PY
echo "wrote docs/preprint/preprint.html"
