# Examples

Every example is drawn through the same interface. Anything that fits the `Protocol` IR
schema (`paper2protocol/models.py`) renders with one command:

```bash
python eval/ir_viz.py <ir.json> -o out.gif      # one IR
python eval/ir_viz.py --all                     # every tasks/**/ir.json and out/*/exp*/protocol.json
```

One panel per container (96-well plates as 8x12 grids, tubes and reservoirs as bars). Orange
border = source of the step, cyan = destination, red text = the checker flagged the step.
Volumes follow `paper2protocol/check.py`.

Robot-level runs (an `opentrons_simulate` log) go through `eval/trace_replay.py`, which replays
the log through the 2D env, so tip and pipette state show up too.

## L1 - hand-written tasks

### 200 µL into two wells
> "Move 200 microlitres from the reservoir into two wells on the plate."

![IR view](../assets/examples/L1-serial-dilution-200ul.gif)

Robot replay: ![replay](../assets/examples/replay-L1-serial-dilution-200ul.gif)

3D: ![MuJoCo](../assets/episode_mujoco.gif)

### 100 µL into A1-A12
> "Add 100 uL of liquid from a 1-well reservoir to wells A1->A12 in a 96-well plate."

![IR view](../assets/examples/L1-a1-a12-100ul.gif)

12 x 100 µL is more than one pipette load, so a correct run re-aspirates partway.

Correct run (re-aspirates, 1200 µL ends up in A1-A12):
![good](../assets/examples/replay-L1-a1-a12-100ul-good.gif)

Bad run (one aspirate, then 12 dispenses). `opentrons_simulate` accepts it silently; the replay
flags `overdispense` and only three wells fill:
![bad](../assets/examples/replay-L1-a1-a12-100ul-bad.gif)

## Papers - `paper2protocol` output

| Source | Steps | Containers | View |
|---|---|---|---|
| Yeast engineering + LC-HRMS (bioRxiv 10.1101/2024.09.14.613006, exp 1) | 56 | 30 | ![](../assets/examples/paper-10_1101_2024_09_14_613006-exp1.gif) |
| SARS-CoV-2 RNA extraction + RT-qPCR (PLOS ONE 10.1371/journal.pone.0246302, exp 2) | 91 | 44 | ![](../assets/examples/paper-10_1371_journal_pone_0246302-exp2.gif) |
| HRE-luciferase assay after KDM2B knockdown (bioRxiv 10.64898/2026.03.26.714448, exp 1) | 53 | 23 | ![](../assets/examples/paper-10_64898_2026_03_26_714448-exp1.gif) |

## What the IR view does not show
Tips, pipette capacity, deck slots and heights. Those need the robot layer (Python or an
Opentrons log), so use `trace_replay.py` for them.
Manual steps (incubate, centrifuge) appear as a caption only. Mixing does not change volumes.
