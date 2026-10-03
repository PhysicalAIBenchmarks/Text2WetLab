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
ref/          Reference implementations (ground truth protocols)
tasks/        Benchmark tasks — one folder per task: input.nl.txt, assumptions.md, ir.json
  L1/         Layer 1: liquid handling (aspirate / dispense / tip management)
  L2/         Layer 2: fine-grained (volumes, concentrations, scheduling)
eval/         Evaluation harness (PyLabRobot + MuJoCo 3D sim + Gymnasium env)
  ot2.xml             MuJoCo MJCF model of the OT-2 Cartesian gantry
  wetlab_mujoco_env.py  Headless 3D sim — recordable, reward-shaped on T1–T6
  wetlab_gym.py         Lightweight Gymnasium env (no MuJoCo dep)
docs/
  agent-spec.md       Pipeline spec, acceptance criteria AC1–AC7, risk register R1–R15
  leaderboard.html    Self-contained leaderboard — runs eval entirely in-browser
paper/        arXiv write-up (placeholder)
scripts/      deploy_hf.py (HF upload; run by CI on push to main)
assets/
  episode_mujoco.mp4  Reference L1 episode (3D MuJoCo)
  episode_mujoco.gif  Animated GIF for README embed
  urdf/               Robot URDFs for 3D simulation
  stl/                Labware STL/OBJ models
```

## Layers

| Layer | Description | Target platform |
|---|---|---|
| L1 | Liquid handling primitives — tip management, aspirate/dispense, volume flow | Opentrons OT-2 API v2 |
| L2 | Fine-grained — concentration, dilution series, multi-instrument scheduling | Opentrons OT-2 / Flex |

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
git clone https://github.com/Tyronita/Text2WetLab
cd Text2WetLab
uv pip install pylabrobot>=0.2.2
uv run python eval/run_eval.py tasks/L1/
```
