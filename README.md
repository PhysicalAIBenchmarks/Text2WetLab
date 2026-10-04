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

Expected: about 0.89 to 1.0 on every task (the LLM judge rarely gives the reference full marks).

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
4. **LLM judge.** `claude-sonnet-5-5` scores the task's `tests/rubric.json` (6 to 9 items) at 0, 0.5 or 1. It sees the instruction, the check results, the reference protocol and, for golden-gate and colony PCR, the paper. The reward is the mean of those scores.
5. **Critical cap.** If a labware, end-state or safety check fails, the reward is capped at 0.3.

Paper text: golden-gate (AssemblyTron, CC BY) and colony PCR (Slowpoke, CC BY) ship `environment/data/paper.txt` at `/data`. Heat-shock's source (APEX, bioRxiv) is "all rights reserved", so it is not included. Ampure (code only), a1-a12 and split (handwritten) have no paper, so the judge scores them against the instruction.

Validation: deliberately broken oracles scored 0.72 (ampure with incubation, magnet and drying steps removed, which still passes the end-state checks) and 0.3 (colony PCR reusing one tip across colonies, which trips the cap).

### opentrons-rna-extraction (`tests/grade.py`)

1. **Simulator gate.** `opentrons_simulate` (Opentrons 7.5.0) runs the protocol. If it crashes, the reward is 0.
2. **Run-log checks.** `checks.py` runs 16 deterministic checks on the normalized log, covering volumes, step order, incubation, magnet and drying times, recovery, the 4 °C plate, and fresh tips with no cross-contact.
3. **LLM judge.** `claude-sonnet-5-5` scores 9 rubric items at 0, 0.5 or 1. The reward is the mean of those scores.
4. **Critical cap.** If a critical check fails, the reward is capped at 0.3. The critical checks are sample count, step order, supernatant removal, the two ethanol washes, recovery, and cross-contamination.

During development, the ground truth scored 0.94 and deliberately broken protocols scored 0 to 0.78.

## Results

The Claude Code agent (`-a claude-code`) was run with Harbor in Modal sandboxes (`-e modal`), 1 attempt per task per model (pass@1), on 2026-10-04. All 7 tasks used the common grader. The oracle solutions scored 0.89 to 1.0.

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

What the results show:
- **No trial errored or failed a deterministic or critical check.** All 21 protocols simulated and passed every end-state check, so every point lost came from the judge.
- **The judge separates the models where the old pass/fail grader did not.** Common deductions were: mixing competent cells and having no operator pause in heat-shock; reusing one master-mix tip in colony PCR; recovering 100 µL instead of about 80 µL in RNA extraction; and aspiration heights near the beads in ampure.
- **The judge is sometimes inconsistent.** It marked down fresh-tip-per-well in `a1-a12-100ul` as "wasteful" even though fresh tips are allowed. With 1 attempt and an LLM judge, differences of about 0.1 between models are within noise.

The previous run (local Docker, 6 tasks graded deterministically) gave every model 1.0 on those 6 tasks.

Per-trial tokens, cost, duration and rubric scores are in `results/summary.json`. Each `results/<model>/<task>/` folder holds the graded `protocol.py`, `reward.json` and `judge.json`.

## Notes

- The agent's network is restricted to `api.anthropic.com` and `registry.npmjs.org`.
- The 6 deterministic tasks come from the `feat/ingestion` branch (`tasks/<task>/harbor/`).
- RNA extraction reference protocol: [HULPopentrons/RNA_extraction_OT2opentrons](https://github.com/HULPopentrons/RNA_extraction_OT2opentrons/blob/master/viral_rna_extraction_protocol.py).
