# Haiku as judge: two experiments (not adopted)

The judge stays **`claude-sonnet-5-5`, one call scoring all 5 rubric items**. This file records two runs on 2026-10-04 that tried `claude-haiku-4-5-20251001` as a cheaper judge, and why it was not adopted.

Both runs used Harbor's Claude Code agent (`-a claude-code`) in Modal sandboxes (`-e modal`): 7 tasks × Opus 5.5, Sonnet 5.5 and Fable 5.1, 1 attempt each, 21 trials. Every protocol passed the simulator, no trial tripped a reward-hacking trap, and none failed the code check. The agents wrote new protocols in each run, so score differences mix judge differences with run-to-run noise.

## Run 1: Haiku, one call for all 5 items

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 1.0 | 1.0 |
| split-200ul-two-wells | 1.0 | 1.0 | 1.0 |
| ampure-bead-cleanup | 0 (judge error) | 0 (judge error) | 0 (judge error) |
| colony-pcr-screening | 1.0 | 0.6 | 1.0 |
| ecoli-heat-shock-transformation | 1.0 | 0.4 | 1.0 |
| golden-gate-assembly | 1.0 | 1.0 | 1.0 |
| opentrons-rna-extraction | 0.6 | 0.4 | 0.8 |
| **Mean, all 7** | **0.800** | **0.629** | **0.829** |
| Mean, without ampure | 0.933 | 0.733 | 0.967 |
| Agent cost (USD) | 1.82 | 0.56 | 5.48 |

- **Ampure judge error:** 96 samples give a 7,877-move run log; the judge prompt is ~212k tokens, over Haiku's 200k limit (`prompt is too long: 212020 tokens > 200000 maximum`). The grader then records `judge_error: 1` and reward 0. These zeros say nothing about the models.
- **RNA:** like Sonnet-as-judge, Haiku failed `elution_recovery` for all 3 models (100 µL recovered instead of ~80 µL). It also failed Opus's `fidelity_to_paper` for the same mistake, and Sonnet's `washes_and_drying` for leaving the magnet engaged while drying.
- **Sonnet, heat-shock:** failed `heat_shock`, `soc_recovery`, `fidelity_to_paper` for skipping the return to 4 °C after the heat shock.
- **Sonnet, colony PCR:** failed `reaction_setup` and `fidelity_to_paper` over master-mix construction.

## Run 2: Haiku, one call per rubric item

Each item scored in its own call (5 parallel calls per trial), following [AutoRubric](https://autorubric.org/docs/cookbook/llm-judges/)'s default.

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 1.0 | 0.8 |
| split-200ul-two-wells | 1.0 | 1.0 | 1.0 |
| ampure-bead-cleanup | 0 (judge error) | 0 (judge error) | 0 (judge error) |
| colony-pcr-screening | 0.2 | 0.2 | 0.6 |
| ecoli-heat-shock-transformation | 0.4 | 0.8 | 0.8 |
| golden-gate-assembly | 0.2 | 0.0 | 0.4 |
| opentrons-rna-extraction | 0.0 | 0.0 | 0.0 |
| **Mean, all 7** | **0.400** | **0.429** | **0.514** |
| Mean, without ampure | 0.467 | 0.500 | 0.600 |
| Agent cost (USD) | 1.75 | 0.59 | 4.78 |

- Ampure still exceeded the context limit: each per-item call still contains the full run log.
- Haiku misread protocols, for example:
  - Fable a1-a12 failed `volumes_and_wells` on the claim that `plate.rows()[0]` is A1–H1 (it is A1–A12).
  - Opus RNA failed `fidelity_to_paper` for transferring "only 80 µL instead of 100 µL"; the log shows 100 µL.
  - Fable RNA failed every item, including for disengaging the magnet before elution, which the rubric requires.
- One mistake was counted against several items (e.g. a wrong volume also failed `robot_practice` and `fidelity_to_task`).

## Comparison of means

| Judge | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| Sonnet 5.5, one call (README results) | 0.971 | 0.857 | 0.971 |
| Haiku 4.5, one call | 0.800 | 0.629 | 0.829 |
| Haiku 4.5, one call per item | 0.400 | 0.429 | 0.514 |

## Decision

Keep Sonnet 5.5 with one call. It fits every task's run log (including ampure), and its failed items matched real mistakes when checked. A cheaper judge would first need the run log shortened (collapsing repeated moves with exact counts) and then a side-by-side re-judge of the same protocols with both judges.
