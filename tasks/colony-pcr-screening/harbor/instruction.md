# Colony PCR screening with Q5 Hot Start master mix

Screen transformant colonies by PCR: add 18 µL Q5 Hot Start master mix to each well of the PCR plate, then add 1 µL of colony template and 1 µL of the corresponding primer mix per well.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed, because the
grader finds your labware by label and checks that it is the labware named here:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `corning_96_wellplate_360ul_flat` | `colony_plate` |
| 2 | `corning_96_wellplate_360ul_flat` | `pcr_plate` |
| 3 | `nest_1_reservoir_195ml` | `master_mix_reservoir` |
| 4 | `corning_96_wellplate_360ul_flat` | `primer_plate` |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `colony_plate` wells A1:H12: colony template, plenty (more than the protocol needs).
- `master_mix_reservoir`: Q5 master mix 2x, plenty (more than the protocol needs).
- `primer_plate` wells A1:H12: primer pairs, plenty (more than the protocol needs).
- `pcr_plate`: empty at the start (Destination 96-well PCR plate (0.2 mL, semi-skirted)).

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them with the pipettes, in this order.

1. Transfer 18 µL of Q5 master mix 2x from `master_mix_reservoir` (well A1) to `pcr_plate` wells A1:H12.
2. Transfer 1 µL of colony template from `colony_plate` wells A1:H12 to `pcr_plate` wells A1:H12. Mix 3 times after dispensing.
3. Transfer 1 µL of primer pairs from `primer_plate` wells A1:H12 to `pcr_plate` wells A1:H12.
4. (Not simulated, record with `protocol.comment`) Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

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
