#!/bin/bash
# Render manuscript/main.md + refs.bib to one self-contained HTML preprint (figures embedded, citations resolved) and to
# LaTeX for journal or arXiv submission. main.md is the only source; never edit the outputs by hand.
#   bash manuscript/build.sh            -> docs/preprint/preprint.html, manuscript/main.tex, manuscript/.source.sha256
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
pypandoc.convert_file(
    "main.md", "latex", outputfile="main.tex",
    extra_args=["--standalone", "--natbib", "--resource-path=.", "--metadata", "link-citations=true"])
import hashlib, pathlib
tex = pathlib.Path("main.tex")
tex.write_text(tex.read_text().replace("\\bibliography{refs.bib}", "\\bibliography{refs}"))  # BibTeX adds .bib itself
digest = hashlib.sha256(b"".join(pathlib.Path(f).read_bytes() for f in ("main.md", "refs.bib", "preprint.css"))).hexdigest()
pathlib.Path(".source.sha256").write_text(digest + "\n")
PY
echo "wrote docs/preprint/preprint.html and manuscript/main.tex"
if [ "${1:-}" = "--pdf" ]; then
  CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || echo "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")}"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --run-all-compositor-stages-before-draw \
    --virtual-time-budget=10000 --print-to-pdf="$PWD/text2wetlab-preprint.pdf" "file://$PWD/../docs/preprint/preprint.html" 2>/dev/null
  echo "wrote manuscript/text2wetlab-preprint.pdf"
fi
