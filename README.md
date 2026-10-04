# Text2WetLab

**Plain-English lab instruction → Opentrons OT-2 protocol, judged on what the simulated robot does.**

```
paper ──paper2protocol──► IR (Protocol) ──► instruction.md   what a model is given
                            │
                            ├──► ir.json + task.toml         the spec: what must be true at the end
                            └──► 2D / 3D renders             what the IR does, with physics tracking

model's Python ──► opentrons_simulate (7.5.0) ──► events ──► eval/spec_check.py ──► verdict
```

## Layout

```
tasks/<task>/          one flat folder per task, same files everywhere
    instruction.md       the plain-English instruction (public)
    ir.json              the decomposed spec (public)         assumptions.md  what the instruction leaves out
    task.toml            name, source, steps, [checks] free_wells
    solution/ tests/     hidden oracle and grader, never published (only some tasks have them)
paper2protocol/        paper -> experiments -> IR -> instructions (lLegon)
eval/                  spec_check.py (the one checker), runlog.py (simulator -> events),
                       ir_viz.py (2D), ir_mujoco.py (3D + physics tracking)
references/            author-published scripts, comparison only, each with upstream commit + licence
data/pipeline_runs/    paper2protocol output: paper.json, exp<N>/protocol.json (the IR), protocol.txt (the NL)
assets/                examples/ (2D GIFs), examples3d/ (MP4, GIF, 12 frames each)
docs/                  criteria.md (what is judged, with evidence), examples.md (gallery), agent-spec.md
manuscript/            arXiv write-up (placeholder)
scripts/               reproduce.py, criteria_matrix.py, make_provenance_csv.py, deploy_hf.py
PROVENANCE.csv         who first committed every task, reference, output, render and code file, with URLs
```

## Tasks

| Task | Steps | Source | Solution + tests |
|---|---:|---|---|
| `split-200ul-two-wells` | 1 | handwritten | solution, `spec_check` |
| `a1-a12-100ul` | 1 | handwritten | `spec_check` (fixtures) |
| `ampure-bead-cleanup` | 13 | handwritten | none yet |
| `colony-pcr-screening` | 4 | handwritten | none yet |
| `ecoli-heat-shock-transformation` | 4 | handwritten | none yet |
| `golden-gate-assembly` | 33 | paper2protocol (AssemblyTron) | none yet |
| `opentrons-rna-extraction` | n/a | Harbor task (PLOS ONE 2021) | solution, 16 checks, LLM judge |

There is no difficulty tier in the folder names. A task's steps and containers are in its `task.toml`.
The instruction's wording is a separate scale, **V0** fully specified, **V1** volume only,
**V2** intent only (see the HuggingFace card).

## Judging a protocol

```bash
# once: the simulator stack Harbor uses (Opentrons 7.5.0 needs Python 3.10)
uv venv --python 3.10 ~/Desktop/ot-sim-venv
uv pip install --python ~/Desktop/ot-sim-venv/bin/python opentrons==7.5.0 opentrons-shared-data==7.5.0 "pydantic<2"

uv sync --group dev --group eval
uv run python eval/spec_check.py tasks/a1-a12-100ul my_protocol.py
```

A protocol is judged on its end state, not its method, so `transfer()`, `distribute()` and explicit
loops all pass if the plate ends up right. What is checked, and how well, is in
[`docs/criteria.md`](docs/criteria.md).

## Reproduce everything

```bash
OT_VENV=~/Desktop/ot-sim-venv uv run python scripts/reproduce.py --out report.json
```

Five stages (IR integrity, simulating every script, the criteria matrix, renders, provenance) write a
report with no timestamps. Two runs in two fresh clones produced byte-identical reports.
The LLM stages (paper -> IR) are not re-run: they need an API key and the response cache is not committed.

## Pipeline

```bash
uv run paper2protocol list 10.1093/synbio/ysac032         # experiments in a paper
uv run paper2protocol convert 10.1093/synbio/ysac032 -e 2   # -> data/pipeline_runs/<doi>/exp2/
```

See [`docs/paper2protocol-pipeline.md`](docs/paper2protocol-pipeline.md). Needs `ANTHROPIC_API_KEY` in `.env`.

## Related work

[WetRobo](https://arxiv.org/abs/2609.18435) · [ProtoAct](https://arxiv.org/abs/2608.01690) · [OpenLabAI](https://github.com/nygmeta/OpenLabAI)

Dataset: [`EvanOLeary/Text2WetLab`](https://huggingface.co/datasets/EvanOLeary/Text2WetLab)
