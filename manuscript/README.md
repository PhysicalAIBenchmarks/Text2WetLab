# Preprint

The Text2WetLab paper. `main.md` is the only source (pandoc Markdown with `[@key]` citations), `refs.bib` the references,
`preprint.css` the typesetting. The HTML preprint, the PDF and `main.tex` are all generated from it by `build.sh`; never
edit them by hand. The README is the one other hand-written document that reports the same results, and
`tests/test_docs_sync.py` fails when the two drift apart (task, trap, attack and corpus counts, headline scores, the
related-work coverage table, citations, and a stale build).

| File | What it is |
|---|---|
| `main.md` | Abstract, introduction, related work (Table 1: what each of 18 related works covers), benchmark, verifier, verifier validation, setup, results, discussion, appendices |
| `refs.bib` | 35 references, each checked against its arXiv, bioRxiv or publisher page |
| `build.sh` | Renders [`docs/preprint/preprint.html`](../docs/preprint/preprint.html) (one self-contained file, figures embedded, citations resolved) and `main.tex` (natbib, with `refs.bib`); `--pdf` also prints the PDF |
| `main.tex` | Generated LaTeX for submission. Compile with `refs.bib` alongside |

```bash
bash manuscript/build.sh
```

The figures are the README's (`docs/figures/`, `docs/preprint/figures/`, drawn by `docs/preprint/make_run_figures.py`),
and every number comes from `results/runs/2026-10-07-openrouter/`. When a run is added or regraded, regenerate the figures
and the report, update the numbers in `main.md`, and rebuild. The repo does not track PDFs; attach one to a GitHub
release.
