# AMPure XP magnetic bead cleanup of PCR products

Clean up 50 µL PCR products using 0.8× AMPure XP magnetic beads: add 40 µL beads to each well, incubate 5 minutes, engage the magnet and remove the supernatant, wash twice with 200 µL 80% ethanol, dry 5 minutes, then elute in 50 µL nuclease-free water.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

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

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them with the pipettes, in this order.

1. Transfer 40 µL of AMPure XP beads from `beads_reservoir` (well A1) to `sample_plate` wells A1:H12. Mix 10 times after dispensing.
2. (Not simulated, record with `protocol.comment`) Incubate sample_plate 5 min at room temperature (beads bind DNA)
3. (Not simulated, record with `protocol.comment`) Engage magnetic module; wait 5 min until solution clears
4. Transfer 90 µL of supernatant from `sample_plate` wells A1:H12 to `waste` (well A1).
5. Transfer 200 µL of ethanol 80pct from `ethanol_reservoir` (well A1) to `sample_plate` wells A1:H12.
6. Transfer 200 µL of ethanol waste 1 from `sample_plate` wells A1:H12 to `waste` (well A1).
7. Transfer 200 µL of ethanol 80pct from `ethanol_reservoir` (well A1) to `sample_plate` wells A1:H12.
8. Transfer 200 µL of ethanol waste 2 from `sample_plate` wells A1:H12 to `waste` (well A1).
9. (Not simulated, record with `protocol.comment`) Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny
10. (Not simulated, record with `protocol.comment`) Disengage magnetic module
11. Transfer 50 µL of nuclease free water from `water_reservoir` (well A1) to `sample_plate` wells A1:H12. Mix 10 times after dispensing.
12. (Not simulated, record with `protocol.comment`) Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min
13. Transfer 45 µL of cleaned DNA from `sample_plate` wells A1:H12 to `elution_plate` wells A1:H12.

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- Simulate with: `opentrons_simulate /app/protocol.py`. Your protocol must simulate without errors.
- No internet access besides the model API.
- Every well and tube must end holding exactly the volume the task implies, and the robot must never pipette
  without a tip, dispense more than it holds, aspirate from an empty well or finish holding a tip.
  `transfer()`, `distribute()` or your own loops are all fine.
- Steps that are not pipetting (incubating, heat shock, thermocycling, sealing, magnet) cannot be simulated; record
  each one with `protocol.comment('...')` at the point it happens.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.
