# 100 µL from a 1-well reservoir to wells A1 to A12

Add 100 uL of liquid from a 1-well reservoir to wells A1->A12 in a 96-well plate.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed, because the
grader finds your labware by label and checks that it is the labware named here:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `nest_1_reservoir_195ml` | `reservoir` |
| 2 | `corning_96_wellplate_360ul_flat` | `plate` |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `reservoir`: liquid, 10000 µL each.
- `plate`: empty at the start (96-well destination plate).

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
