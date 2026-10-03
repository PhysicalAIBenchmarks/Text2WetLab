# L1 · 200 µL → two wells

One example, kept in separate stages so each can be scored on its own.

| Stage | File |
|---|---|
| NL input | [`input.nl.txt`](input.nl.txt) |
| What the NL leaves out | [`assumptions.md`](assumptions.md) |
| IR (decomposed steps) | [`ir.json`](ir.json) |
| Python (Opentrons API v2) | [`../../../ref/L1-serial-dilution-200ul-2x100ul/protocol_correct.py`](../../../ref/L1-serial-dilution-200ul-2x100ul/protocol_correct.py) |
| Run log | [`run_log.txt`](run_log.txt) |
| Visualisation | below |

> "Move 200 microlitres from the reservoir into two wells on the plate."

## Visualisation

Reference episode in the MuJoCo OT-2 env (`eval/wetlab_mujoco_env.py`): pick up tip, aspirate 200 µL, dispense 100 µL into A1 and B1, drop tip.

![Reference episode: OT-2 gantry in MuJoCo](../../../assets/episode_mujoco.gif)

[Open the MP4](../../../assets/episode_mujoco.mp4) · [2D env episode](../../../assets/reference_episode.mp4)

## Checking a protocol

```bash
opentrons_simulate protocol.py > run.log      # OT-2 API v2, opentrons<9
python eval/trace_replay.py run.log           # replays the log through WetLabEnv
```

`eval/trace_replay.py` replays the simulator's command log through the 2D env, so checks run on what the robot would do, not on the Python source. On this task it passes T1-T6 with no errors.

It also catches a case the simulator lets through. In `tests/fixtures/L1_a1_a12/bad_protocol.py` (in the GitHub repo) the model aspirates once and then dispenses 12 × 100 µL. `opentrons_simulate` accepts that silently, and the replay flags `overdispense`.
