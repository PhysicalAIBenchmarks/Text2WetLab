# Preprint

The Text2WetLab paper. `main.md` is the source (pandoc Markdown with `[@key]` citations), `refs.bib` the references,
`preprint.css` the typesetting.

| File | What it is |
|---|---|
| `main.md` | Abstract, introduction, related work (Table 1 compares the closest benchmarks), benchmark, verifier, verifier validation, setup, results, discussion |
| `refs.bib` | 25 references. arXiv entries come from the arXiv API and published papers from Crossref, so titles, authors and years are as the publisher records them |
| `build.sh` | Renders [`docs/preprint/preprint.html`](../docs/preprint/preprint.html): one self-contained file, figures embedded, citations resolved |

```bash
bash manuscript/build.sh
```

The figures are the README's (`docs/figures/`, `docs/preprint/figures/`, drawn by `docs/preprint/make_run_figures.py`),
and every number comes from `results/runs/2026-10-07-openrouter/`. When a run is added or regraded, regenerate the figures
and the report, update the numbers in `main.md`, and rebuild. The repo does not track PDFs; attach one to a GitHub
release.
