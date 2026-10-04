# Eval results

Claude Code agent (Harbor, `-a claude-code`) in Modal sandboxes (`-e modal`), 1 attempt per task per model (pass@1), run 2026-10-04. Every task is graded by the simulator gate, deterministic checks and a `claude-sonnet-5-5` rubric judge, with a 0.3 cap on critical failures.

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 0.917 | 0.833 |
| split-200ul-two-wells | 1.0 | 1.0 | 0.917 |
| ampure-bead-cleanup | 0.944 | 0.889 | 1.0 |
| colony-pcr-screening | 1.0 | 0.875 | 0.875 |
| ecoli-heat-shock-transformation | 0.714 | 0.857 | 0.714 |
| golden-gate-assembly | 1.0 | 1.0 | 1.0 |
| opentrons-rna-extraction | 0.889 | 0.833 | 0.833 |
| **Mean** | **0.935** | **0.910** | **0.882** |
| Agent cost (USD) | 1.25 | 0.41 | 3.69 |

No trial errored, and no trial failed a deterministic or critical check. Every point lost came from the judge.

Per-trial details (reward, deterministic reward, judge mean, rubric scores, tokens, cost, duration) are in `summary.json`. Each `results/<model>/<task>/` folder holds the graded `protocol.py`, `reward.json` and `judge.json`.
