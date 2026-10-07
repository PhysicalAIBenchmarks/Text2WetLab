#!/bin/bash
# Render manuscript/main.md + refs.bib to one self-contained HTML preprint (figures embedded, citations resolved).
#   bash manuscript/build.sh            -> docs/preprint/preprint.html
#   bash manuscript/build.sh --pdf      -> also manuscript/text2wetlab-preprint.pdf (headless Chrome; set CHROME= to override)
# Needs uv; pandoc comes from the pypandoc_binary wheel. The repo does not track PDFs (it is gitignored): attach the
# PDF to a GitHub release instead.
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
if [ "${1:-}" = "--pdf" ]; then
  CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || echo "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")}"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --run-all-compositor-stages-before-draw \
    --virtual-time-budget=10000 --print-to-pdf="$PWD/text2wetlab-preprint.pdf" "file://$PWD/../docs/preprint/preprint.html" 2>/dev/null
  echo "wrote manuscript/text2wetlab-preprint.pdf"
fi
