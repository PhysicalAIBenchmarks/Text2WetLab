# Golden Gate assembly of four chromoprotein plasmids with AssemblyTron on the OT-2 (from the paper)

Use the AssemblyTron Golden Gate workflow described in the paper to build four four-fragment chromoprotein expression plasmids on the OT-2, from the PCR of each fragment through to transformation into E. coli TOP10.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## Source paper

The method is in AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab robots (Synth. Biol. 2022, doi:10.1093/synbio/ysac032, CC BY). Its text is at **`/data/paper.txt`** (read-only). The deck, the starting contents and the j5/AssemblyTron design below are fixed; everything else comes from the paper.


## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
| 1 | `opentrons_6_tuberack_falcon_50ml_conical` | `tubes_50ml_1` |
| 2 | `opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap` | `tubes_1_5ml_1` |
| 3 | `corning_96_wellplate_360ul_flat` | `primer_plate` |
| 4 | `corning_96_wellplate_360ul_flat` | `template_plate` |
| 5 | `corning_96_wellplate_360ul_flat` | `pcr_plate` |
| 6 | `corning_96_wellplate_360ul_flat` | `assembly_plate` |
| 7 | `corning_96_wellplate_360ul_flat` | `cells_plate` |
| 8 | `opentrons_15_tuberack_falcon_15ml_conical` | `tubes_15ml_1` |

Tubes sit in the racks like this:

| Tube | Rack label | Well |
|---|---|---|
| water | `tubes_50ml_1` | A1 |
| q5_buffer | `tubes_1_5ml_1` | A1 |
| dntp | `tubes_1_5ml_1` | B1 |
| q5_pol | `tubes_1_5ml_1` | C1 |
| pcr_mm | `tubes_1_5ml_1` | D1 |
| rcutsmart | `tubes_1_5ml_1` | A2 |
| dpni | `tubes_1_5ml_1` | B2 |
| t4_buffer | `tubes_1_5ml_1` | C2 |
| gg_enzyme | `tubes_1_5ml_1` | D2 |
| lb_dextrose | `tubes_15ml_1` | A1 |

Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

- `tubes_50ml_1` well A1: nuclease-free water, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well A1: 5X Q5 reaction buffer, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well B1: 10 mM dNTPs, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well C1: Q5 High-Fidelity DNA Polymerase, plenty (more than the protocol needs).
- `primer_plate` wells A1, B1, C1, D1, E1, F1, G1: forward primers for fragments 1-7 (1 µM), 50 µL each.
- `primer_plate` wells A2, B2, C2, D2, E2, F2, G2: reverse primers for fragments 1-7 (1 µM), 50 µL each.
- `template_plate` wells A1: pIDMv5K-J23100-tsPurple-B1006 linearized, 0.5 ng/µL, 20 µL each.
- `template_plate` wells B1: pIDMv5K-J23100-YukonOFP-B1006 linearized, 0.5 ng/µL, 20 µL each.
- `template_plate` wells C1: pIDMv5K-J23100-aeBlue-B1006 linearized, 0.5 ng/µL, 20 µL each.
- `template_plate` wells D1: pIDMv5K-J23100-fuGFP-B1006 linearized, 0.5 ng/µL, 20 µL each.
- `tubes_1_5ml_1` well A2: rCutSmart Buffer, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well B2: DpnI, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well C2: 10X T4 DNA Ligase Buffer, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well D2: Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase), plenty (more than the protocol needs).
- `cells_plate` wells A1, B1, C1, D1: E. coli TOP10 chemically competent cells (Hanahan method), 50 µL each.
- `tubes_15ml_1` well A1: LB + 0.2% (w/v) dextrose, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well D1: empty at the start (PCR master mix (buffer, dNTPs, polymerase, water) for 8 reactions).
- `pcr_plate`: empty at the start (PCR / DpnI / fragment plate (stands in for 100 µL PCR tubes in the thermocycler block); column 1 wells A1:G1 = fragments 1-7).
- `assembly_plate`: empty at the start (Golden Gate reactions A1:D1 (on Opentrons thermocycler module)).


## The j5 / AssemblyTron design (fixed)

AssemblyTron has already turned the j5 design into these fragment and assembly tables.

| Fragment | PCR well (`pcr_plate`) | Forward primer (`primer_plate`) | Reverse primer (`primer_plate`) | Template (`template_plate`) |
|---|---|---|---|---|
| 1 (tsPurple chromoprotein) | A1 | A1 | A2 | A1 |
| 2 (backbone) | B1 | B1 | B2 | A1 |
| 3 (YukonOFP chromoprotein) | C1 | C1 | C2 | B1 |
| 4 (aeBlue chromoprotein) | D1 | D1 | D2 | C1 |
| 5 (backbone / KanR) | E1 | E1 | E2 | A1 |
| 6 (backbone) | F1 | F1 | F2 | A1 |
| 7 (fuGFP chromoprotein) | G1 | G1 | G2 | D1 |

| Assembly (`assembly_plate` well) | Fragments, with the volume of each cleaned fragment (proportional to fragment length) |
|---|---|
| A1 (tsPurple) | fragment 2: 3 µL, fragment 5: 2 µL, fragment 6: 3 µL, fragment 1: 2 µL |
| B1 (YukonOFP) | fragment 2: 3 µL, fragment 5: 2 µL, fragment 6: 3 µL, fragment 3: 2 µL |
| C1 (aeBlue) | fragment 2: 3 µL, fragment 5: 2 µL, fragment 6: 3 µL, fragment 4: 2 µL |
| D1 (fuGFP) | fragment 2: 3 µL, fragment 5: 2 µL, fragment 6: 3 µL, fragment 7: 2 µL |

Each Golden Gate reaction is 20 µL. The cleaned fragments go back into their PCR wells (`pcr_plate` A1:G1) before assembly.

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
