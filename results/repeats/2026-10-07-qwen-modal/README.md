# Qwen3.8-2.4T-A95B, repeated on Modal (2026-10-07)

The same model, agent (Claude Code via OpenRouter), tasks and grader as the Qwen run in
[`results/runs/2026-10-07-openrouter`](../../runs/2026-10-07-openrouter/), run a second time on Modal with all 11
tasks at once (`harbor run ... -e modal -n 11`) instead of local Docker two at a time. It measures two things: what
running in parallel on Modal buys, and how much one model's score moves between two pass@1 attempts. The leaderboard
uses the local run, so every model there ran in the same environment except DeepSeek V4 Pro (Modal only).

| Job | Trials | Wall clock | Median trial | Median env setup | Median agent | Median verifier | Agent cost | Mean reward (answered) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Qwen, local Docker (2 at a time) | 11 | 54.7 min | 4.4 min | 7 s | 3.0 min | 46 s | $2.83 | 0.728 (n=11) |
| Qwen, Modal (11 at a time) | 11 | 31.9 min | 7.8 min | 1.5 min | 4.9 min | 45 s | $3.61 | 0.805 (n=11) |
| DeepSeek, Modal (11 at a time) | 11 | 12.0 min | 4.7 min | 1.5 min | 1.8 min | 53 s | $2.53 | 0.581 (n=11) |

| Task | Qwen, local Docker (2 at a time) | Qwen, Modal (11 at a time) | DeepSeek, Modal (11 at a time) |
|---|:---:|:---:|:---:|
| `a1-a12-100ul` | 1.00 | 1.00 | 0.00 |
| `ampure-bead-cleanup` | 1.00 | 1.00 | 0.30 |
| `colony-pcr-screening` | 1.00 | 1.00 | 1.00 |
| `ecoli-heat-shock-transformation` | 1.00 | 1.00 | 1.00 |
| `golden-gate-assembly` | 0.30 | 0.30 | 1.00 |
| `opentrons-rna-extraction` | 0.30 | 1.00 | 0.30 |
| `split-200ul-two-wells` | 1.00 | 1.00 | 1.00 |
| `colony-pcr-screening-hard` | 0.67 | 0.75 | 0.30 |
| `ecoli-heat-shock-transformation-hard` | 0.75 | 0.30 | 0.75 |
| `golden-gate-assembly-hard` | 0.30 | 0.75 | 0.30 |
| `opentrons-rna-extraction-hard` | 0.69 | 0.75 | 0.44 |

Made with `scripts/compare_jobs.py ... --prices`. Rewards are as graded at run time: DeepSeek's two grader false
positives (`a1-a12-100ul` 0.00 and `colony-pcr-screening-hard` 0.30 here) were fixed and regraded to 1.00 in the main run.

- **Wall clock.** Modal finished in 31.9 min against 54.7 min locally (1.7x). With every task running at once the wall
  clock is the slowest trial: Qwen's 28-minute agent session on `opentrons-rna-extraction`. DeepSeek, with no such
  outlier, finished all 11 in 12.0 min.
- **Per-trial overhead.** Modal builds each task's image in its sandbox (median 1.5 min against 7 s locally, where
  images are cached), and its agent sessions ran longer (median 4.9 against 3.0 min).
- **Run-to-run variation.** The mean moved 0.728 to 0.805 between two attempts of the same model. Four tasks changed
  score: RNA extraction 0.30 to 1.00, heat-shock-hard 0.75 to 0.30, Golden-Gate-hard 0.30 to 0.75, colony-PCR-hard
  0.67 to 0.75. Differences of this size between models on single attempts are within noise.
