# Eval results

Claude Code agent (Harbor, `-a claude-code`) in Modal sandboxes (`-e modal`), 1 attempt per task per model (pass@1), run 2026-10-04. Every task is graded by the simulator gate, deterministic checks and a `claude-sonnet-5-5` judge scoring 5 pass/fail rubric items (20% each), with a 0.3 cap on critical failures.

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 1.0 | 1.0 |
| split-200ul-two-wells | 1.0 | 1.0 | 1.0 |
| ampure-bead-cleanup | 1.0 | 1.0 | 1.0 |
| colony-pcr-screening | 1.0 | 1.0 | 1.0 |
| ecoli-heat-shock-transformation | 0.8 | 1.0 | 0.8 |
| golden-gate-assembly | 1.0 | 1.0 | 1.0 |
| opentrons-rna-extraction | 0.8 | 0.4 | 1.0 |
| **Mean** | **0.943** | **0.914** | **0.971** |
| Agent cost (USD) | 1.28 | 0.39 | 3.05 |

No trial errored, and no trial failed a deterministic or critical check. Every point lost came from a failed judge item.

Per-trial details (reward, deterministic reward, judge mean, rubric scores, tokens, cost, duration) are in `summary.json`. Each `results/<model>/<task>/` folder holds the graded `protocol.py`, `reward.json` and `judge.json`.
