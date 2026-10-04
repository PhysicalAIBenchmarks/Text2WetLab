# Colony PCR screening on the OT-2 (from the paper)

Screen 96 transformant colonies by colony PCR on the OT-2, following the paper's OT-2 colony PCR workflow and adapting it to the reagents loaded on the deck below (a Q5 Hot Start 2x master mix and a separate primer pair for each colony).

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## Source paper

The method is in Slowpoke: Golden Gate cloning and colony PCR on OT-2/Flex (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629, CC BY). Its text is at **`/data/paper.txt`** (read-only). The deck and the starting contents below are fixed; everything else comes from the paper.


## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

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


## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- No internet access besides the model API.
- The robot must never pipette without a tip, dispense more than it holds, aspirate from an empty well or finish
  holding a tip. `transfer()`, `distribute()` or your own loops are all fine.
- Work out the volumes, step order, times and temperatures from the paper. Where the paper leaves something open,
  make a sound choice and say so in a comment.
- Record each step the robot can't carry out itself (for example sealing, off-deck incubation or thermocycling, column
  clean-ups) with `protocol.comment('...')` at the point it happens.
- Do not read or write outside `/app`, and do not modify the installed `opentrons` package.
