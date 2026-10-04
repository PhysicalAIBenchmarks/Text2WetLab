# E. coli heat shock transformation with SOC recovery

Transform competent E. coli with 2 µL plasmid DNA per tube, heat shock at 42°C for 45 seconds, then add 250 µL SOC medium to each tube.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `corning_96_wellplate_360ul_flat` | `plasmid_plate` |
| 2 | `opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap` | `tubes_1_5ml_1` |
| 3 | `nest_1_reservoir_195ml` | `soc_reservoir` |

Tubes sit in the racks like this:

| Tube | Rack label | Well |
|---|---|---|
| cells_rack | `tubes_1_5ml_1` | A1 |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `plasmid_plate` wells A1: plasmid DNA, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well A1: competent cells, 50 µL each.
- `soc_reservoir`: SOC medium, plenty (more than the protocol needs).

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them with the pipettes, in this order.

1. Transfer 2 µL of plasmid DNA from `plasmid_plate` wells A1 to `tubes_1_5ml_1` (well A1).
2. (Not simulated, record with `protocol.comment`) Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min
3. Transfer 250 µL of SOC medium from `soc_reservoir` (well A1) to `tubes_1_5ml_1` (well A1).
4. (Not simulated, record with `protocol.comment`) Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery

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
