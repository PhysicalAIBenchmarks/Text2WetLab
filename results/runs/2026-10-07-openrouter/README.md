# 2026-10-07: six models on all 11 tasks

Claude Sonnet 5.5, Opus 5.5 and Fable 5.1, GPT-6.1 Sol, Qwen3.8-2.4T-A95B and DeepSeek V4 Pro. Harbor 0.23.0, agent
`claude-code` (Claude Code 2.1.288) for every model, one attempt per task (pass@1). Agent and judge (Claude Sonnet 5.5,
three calls per protocol, majority per item) both through OpenRouter. Harbor pins every Claude Code model alias and
sub-agent to the model under test; every non-Claude transcript, sub-agents included, contains only that model's responses.

- **Where they ran.** Docker via Colima, two tasks at a time, for every model except DeepSeek V4 Pro, which ran on
  Modal with all 11 at once. Qwen was also repeated on Modal to measure the backend and run-to-run variation:
  [`results/repeats/2026-10-07-qwen-modal`](../../repeats/2026-10-07-qwen-modal/).
- **Grading.** Every trial is graded by the final verifier: the Claude trials ran first and were regraded
  (`scripts/regrade_jobs.py --judge --all`), and each `trial.json` keeps the first grades as `original_rewards`. Every
  judged trial has three judge votes except Sonnet's `ampure-bead-cleanup`, which has two that agree on every item.
  DeepSeek's `a1-a12-100ul` and `colony-pcr-screening-hard` were regraded after two grader false positives its
  protocols exposed were fixed (a lint rule that blocked `pipette.tip_racks = [...]`, and a contamination rule that
  flagged mixing a source well before drawing from it).
- **Cost.** `cost_usd` is the agent's cost for the trial. Claude Code prices every model as a Claude model, so for
  GPT, Qwen and DeepSeek it is recomputed from the token counts at the OpenRouter prices in `prices.json`; Claude
  Code's own figure is kept as `claude_code_cost_usd`.
- `REPORT.md`: reward per task, per risk check, per rubric item, and every failure with its evidence and votes
  (`scripts/benchmark_report.py results/runs/2026-10-07-openrouter/*/`).
- `<model>/<task>/`: `trial.json` (rewards, cost, tokens), `protocol.py` (what was graded), `reward.json`,
  `grader.json` (lint, traps, simulator summary, every check with expected vs measured, every judge vote), written by
  `scripts/export_run.py`.

5 trials ended in `AgentSafetyRefusalError`: Anthropic's `[bio]` safeguard flagged the Golden Gate prompts for Opus 5.5
and Fable 5.1, and the paper-only E. coli transformation prompt for Fable 5.1. Refused tasks are not scored; they are
reported separately in `REPORT.md`, and models are ranked on the 8 tasks every model answered.
