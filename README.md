# Text2WetLab Harbor tasks (Opentrons OT-2)

Seven [Harbor](https://github.com/laude-institute/harbor) benchmark tasks. In each one an AI agent writes an Opentrons OT-2 Python protocol to `/app/protocol.py`, and the protocol is graded on what the simulated robot actually does.

## Tasks

| Task | What the agent must automate | Grader |
|---|---|---|
| `a1-a12-100ul` | 100 µL from a 1-well reservoir to wells A1 to A12 | Deterministic |
| `split-200ul-two-wells` | Split 200 µL into two 100 µL wells | Deterministic |
| `ampure-bead-cleanup` | AMPure XP magnetic bead cleanup of PCR products | Deterministic |
| `colony-pcr-screening` | Colony PCR screening with Q5 Hot Start master mix | Deterministic |
| `ecoli-heat-shock-transformation` | E. coli heat shock transformation with SOC recovery | Deterministic |
| `golden-gate-assembly` | Golden Gate assembly of four four-fragment chromoprotein plasmids (AssemblyTron) | Deterministic |
| `opentrons-rna-extraction` | 48-sample magnetic-bead SARS-CoV-2 RNA extraction from PLOS ONE 2021 ([doi:10.1371/journal.pone.0246302](https://doi.org/10.1371/journal.pone.0246302)) | Simulator, run-log checks and LLM judge |

## What is Harbor?

Harbor is a framework for evaluating AI agents on tasks that run in sandboxes. Every task folder here has the same parts:

```
tasks/<task>/
├── task.toml        Harbor settings: timeouts, network allowlist, 4 CPU / 8 GB
├── instruction.md   The prompt given to the agent: deck, labware, pipettes, steps
├── environment/     Dockerfile for the agent's sandbox (python 3.10, Claude Code, opentrons 7.5.0)
│                    (opentrons-rna-extraction also ships data/: paper.txt and custom labware, mounted read-only at /data)
├── solution/        protocol.py + solve.sh: the oracle answer, used to check the task is solvable
└── tests/           The grader. It is copied in only after the agent finishes, so the agent never sees it
    └── test.sh      Entry point; writes /logs/verifier/reward.json
```

Harbor builds the environment and runs the agent inside it. It then runs `tests/test.sh` and reads the reward.

## How to run

You need Docker (or another Harbor environment such as Modal), Python 3.12+ and an Anthropic API key. Only `opentrons-rna-extraction` uses the key at grading time, for its LLM judge.

```bash
pip install harbor            # or: uv tool install harbor
export ANTHROPIC_API_KEY=sk-ant-...

# 1. Oracle check: should score 1.0 on the 6 deterministic tasks and about 0.94 on RNA extraction
harbor run -p tasks -a oracle -y

# 2. Run an agent on all 7 tasks (2 at a time)
harbor run -p tasks -a claude-code -m anthropic/claude-sonnet-5-5 -n 2 -y

# Run one task, 3 attempts each, on Modal
harbor run -p tasks/opentrons-rna-extraction -a claude-code -m anthropic/claude-opus-5-5 -k 3 -e modal -y
```

Each trial writes the following to `/logs/verifier/`, which ends up in the Harbor job output:
- `reward.json`: final reward and sub-scores
- `protocol.py`: a copy of the graded protocol
- RNA task only: `judge.json` (checks, judge scores and evidence) and `events.json` (simulator log)

## How grading works

### The 6 deterministic tasks (`tests/grade.py`, no LLM)

1. **Lint.** `protocol_lint.py` rejects code that reaches into simulator internals. A lint failure scores 0.
2. **Simulator gate.** `opentrons_simulate` runs the protocol. If it crashes, the reward is 0.
3. **End-state checks.** `spec_check.py` compares the simulated deck against the task spec (`tests/ir.json`, `deck.json`, `checks.json`). It checks that the right labware is in the right slot, that each well ends with the right contents, and that safety rules hold (tip use, no over-aspirating, and so on).
4. **Reward.** 1.0 if every check passes. Otherwise up to 0.5 for the fraction of substantive checks that pass, halved again if a safety rule was broken.

### opentrons-rna-extraction (`tests/grade.py`)

1. **Simulator gate.** `opentrons_simulate` (Opentrons 7.5.0) runs the protocol. If it crashes, the reward is 0.
2. **Run-log checks.** `checks.py` runs 16 deterministic checks on the normalized log, covering volumes, step order, incubation, magnet and drying times, recovery, the 4 °C plate, and fresh tips with no cross-contact.
3. **LLM judge.** `claude-sonnet-5-5` scores 9 rubric items at 0, 0.5 or 1. The reward is the mean of those scores.
4. **Critical cap.** If a critical check fails, the reward is capped at 0.3. The critical checks are sample count, step order, supernatant removal, the two ethanol washes, recovery, and cross-contamination.

During development, the ground truth scored 0.94 and deliberately broken protocols scored 0 to 0.78.

## Results

The Claude Code agent was run with Harbor 0.23.0 on local Docker, 1 attempt per task per model (pass@1), on 2026-10-04. The oracle scored 1.0 on all 6 deterministic tasks.

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 1.0 | 1.0 |
| split-200ul-two-wells | 1.0 | 1.0 | 1.0 |
| ampure-bead-cleanup | 1.0 | 1.0 | 1.0 |
| colony-pcr-screening | 1.0 | 1.0 | 1.0 |
| ecoli-heat-shock-transformation | 1.0 | 1.0 | 1.0 |
| golden-gate-assembly | 1.0 | 1.0 | 1.0 |
| opentrons-rna-extraction | 0.889 | 0.944 | 0.944 |
| **Mean** | **0.984** | **0.992** | **0.992** |
| Agent cost (USD) | 1.16 | 0.37 | 2.83 |

What the results show:
- **The 6 deterministic tasks didn't separate the models.** Every model solved every one at the first attempt.
- **RNA extraction:** all 3 models passed all 16 run-log checks and had no critical failures. The judge gave all of them half credit on `elution_recovery`, because each recovered the full 100 µL of eluate instead of about 80 µL. Opus also got half credit on `fidelity_to_paper` for a misattributed author name in the docstring and metadata.

Per-trial tokens, cost and duration are in `results/summary.json`. Each `results/<model>/<task>/` folder holds the graded `protocol.py`, `reward.json` and, for the RNA task, `judge.json`.

## Notes

- The agent's network is restricted to `api.anthropic.com` and `registry.npmjs.org`.
- The 6 deterministic tasks come from the `feat/ingestion` branch (`tasks/<task>/harbor/`).
- RNA extraction reference protocol: [HULPopentrons/RNA_extraction_OT2opentrons](https://github.com/HULPopentrons/RNA_extraction_OT2opentrons/blob/master/viral_rna_extraction_protocol.py).
