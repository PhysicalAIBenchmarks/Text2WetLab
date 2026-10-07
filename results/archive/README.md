# Archived evaluation rounds

The headline results in `results/` are round R4 (checks + 75/25 rubric judge; see `docs/harbor-results/`).
These folders keep runs that were graded differently, so they are not comparable with R4 and are not in the README
tables. They are kept as data: per-trial `protocol.py`, `result.json` and `reward.json`, as committed on their branches.

| Folder | From | Agents | Grader | Notes |
|---|---|---|---|---|
| `2026-10-04-runlog-judge-haiku/` | `devin/1791063775-opentrons-rna-extraction-only` @ `d993fcb` (M. Alshehri) | Opus 5.5, Haiku 4.5, Fable 5.1 | Sonnet 5.5 judge on the full simulator run log (no end-state checks) | the only Haiku 4.5 agent run; `HAIKU_JUDGE_EXPERIMENTS.md` (Haiku tried as judge, not adopted), `REWARD_HACKING.md`, `MODEL_RESULTS.md` |
| `2026-10-04-pr49-r7/` | `ll-hard-evals` (#49) @ `26ff7dc` (L. Legon, M. Alshehri) | Opus 5.5, Sonnet 5.5, Fable 5.1 | run-log judge (8beadb3, 9984c6a) | round R7 in `docs/harbor-results/analysis/rounds.json` |

The run-log judge itself (`judge_layer.py`/`grade.py` from 8beadb3 and 9984c6a) is in this branch's history; both branches
are merged, so `git show 8beadb3` works from main.
