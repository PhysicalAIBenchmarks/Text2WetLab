# Text2WetLab

**Natural language → wet lab robot protocol benchmark**

Given a plain-English instruction, can a language model generate a correct, safe, executable liquid-handling protocol?

## Visualisation

L1 reference protocol — OT-2 Cartesian gantry sim (MuJoCo 3.x, headless, recordable):

![L1 serial dilution — MuJoCo 3D sim](assets/episode_mujoco.gif)

*[Download MP4](assets/episode_mujoco.mp4)* · Tiprack (amber) → aspirate from trough (green) → dispense 2×100µL into plate (purple) → drop tip. T1–T6 criteria strip bottom-left.

**[Live leaderboard demo →](docs/leaderboard.html)** — paste an action sequence, evaluate T1–T6 in-browser, see ranked results.

---

## Structure

```
paper2protocol/  Paper -> experiments -> IR (Protocol) -> plain-English instructions (lLegon)
tasks/           Benchmark tasks, one folder each, grouped by layer (see below)
  L1/<task>/     input.nl.txt  ir.json  assumptions.md  [solution/ tests/]
  L2/<task>/     same; the Harbor task also has instruction.md task.toml environment/
                 solution/ and tests/ are hidden grader files and are never published
eval/            Scoring and visualisation: ir_viz.py (2D), ir_mujoco.py (3D + physics tracking),
                 trace_replay.py (opentrons_simulate log -> WetLabEnv), wetlab_gym.py, wetlab_mujoco_env.py
ref/             Author-published scripts for comparison only; each has a README with upstream
                 commit and licence. Never read by the pipeline, never published
out/             Generated paper2protocol output only (paper.json, exp<N>/protocol.json ...)
assets/          examples/ (2D GIFs), examples3d/ (3D MP4/GIF/frames)
docs/            examples.md (gallery), agent-spec.md, paper2protocol-pipeline.md, leaderboard.html
manuscript/      arXiv write-up (placeholder)
scripts/         deploy_hf.py (allowlist upload), make_provenance_csv.py
PROVENANCE.csv   Who first committed each task / reference / output / code file, with URLs
tests/           pytest suite
```

## Layers

| Layer | Description | Target platform |
|---|---|---|
| L1 | Liquid handling primitives — tip management, aspirate/dispense, volume flow | Opentrons OT-2 API v2 |
| L2 | Fine-grained — concentration, dilution series, multi-instrument scheduling | Opentrons OT-2 / Flex |

### L1 / L2 and V0 / V1 / V2

Two separate scales, which earlier docs both called "L":

- **Layer (L1, L2)** is how complex the *task* is. It names the folder under `tasks/`.
- **Vagueness (V0, V1, V2)** is how much the plain-English *instruction* leaves out:
  V0 fully specified, V1 volume only, V2 intent only. See the HuggingFace card.

## Evaluation criteria (all 6 must pass)

| # | Criterion | Caught by |
|---|---|---|
| T1 | Pick up tip before any aspirate | PyLabRobot `NoTipError` |
| T2 | Aspirate correct volume | Volume tracker assertion |
| T3 | Two dispenses from single tip load | Volume tracker assertion |
| T4 | Drop tip when finished | Tip state assertion |
| T5 | No overdispense (dispense > aspirated) | Volume tracker assertion |
| T6 | No over-capacity (aspirate > pipette max) | Volume tracker assertion |

## HuggingFace

Dataset: `EvanOLeary/Text2WetLab`  
Weights / model outputs: to be added post-evaluation.

## Simulation backends

- **PyLabRobot 0.2.2** — hardware-agnostic, catches T1 natively; T2–T6 via manual assertions
- **Opentrons API v2 / opentrons_simulate** — catches all 6 natively
- **3D visualisation** — URDF + STL assets in `assets/` (see below)

## Equipment 3D models

See [`assets/`](assets/) for URDF and STL files used in simulation.
Sources and licenses documented in [`assets/SOURCES.md`](assets/SOURCES.md).

## Related work

- [WetRobo](https://arxiv.org/abs/2609.18435) — NL → wet lab action benchmark (2025)
- [ProtoAct](https://arxiv.org/abs/2608.01690) — protocol-level action grounding (2025)
- [OpenLabAI](https://github.com/nygmeta/OpenLabAI) — Opentrons + PyLabRobot integration

## Setup

```bash
git clone https://github.com/PhysicalAIBenchmarks/Text2WetLab
cd Text2WetLab
uv pip install pylabrobot>=0.2.2
uv run python eval/run_eval.py tasks/L1/
```
