# Remote URLs

Every public address of the project. `scripts/check_urls.py` checks these and every other link in the repo that
points at them (164 URLs at the last regeneration); `.github/workflows/links.yml` runs it after each Pages
deploy, every Monday, and on demand, and fails if any URL stops returning 200.

| What | URL |
|---|---|
| Site: visualisation gallery | <https://physicalaibenchmarks.github.io/Text2WetLab/> |
| Site: leaderboard (generated from results/runs/) | <https://physicalaibenchmarks.github.io/Text2WetLab/leaderboard.html> |
| Site: preprint (built from manuscript/) | <https://physicalaibenchmarks.github.io/Text2WetLab/docs/preprint/preprint.html> |
| Site: PLR machine coverage | <https://physicalaibenchmarks.github.io/Text2WetLab/plr_coverage_table.html> |
| Site: PLR paper-code pairs | <https://physicalaibenchmarks.github.io/Text2WetLab/plr_embodiment_pairs.html> |
| Site: demo | <https://physicalaibenchmarks.github.io/Text2WetLab/docs/demo.html> |
| Site: old leaderboard address (redirects) | <https://physicalaibenchmarks.github.io/Text2WetLab/docs/leaderboard.html> |
| Repository | <https://github.com/PhysicalAIBenchmarks/Text2WetLab> |
| Latest results report | <https://github.com/PhysicalAIBenchmarks/Text2WetLab/blob/main/results/runs/2026-10-07-openrouter/REPORT.md> |
| Hugging Face dataset | <https://huggingface.co/datasets/EvanOLeary/Text2WetLab> |

The site is built by `scripts/build_site.py` and deployed by `.github/workflows/pages.yml` on every change to `main`
that touches a page, `docs/`, `assets/`, `results/runs/` or `manuscript/`. The dataset is uploaded by the `deploy-hf`
job in `.github/workflows/ci.yml`.
