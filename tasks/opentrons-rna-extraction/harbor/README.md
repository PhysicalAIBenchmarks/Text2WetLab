# Opentrons OT-2 viral RNA extraction (Harbor task)

This is a [Harbor](https://github.com/laude-institute/harbor) benchmark task. An AI agent reads a paper and writes a working Opentrons OT-2 robot protocol. The protocol is then graded on what the simulated robot actually does.

- **Paper:** "Automated low-cost SARS-CoV-2 RNA extraction protocols", PLOS ONE 2021, [doi:10.1371/journal.pone.0246302](https://doi.org/10.1371/journal.pone.0246302)
- **Goal:** implement the paper's in-house 48-sample magnetic-bead RNA extraction as `/app/protocol.py`
- **Task name:** `opentrons/rna-extraction` (see `task.toml`)

## What is Harbor?

Harbor is a framework for evaluating AI agents on tasks that run in sandboxes. Each task is a folder with four parts:

| Part | Purpose |
|---|---|
| `instruction.md` | The prompt given to the agent |
| `environment/` | The Docker image the agent works in |
| `solution/` | A known-good answer, used by the `oracle` agent to check that the task is solvable |
| `tests/` | The grader. It is copied in only after the agent finishes, so the agent never sees it |

Harbor builds the environment and runs the agent (for example Claude Code) inside it. It then runs `tests/test.sh` and reads the reward from `/logs/verifier/reward.json`.

## Layout

```
tasks/opentrons-rna-extraction/harbor/
├── task.toml                 Harbor settings: timeouts, network allowlist, 4 CPU / 8 GB
├── instruction.md            The agent's task: deck layout, pipettes, reservoir map
├── environment/
│   ├── Dockerfile            python 3.10 + Claude Code + opentrons 7.5.0 (in /opt/ot)
│   └── data/                 Mounted read-only at /data
│       ├── paper.txt
│       └── labware/thermo_96_wellplate_200ul.json   Custom labware definition
├── solution/
│   ├── protocol.py           Oracle solution
│   └── solve.sh              Copies it to /app/protocol.py
└── tests/                    Hidden from the agent
    ├── test.sh               Entry point; runs grade.py
    ├── grade.py              Simulator gate, checks, LLM judge, reward
    ├── checks.py             16 deterministic checks on the simulator run log
    ├── runlog.py             Runs opentrons_simulate and normalizes the command log
    ├── reference_protocol.py The authors' protocol (ground truth, shown to the judge)
    └── variant.json          Variant label used in grading records
```

## How to run

You need Docker (or another Harbor environment such as Modal), Python 3.12+ and an Anthropic API key. The key is used by the agent and by the LLM judge (`task.toml` passes `ANTHROPIC_API_KEY` to the verifier).

```bash
pip install harbor            # or: uv tool install harbor
export ANTHROPIC_API_KEY=sk-ant-...

# 1. Sanity check: the oracle solution should score about 0.94
harbor run -p tasks/opentrons-rna-extraction/harbor -a oracle

# 2. Run an agent
harbor run -p tasks/opentrons-rna-extraction/harbor -a claude-code -m anthropic/claude-opus-5-5

# Options: 3 attempts per task, 3 at a time, on Modal instead of local Docker
harbor run -p tasks/opentrons-rna-extraction/harbor -a claude-code -m anthropic/claude-sonnet-5-5 -k 3 -n 3 -e modal
```

Each trial writes the following to `/logs/verifier/`, which ends up in the Harbor job output:
- `reward.json`: final reward and sub-scores
- `judge.json`: full record with checks, judge scores and evidence
- `events.json`: normalized simulator log
- `protocol.py`: a copy of the agent's protocol

To check a protocol by hand with the same simulator:

```bash
opentrons_simulate -L environment/data/labware solution/protocol.py
```

## How grading works

`tests/grade.py` runs four stages:

1. **Simulator gate.** `opentrons_simulate` (Opentrons 7.5.0) runs `/app/protocol.py`. If it crashes, times out or is missing, the reward is **0**.
2. **Deterministic run-log checks** (`checks.py`). These 16 checks look at what the robot would physically do:
   - `48_samples_to_odd_columns`, `step_order`
   - `binding_volumes_40_250_250`, `mix_5x_after_sample`, `incubation_5min_before_magnet`
   - `magnet_4min_before_first_removal`, `supernatant_removed_each_step`, `magnet_engaged_for_all_removals`
   - `two_500ul_ethanol_washes`, `air_dry_4min`
   - `elution_100ul`, `elution_off_magnet_then_90s_on`, `recover_70_100ul_one_well_each`
   - `distinct_elution_wells`, `elution_plate_4C_before_recovery`, `fresh_tip_per_sample_no_cross_contact`
3. **LLM judge** (`claude-sonnet-5-5`). The judge sees the paper, the reference protocol, the check results and the agent's code. It scores 9 rubric items at 0, 0.5 or 1: `deck_and_hardware`, `sample_handling`, `binding`, `magnetic_separation`, `washes`, `drying`, `elution_recovery`, `robot_practice` and `fidelity_to_paper`. **The reward is the mean of these 9 scores.**
4. **Critical cap.** If any critical check fails, the reward is capped at **0.3**. The critical checks cover sample count and placement, step order, supernatant removal, the two ethanol washes, recovery, and cross-contamination.

`reward.json` also reports `sim_pass`, `checks_frac`, `judge_mean`, `critical_fail`, `suspicious_code` (flags attempts to tamper with simulator internals), `judge_error` and one `rubric_<item>` score per rubric item.

## Results

| Protocol / agent | Reward |
|---|---|
| Ground truth (oracle) | 0.94 |
| Deliberately broken protocols | 0 to 0.78 |
| 9-model Anthropic sweep (27 trials), lowest: Haiku 4.5 | 0.30 |
| 9-model Anthropic sweep (27 trials), highest: Opus 5.5 and Fable 5.1 | 0.94 |

The broken protocols show that the grader catches real mistakes. The model sweep shows the task separates weaker and stronger models.

## Notes

- The agent's network is restricted to `api.anthropic.com` and `registry.npmjs.org`. The authors' published code is not reachable.
- The agent must use OT-2 `apiLevel` 2.2 to 2.15 and the fixed deck described in `instruction.md`.
- Reference protocol source: [HULPopentrons/RNA_extraction_OT2opentrons](https://github.com/HULPopentrons/RNA_extraction_OT2opentrons/blob/master/viral_rna_extraction_protocol.py).
