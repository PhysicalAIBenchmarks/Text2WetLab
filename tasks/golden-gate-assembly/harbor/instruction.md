# Golden Gate assembly of four four-fragment chromoprotein expression plasmids with AssemblyTron on the OT-2

Assemble four four-fragment chromoprotein expression plasmids using Golden Gate assembly on the OT-2: set up PCRs for each fragment using j5-designed primers at 0.1 µM with 0.5 ng linearized template in 25 µL, run a gradient PCR, then perform DpnI digestion to remove residual template, clean and concentrate the fragments, combine them in volumes proportional to fragment length in a Golden Gate reaction with BsaI-HFv2 and T4 DNA ligase, run the thermocycler assembly program, clean up the assemblies, and transform into competent E. coli TOP10 cells.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed, because the
grader finds your labware by label and checks that it is the labware named here:

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
