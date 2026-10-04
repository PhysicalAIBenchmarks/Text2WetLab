# Automated heat shock transformation with APEX on the OT-2 thermocycler (from the paper)

Implement **APEX Protocol 1, the heat shock transformation**, as described in the paper, for **8 plasmids** on the
deck below. Use the transformation volumes the paper selected for its automated runs and run every temperature step on
the thermocycler module.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## Source paper

The method is in APEX: Automated Protein EXpression in Escherichia coli (Kasprzyk, Herrera and Stracquadanio,
bioRxiv 2024, doi:10.1101/2024.08.13.607171). Its text is at **`/data/paper.txt`** (read-only). The deck and the
starting contents below are fixed; everything else comes from the paper.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
tc = protocol.load_module('thermocycler')
tc.load_labware('<load name>', label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `biorad_96_wellplate_200ul_pcr` | `plasmid_plate` |
| 2 | `nest_12_reservoir_15ml` | `soc_reservoir` |
| 7, 8, 10, 11 | Thermocycler Module GEN1 (`'thermocycler'`) holding `biorad_96_wellplate_200ul_pcr` | `transformation_plate` |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 4) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 5). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `plasmid_plate` wells A1, B1, C1, D1, E1, F1, G1, H1: plasmids pEX01–pEX08 (in that order, 1.5 × 10⁻⁴ pmol/µL), 10 µL each.
- `transformation_plate` wells A1, B1, C1, D1, E1, F1, G1, H1: chemically competent E. coli DH5α (made with the paper's
  method), 10 µL each, loaded by the operator onto the pre-chilled thermocycler block. Transformation *n* uses plasmid
  well *n* and cell well *n* (A1 to A1, and so on).
- `soc_reservoir` well A1: SOC medium, plenty (more than the protocol needs).

## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- No internet access besides the model API.
- The robot must never pipette without a tip, dispense more than it holds, aspirate from an empty well or finish
  holding a tip. `transfer()`, `distribute()` or your own loops are all fine.
- Work out the volumes, step order, times and temperatures from the paper. Where the paper leaves something open,
  make a sound choice and say so in a comment.
- Steps after recovery (spotting on agar, Protocol 2) are out of scope.
- Do not read or write outside `/app`, and do not modify the installed `opentrons` package.
