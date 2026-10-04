# AMPure XP magnetic bead cleanup of PCR products

Clean up 50 µL PCR products using 0.8× AMPure XP magnetic beads: add 40 µL beads to each well, incubate 5 minutes, engage the magnet and remove the supernatant, wash twice with 200 µL 80% ethanol, dry 5 minutes, then elute in 50 µL nuclease-free water.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed, because the
grader finds your labware by label and checks that it is the labware named here:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `corning_96_wellplate_360ul_flat` | `sample_plate` |
| 2 | `nest_1_reservoir_195ml` | `beads_reservoir` |
| 3 | `nest_1_reservoir_195ml` | `ethanol_reservoir` |
| 4 | `nest_1_reservoir_195ml` | `water_reservoir` |
| 5 | `nest_1_reservoir_195ml` | `waste` |
| 6 | `corning_96_wellplate_360ul_flat` | `elution_plate` |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `sample_plate` wells A1:H12: PCR product, 50 µL each.
- `beads_reservoir`: AMPure XP beads, plenty (more than the protocol needs).
- `ethanol_reservoir`: ethanol 80pct, plenty (more than the protocol needs).
- `water_reservoir`: nuclease free water, plenty (more than the protocol needs).
- `waste` well A1: empty at the start (Liquid waste container).
- `elution_plate`: empty at the start (Clean 96-well plate to receive eluate).

## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- Simulate with: `opentrons_simulate /app/protocol.py`. Your protocol must simulate without errors.
- No internet access besides the model API.
- Grading is by simulation, not by reading your code. Every well and tube must end holding exactly the volume the
  task implies, and the robot must never pipette without a tip, dispense more than it holds, aspirate from an empty
  well or finish holding a tip. `transfer()`, `distribute()` or your own loops are all fine.
- Steps that are not pipetting (incubating, heat shock, thermocycling, sealing, magnet) cannot be simulated and are
  not graded; record them with `protocol.comment('...')` if you want them in the log.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.
