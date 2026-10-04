# Text2WetLab Harbor tasks (Opentrons OT-2)

Seven [Harbor](https://github.com/laude-institute/harbor) benchmark tasks. In each one an AI agent writes an Opentrons OT-2 Python protocol to `/app/protocol.py`, and the protocol is graded on what the simulated robot actually does.

## Tasks

| Task | What the agent must automate | Grader |
|---|---|---|
| `a1-a12-100ul` | 100 µL from a 1-well reservoir to wells A1 to A12 | Simulator, end-state checks and LLM judge |
| `split-200ul-two-wells` | Split 200 µL into two 100 µL wells | Simulator, end-state checks and LLM judge |
| `ampure-bead-cleanup` | AMPure XP magnetic bead cleanup of PCR products | Simulator, end-state checks and LLM judge |
| `colony-pcr-screening` | Colony PCR screening with Q5 Hot Start master mix | Simulator, end-state checks and LLM judge |
| `ecoli-heat-shock-transformation` | E. coli heat shock transformation with SOC recovery | Simulator, end-state checks and LLM judge |
| `golden-gate-assembly` | Golden Gate assembly of four four-fragment chromoprotein plasmids (AssemblyTron) | Simulator, end-state checks and LLM judge |
| `opentrons-rna-extraction` | 48-sample magnetic-bead SARS-CoV-2 RNA extraction from PLOS ONE 2021 ([doi:10.1371/journal.pone.0246302](https://doi.org/10.1371/journal.pone.0246302)) | Simulator, run-log checks and LLM judge |

## What is Harbor?

Harbor is a framework for evaluating AI agents on tasks that run in sandboxes. Every task folder here has the same parts:

```
tasks/<task>/
├── task.toml        Harbor settings: timeouts, network allowlist, 4 CPU / 8 GB
├── instruction.md   The prompt given to the agent: deck, labware, pipettes, steps
├── environment/     Dockerfile for the agent's sandbox (python 3.10, Claude Code, opentrons 7.5.0)
│                    (RNA, golden-gate and colony PCR also ship data/paper.txt, mounted read-only at /data)
├── solution/        protocol.py + solve.sh: the oracle answer, used to check the task is solvable
└── tests/           The grader. It is copied in only after the agent finishes, so the agent never sees it
    └── test.sh      Entry point; writes /logs/verifier/reward.json
```

Harbor builds the environment and runs the agent inside it. It then runs `tests/test.sh` and reads the reward.

## How to run

### 1. Prerequisites

- Python 3.12+ (Harbor won't install on 3.10) and [uv](https://docs.astral.sh/uv/) or pip
- Docker running locally, **or** a [Modal](https://modal.com) account for cloud sandboxes
- An Anthropic API key. The Claude Code agent uses it, and all 7 graders use it for the LLM judge

```bash
git clone -b devin/1791063775-opentrons-rna-extraction-only https://github.com/PhysicalAIBenchmarks/Text2WetLab.git
cd Text2WetLab

uv tool install harbor            # or: pip install harbor
export ANTHROPIC_API_KEY=sk-ant-...

# Modal only: extra packages + one-time login
pip install modal dockerfile-parse     # or: uv tool install harbor --with modal --with dockerfile-parse
modal token new
```

If you don't want to install Harbor, put `uvx --python 3.12 --from harbor` in front of every `harbor` command below (for Modal: `uvx --python 3.12 --from harbor --with modal --with dockerfile-parse`).

### 2. Check that the tasks are solvable (oracle)

The oracle "agent" just copies `solution/protocol.py`. Run it first to confirm the images build and the graders work:

```bash
harbor run -p tasks -a oracle -y
```

Expected: 1.0 on 6 tasks and 0.8 on RNA extraction (its reference script labels the ethanol "absolute" instead of 70%, so it fails `fidelity_to_paper`).

### 3. Run an agent on all 7 tasks

```bash
# Local Docker, 2 tasks at a time
harbor run -p tasks -a claude-code -m anthropic/claude-sonnet-5-5 -n 2 -y

# Modal sandboxes, all 7 tasks in parallel
harbor run -p tasks -a claude-code -m anthropic/claude-sonnet-5-5 -e modal -n 7 -y
```

Swap the model with `-m anthropic/claude-opus-5-5` or `-m anthropic/claude-fable-5-1`. To compare models, run one command per model; they can run at the same time.

### 4. Run a subset or repeat attempts

```bash
# One task
harbor run -p tasks/golden-gate-assembly -a claude-code -m anthropic/claude-opus-5-5 -y

# Several tasks by name (glob patterns work)
harbor run -p tasks -i 'colony-pcr-screening' -i 'ecoli-*' -a claude-code -m anthropic/claude-opus-5-5 -y

# 3 attempts per task (pass@k), on Modal
harbor run -p tasks/opentrons-rna-extraction -a claude-code -m anthropic/claude-opus-5-5 -k 3 -e modal -y
```

Paths for each task:

| Task | `-p` path |
|---|---|
| A1 to A12, 100 µL | `tasks/a1-a12-100ul` |
| Split 200 µL into two wells | `tasks/split-200ul-two-wells` |
| AMPure bead cleanup | `tasks/ampure-bead-cleanup` |
| Colony PCR screening | `tasks/colony-pcr-screening` |
| E. coli heat shock transformation | `tasks/ecoli-heat-shock-transformation` |
| Golden Gate assembly | `tasks/golden-gate-assembly` |
| RNA extraction (PLOS ONE 2021) | `tasks/opentrons-rna-extraction` |

Useful flags:
- `-y` auto-confirms prompts. Without it, Harbor stops and asks before passing `ANTHROPIC_API_KEY` to the verifier
- `-n` sets how many trials run at once, `-k` sets attempts per task
- `-o <dir>` changes the output folder (default `jobs/`), `--job-name` names the run
- `--force-build` rebuilds the task images after you edit a Dockerfile

### 5. Read the results

Each run creates `jobs/<job-name>/`. Inside it, `result.json` holds the job-level scores, and each trial folder has:
- `agent/`: the Claude Code transcript, plus token and cost counts
- `verifier/reward.json`: final reward and sub-scores
- `verifier/protocol.py`: a copy of the graded protocol
- `verifier/judge.json`: checks, judge scores and evidence (RNA also writes `verifier/events.json`, the simulator log)

Rewards go from 0 to 1 and are capped at 0.3 when a critical check fails (see below).

## How grading works

### The other 6 tasks (`tests/grade.py` + `tests/judge_layer.py`)

1. **Lint.** `protocol_lint.py` rejects code that reaches into simulator internals. A lint failure scores 0.
2. **Simulator gate.** `opentrons_simulate` runs the protocol. If it crashes, the reward is 0.
3. **End-state checks.** `spec_check.py` compares the simulated deck against the task spec (`tests/ir.json`, `deck.json`, `checks.json`): labware in the right slots, the right contents in each well, and safety rules (tip use, no over-aspirating, no cross-contamination). The old pass/fail score is kept as `deterministic_reward`.
4. **LLM judge.** `claude-sonnet-5-5` scores the task's 5 items in `tests/rubric.json` as pass (1) or fail (0), with no partial credit, so each item is worth 20%. It sees the instruction, the check results, the reference protocol and, for golden-gate and colony PCR, the paper. The reward is the mean of those scores.
5. **Critical cap.** If a labware, end-state or safety check fails, the reward is capped at 0.3.

Paper text: golden-gate (AssemblyTron, CC BY) and colony PCR (Slowpoke, CC BY) ship `environment/data/paper.txt` at `/data`. Heat-shock's source (APEX, bioRxiv) is "all rights reserved", so it is not included. Ampure (code only), a1-a12 and split (handwritten) have no paper, so the judge scores them against the instruction.

Validation (earlier partial-credit rubric): deliberately broken oracles scored 0.72 (ampure with incubation, magnet and drying steps removed, which still passes the end-state checks) and 0.3 (colony PCR reusing one tip across colonies, which trips the cap).

### opentrons-rna-extraction (`tests/grade.py`)

1. **Simulator gate.** `opentrons_simulate` (Opentrons 7.5.0) runs the protocol. If it crashes, the reward is 0.
2. **Run-log checks.** `checks.py` runs 16 deterministic checks on the normalized log, covering volumes, step order, incubation, magnet and drying times, recovery, the 4 °C plate, and fresh tips with no cross-contact.
3. **LLM judge.** `claude-sonnet-5-5` scores 5 rubric items as pass (1) or fail (0), each worth 20%. The reward is the mean of those scores.
4. **Critical cap.** If a critical check fails, the reward is capped at 0.3. The critical checks are sample count, step order, supernatant removal, the two ethanol washes, recovery, and cross-contamination.

With binary scoring, the ground truth scores 0.8: it fails `fidelity_to_paper` because it labels the ethanol "absolute" instead of 70%.

## Rubrics (what the judge scores)

Each task has 5 items. The judge (`claude-sonnet-5-5`) gives every item **1 (pass) or 0 (fail)**, with no partial credit, so each item is worth **20%**. Reward = passed items / 5, so the possible scores are 0, 0.2, 0.4, 0.6, 0.8 and 1.0.

Before the judge runs, the protocol must simulate without error (otherwise 0). The deterministic checks also run first. If a critical one fails (labware/deck, end-state volumes, cross-contamination, pipetting without a tip, aspirating from an empty well, over-dispensing; for RNA, the 6 critical run-log checks), the reward is capped at **0.3**. The judge is told to treat the check results as facts.

### a1-a12-100ul

Judged against: task text (no paper). Source: `tasks/a1-a12-100ul/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `deck_and_hardware` | Loads the specified labware in the given slots with the given labels, and uses suitable pipettes and tip racks. |
| 2 | `volumes_and_wells` | Exactly 100 uL from reservoir A1 into each of plate wells A1-A12 using the 300 uL pipette, and no other wells touched. |
| 3 | `tip_usage` | Never pipettes without a tip and drops the tip at the end. Reusing one tip or using a fresh tip per well both pass. |
| 4 | `robot_practice` | Volumes within pipette limits, apiLevel valid, nothing physically unsafe or nonsensical. |
| 5 | `fidelity_to_task` | No missing steps and no steps that change the outcome; comments and metadata are accurate. |

### split-200ul-two-wells

Judged against: task text (no paper). Source: `tasks/split-200ul-two-wells/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `deck_and_hardware` | Loads the specified labware in the given slots with the given labels, and uses suitable pipettes and tip racks. |
| 2 | `volumes_and_wells` | 200 uL from reservoir A1 split as exactly 100 uL into plate A1 and 100 uL into B1 using the 300 uL pipette, and no other wells touched. |
| 3 | `tip_usage` | Never pipettes without a tip and drops the tip at the end. Reusing one tip or using fresh tips both pass. |
| 4 | `robot_practice` | Volumes within pipette limits, apiLevel valid, nothing physically unsafe or nonsensical. |
| 5 | `fidelity_to_task` | No missing steps and no steps that change the outcome; comments and metadata are accurate. |

### ampure-bead-cleanup

Judged against: task text (no paper). Source: `tasks/ampure-bead-cleanup/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `binding` | 40 uL beads (0.8x) into each of the 96 samples, mixed about 10 times, and a 5 min incubation recorded before the magnet. |
| 2 | `supernatant_and_washes` | Magnet engaged and settle recorded, about 90 uL supernatant removed to waste from every well, then two 200 uL 80% ethanol washes each fully removed to waste. |
| 3 | `drying_and_elution` | About 5 min air dry, magnet disengaged, 50 uL water added and mixed about 10 times, 2 min incubation, then magnet re-engaged. |
| 4 | `recovery` | 45 uL eluate moved from each sample well to the matching elution plate well, so sample identity is preserved. |
| 5 | `tips_and_contamination` | A fresh tip whenever touching a different sample (supernatant removal, ethanol removal, elution) and no cross-contamination between samples. |

### colony-pcr-screening

Judged against: task text + Slowpoke paper (`/data/paper.txt`). Source: `tasks/colony-pcr-screening/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `master_mix` | 18 uL Q5 2x master mix into each of the 96 PCR wells. |
| 2 | `template_and_primers` | 1 uL colony template and 1 uL primer pair from each source well into the matching PCR well with the 20 uL pipette, giving 20 uL reactions. |
| 3 | `tips_and_contamination` | A fresh tip for every colony and every primer pair, and no cross-contamination between samples. Reusing one tip for master mix into empty wells passes. |
| 4 | `thermocycling` | Seal and the thermocycling program (98 C 30 s; 30x [98 C 10 s, 60 C 30 s, 72 C 30 s]; 72 C 2 min; 4 C hold) recorded. |
| 5 | `fidelity_to_paper` | Consistent with the task text and the Slowpoke paper; no missing or invented steps; comments and metadata are accurate. |

### ecoli-heat-shock-transformation

Judged against: task text (no paper). Source: `tasks/ecoli-heat-shock-transformation/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `dna_addition` | 2 uL plasmid DNA from plasmid plate A1 into the competent-cell tube A1 with the 20 uL pipette. |
| 2 | `heat_shock` | Heat shock at 42 C for 45 s, then 2 min on ice, recorded in that order after DNA addition. |
| 3 | `soc_recovery` | 250 uL SOC added to the tube after the heat shock, and the 37 C, 60 min, 250 rpm outgrowth recorded. |
| 4 | `tip_usage` | A fresh tip for the DNA and for the SOC, no contamination of cells or stocks, and the tip dropped at the end. |
| 5 | `fidelity_to_task` | No missing or reordered steps and nothing added that would change the outcome; comments and metadata are accurate. |

### golden-gate-assembly

Judged against: task text + AssemblyTron paper (`/data/paper.txt`). Source: `tasks/golden-gate-assembly/tests/rubric.json`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `pcr_setup` | PCR reactions for each fragment set up as specified (primer and template amounts, reaction volume) with primers and templates paired to the correct wells. |
| 2 | `dpni_and_cleanup` | DpnI digestion and the fragment clean-up and concentration steps carried out or recorded in order. |
| 3 | `assembly_mix` | Fragments combined in the specified volumes for each assembly with BsaI-HFv2, T4 ligase and buffer, with volumes matching the task. |
| 4 | `cycling_and_transformation` | Golden Gate cycling program run or recorded as specified, then assemblies transformed into TOP10 cells as specified. |
| 5 | `tips_and_contamination` | Fresh tips between different fragments and assemblies, and no cross-contamination. |

### opentrons-rna-extraction

Judged against: PLOS ONE paper (`/data/paper.txt`). Source: `tasks/opentrons-rna-extraction/tests/grade.py`.

| # | Item | Passes only if |
|---|---|---|
| 1 | `sample_handling` | All 48 samples, 250 uL each, one fresh tip per sample, one sample per well, no cross-contamination, and each sample traceable to its elution well. |
| 2 | `binding_and_separation` | 40 uL beads, 250 uL isopropanol, then 250 uL sample in that order, mixed 5 times, 5 min incubation, magnet engaged about 4 min, then supernatant removed to waste with the magnet on. |
| 3 | `washes_and_drying` | Two 500 uL 70% ethanol washes, each fully removed with the magnet engaged, then about 4 min air-dry and the magnet disengaged before elution. |
| 4 | `elution_recovery` | 100 uL elution added off-magnet and mixed, magnet re-engaged about 90 s, and about 80 uL recovered into a distinct well of the elution plate held at 4 C. |
| 5 | `fidelity_to_paper` | No invented, missing or reordered steps relative to the paper; reagent identities and comments/metadata are accurate. |

## Results

The Claude Code agent (`-a claude-code`) was run with Harbor in Modal sandboxes (`-e modal`), 1 attempt per task per model (pass@1), on 2026-10-04. All 7 tasks used the common grader with 5 pass/fail judge items (20% each). The oracle solutions scored 1.0 on 6 tasks and 0.8 on RNA extraction, where the authors' script labels the ethanol "absolute" but the paper says 70%.

| Task | Opus 5.5 | Sonnet 5.5 | Fable 5.1 |
|---|---|---|---|
| a1-a12-100ul | 1.0 | 1.0 | 1.0 |
| split-200ul-two-wells | 1.0 | 1.0 | 1.0 |
| ampure-bead-cleanup | 1.0 | 1.0 | 1.0 |
| colony-pcr-screening | 1.0 | 1.0 | 1.0 |
| ecoli-heat-shock-transformation | 0.8 | 1.0 | 0.8 |
| golden-gate-assembly | 1.0 | 1.0 | 1.0 |
| opentrons-rna-extraction | 0.8 | 0.4 | 1.0 |
| **Mean** | **0.943** | **0.914** | **0.971** |
| Agent cost (USD) | 1.28 | 0.39 | 3.05 |

What the results show:
- **No trial errored or failed a deterministic or critical check.** Every point lost came from a failed judge item.
- **Heat-shock (Opus, Fable):** failed `fidelity_to_task` for pipette-mixing the competent cells, which the task doesn't ask for.
- **RNA extraction:** Opus and Sonnet failed `elution_recovery` for recovering 100 µL instead of about 80 µL. Sonnet also added the sample before the beads and isopropanol, so it failed `binding_and_separation` and `fidelity_to_paper` too. Fable passed all 5 items.
- **The other 5 tasks didn't separate the models.** With 1 attempt per model and an LLM judge, treat differences between models as indicative only.

Per-trial tokens, cost, duration and rubric scores are in `results/summary.json`. Each `results/<model>/<task>/` folder holds the graded `protocol.py`, `reward.json` and `judge.json`.

## Notes

- The agent's network is restricted to `api.anthropic.com` and `registry.npmjs.org`.
- The 6 deterministic tasks come from the `feat/ingestion` branch (`tasks/<task>/harbor/`).
- RNA extraction reference protocol: [HULPopentrons/RNA_extraction_OT2opentrons](https://github.com/HULPopentrons/RNA_extraction_OT2opentrons/blob/master/viral_rna_extraction_protocol.py).
