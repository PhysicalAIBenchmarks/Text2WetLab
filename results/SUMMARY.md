# Eval results

Claude Code agent (Harbor 0.23.0, local Docker), 1 attempt per task per model (pass@1), run 2026-10-04.

| Task | claude-opus-5-5 | claude-sonnet-5-5 | claude-fable-5-1 |
|---|---|---|---|
| a1-a12-100ul | 1 | 1 | 1 |
| ampure-bead-cleanup | 1 | 1 | 1 |
| colony-pcr-screening | 1 | 1 | 1 |
| ecoli-heat-shock-transformation | 1 | 1 | 1 |
| golden-gate-assembly | 1 | 1 | 1 |
| opentrons-rna-extraction | 0.889 | 0.944 | 0.944 |
| split-200ul-two-wells | 1 | 1 | 1 |
| **Mean** | **0.984** | **0.992** | **0.992** |
| Cost (USD) | 1.16 | 0.37 | 2.83 |

Per-trial details (tokens, cost, duration) are in `summary.json`; each `results/<model>/<task>/` holds the graded `protocol.py`, `reward.json` and (RNA task) `judge.json`.
