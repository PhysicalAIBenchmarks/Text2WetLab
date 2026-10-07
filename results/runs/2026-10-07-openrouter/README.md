# 2026-10-07: Sonnet 5.5, Opus 5.5, Fable 5.1 and GPT-6.1 Sol on all 11 tasks

Harbor 0.23.0, agent `claude-code` (Claude Code 2.1.288) for every model, one attempt per task (pass@1), Docker via
Colima. Agent and judge (Claude Sonnet 5.5, three calls per protocol, majority per item) both through OpenRouter.
Harbor pins every Claude Code model alias and sub-agent to the model under test; every GPT-6.1 Sol transcript,
sub-agents included, contains only `openai/gpt-6.1-sol` responses.

- The three Claude models ran first, against the tasks at `8da544a`. Their saved protocols were then regraded with
  the final verifier (`scripts/regrade_jobs.py --judge --all`); each `trial.json` keeps the first grades as
  `original_rewards`. GPT-6.1 Sol ran later and was graded by the final verifier directly.
- Not yet re-judged (the key ran out of credit): the RNA trials were judged before the `recover_about_80ul` check and
  the RNA rubric's 100 uL line were added, and three Sonnet trials got fewer than three judge votes because of a
  network outage (ampure 2, ecoli-hard 1, colony-hard 2 votes split 1-1). Each record shows its votes.
- `REPORT.md`: reward per task, per risk check, per rubric item, and every failure with its evidence and votes
  (`scripts/benchmark_report.py results/runs/2026-10-07-openrouter/*/`).
- `<model>/<task>/`: `trial.json` (rewards, cost, tokens), `protocol.py` (what was graded), `reward.json`,
  `grader.json` (lint, traps, simulator summary, every check with expected vs measured, every judge vote), written by
  `scripts/export_run.py`.

5 trials ended in `AgentSafetyRefusalError`: Anthropic's `[bio]` safeguard flagged the Golden Gate prompts for Opus 5.5
and Fable 5.1, and the paper-only E. coli transformation prompt for Fable 5.1. They are reported separately from
capability in `REPORT.md`.
