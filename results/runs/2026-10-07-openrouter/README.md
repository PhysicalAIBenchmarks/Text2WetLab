# 2026-10-07: Sonnet 5.5, Opus 5.5 and Fable 5.1 on all 11 tasks

Harbor 0.23.0, agent `claude-code`, one attempt per task (pass@1), Docker via Colima. Agent and judge (Claude Sonnet 5.5)
both through OpenRouter (`anthropic/<model>`). Graded with the tasks at `8da544a`. One trial was regraded after the
grader fix in `d0ab2b2` (module labware naming on API 2.14+): Opus 5.5 on ecoli-heat-shock-transformation-hard,
0.30 -> 0.75. Regrading every other trial with `d0ab2b2` changed nothing (`scripts/regrade_jobs.py`).

- `REPORT.md`: reward per task, per risk check, per rubric item, and every failure with its evidence
  (`scripts/benchmark_report.py`).
- `<model>/<task>/`: `trial.json` (rewards, cost, tokens), `protocol.py` (what was graded), `reward.json`,
  `grader.json` (lint, traps, simulator summary, every check with expected vs measured, the judge's item-by-item verdict).

5 trials ended in `AgentSafetyRefusalError`: Anthropic's `[bio]` safeguard flagged the Golden Gate prompts for Opus 5.5
and Fable 5.1, and the paper-only E. coli transformation prompt for Fable 5.1. They are reported separately from
capability in `REPORT.md`.
