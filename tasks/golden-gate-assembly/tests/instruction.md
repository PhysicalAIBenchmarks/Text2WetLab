# Golden Gate assembly of four four-fragment chromoprotein expression plasmids with AssemblyTron on the OT-2

Assemble four four-fragment chromoprotein expression plasmids using Golden Gate assembly on the OT-2: set up PCRs for each fragment using j5-designed primers at 0.1 µM with 0.5 ng linearized template in 25 µL, run a gradient PCR, then perform DpnI digestion to remove residual template, clean and concentrate the fragments, combine them in volumes proportional to fragment length in a Golden Gate reaction with BsaI-HFv2 and T4 DNA ligase, run the thermocycler assembly program, clean up the assemblies, and transform into competent E. coli TOP10 cells.

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## Source paper

This task comes from AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab robots (Synth. Biol. 2022, doi:10.1093/synbio/ysac032, CC BY). Its text is at **`/data/paper.txt`** (read-only). The deck and quantities above are fixed; use the paper for anything they leave open.

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

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them with the pipettes, in this order.

1. Transfer 106 µL of nuclease-free water from `tubes_50ml_1` (well A1) to `tubes_1_5ml_1` (well D1).
2. Transfer 40 µL of 5X Q5 reaction buffer from `tubes_1_5ml_1` (well A1) to `tubes_1_5ml_1` (well D1).
3. Transfer 4 µL of 10 mM dNTPs from `tubes_1_5ml_1` (well B1) to `tubes_1_5ml_1` (well D1).
4. Transfer 2 µL of Q5 High-Fidelity DNA Polymerase from `tubes_1_5ml_1` (well C1) to `tubes_1_5ml_1` (well D1).
5. Mix `tubes_1_5ml_1` (well D1), 5 cycles at 100 µL.
6. Transfer 19 µL of PCR master mix from `tubes_1_5ml_1` (well D1) to `pcr_plate` wells A1:G1.
7. Transfer 2.5 µL of forward primer (1 µM) from `primer_plate` wells A1, B1, C1, D1, E1, F1, G1 to `pcr_plate` wells A1, B1, C1, D1, E1, F1, G1.
8. Transfer 2.5 µL of reverse primer (1 µM) from `primer_plate` wells A2, B2, C2, D2, E2, F2, G2 to `pcr_plate` wells A1, B1, C1, D1, E1, F1, G1.
9. Transfer 1 µL of linearized template plasmid (0.5 ng/µL) from `template_plate` wells A1, A1, B1, C1, A1, A1, D1 to `pcr_plate` wells A1, B1, C1, D1, E1, F1, G1.
10. Mix `pcr_plate` wells A1:G1, 3 cycles at 15 µL.
11. (Not simulated, record with `protocol.comment`) Seal pcr_plate (or move the PCR tubes) and transfer manually to the Bio-Rad C100 gradient thermocycler. Run: 98°C 30 s; 34 cycles of 98°C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature for each fragment, 72°C extension at the time set by AssemblyTron (about 20-30 s/kb); final extension 72°C 5 min; hold 4°C. Take a sample of each reaction for gel electrophoresis, then return to the OT-2.
12. Transfer 19 µL of nuclease-free water from `tubes_50ml_1` (well A1) to `pcr_plate` wells A1:G1.
13. Transfer 5 µL of rCutSmart Buffer from `tubes_1_5ml_1` (well A2) to `pcr_plate` wells A1:G1.
14. Transfer 1 µL of DpnI from `tubes_1_5ml_1` (well B2) to `pcr_plate` wells A1:G1.
15. Mix `pcr_plate` wells A1:G1, 3 cycles at 30 µL.
16. (Not simulated, record with `protocol.comment`) Incubate pcr_plate A1:G1 at 37°C for 30 min, then 65°C for 20 min (DpnI inactivation) on the thermocycler block.
17. (Not simulated, record with `protocol.comment`) Pause the protocol. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 µL per 50 µL), spin 30 s, wash 2 x 200 µL DNA Wash Buffer (30 s spins), elute in 20 µL water after 1 min at room temperature (30 s spin). Return the eluted fragments to their original positions pcr_plate A1:G1 (fragments 1-7) and resume the protocol.
18. Transfer 7 µL of nuclease-free water from `tubes_50ml_1` (well A1) to `assembly_plate` wells A1, B1, C1, D1.
19. Transfer 2 µL of 10X T4 DNA Ligase Buffer from `tubes_1_5ml_1` (well C2) to `assembly_plate` wells A1, B1, C1, D1.
20. Transfer 3 µL of fragment 2 (backbone) from `pcr_plate` wells B1 to `assembly_plate` wells A1, B1, C1, D1.
21. Transfer 2 µL of fragment 5 (backbone/KanR) from `pcr_plate` wells E1 to `assembly_plate` wells A1, B1, C1, D1.
22. Transfer 3 µL of fragment 6 (backbone) from `pcr_plate` wells F1 to `assembly_plate` wells A1, B1, C1, D1.
23. Transfer 2 µL of chromoprotein fragments 1, 3, 4, 7 from `pcr_plate` wells A1, C1, D1, G1 to `assembly_plate` wells A1, B1, C1, D1.
24. Transfer 1 µL of Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase) from `tubes_1_5ml_1` (well D2) to `assembly_plate` wells A1, B1, C1, D1. Mix 5 times after dispensing.
25. (Not simulated, record with `protocol.comment`) Run Golden Gate program on assembly_plate in the Opentrons thermocycler module: 30 cycles of 37°C 5 min then 16°C 5 min; then 60°C 5 min; hold at 4°C. Lid about 85°C. If no module is available, pause and move reactions to another thermocycler.
26. (Not simulated, record with `protocol.comment`) Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 µL wash) and elute in 10 µL molecular grade water; return the eluates to assembly_plate A1:D1.
27. Transfer 5 µL of purified Golden Gate assembly from `assembly_plate` wells A1, B1, C1, D1 to `cells_plate` wells A1, B1, C1, D1.
28. (Not simulated, record with `protocol.comment`) Measure DNA concentration of the remaining 5 µL of each eluate with a NanoDrop-2000c for CFU/µg calculation.
29. (Not simulated, record with `protocol.comment`) Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42°C for 60 s, then return to ice for about 2 min.
30. Transfer 250 µL of LB + 0.2% (w/v) dextrose from `tubes_15ml_1` (well A1) to `cells_plate` wells A1, B1, C1, D1.
31. (Not simulated, record with `protocol.comment`) Recover cells at 37°C for 60 min with shaking (about 250 rpm).
32. (Not simulated, record with `protocol.comment`) Plate 50-200 µL of each recovery (neat or a 10x dilution, depending on predicted efficiency) onto separate LB agar plates containing kanamycin 50 µg/mL; incubate at 37°C overnight.
33. (Not simulated, record with `protocol.comment`) Manually count colonies per plate and score the fraction showing the expected chromoprotein colour (purple, orange, blue, green); report CFU/µg of DNA plated.

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
