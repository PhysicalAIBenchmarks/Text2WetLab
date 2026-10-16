# Golden Gate assembly of four chromoprotein plasmids with AssemblyTron on a Tecan Freedom EVO (from the paper)

Use the AssemblyTron Golden Gate workflow described in the paper to build four four-fragment chromoprotein expression plasmids on a Tecan Freedom EVO, from the PCR of each fragment through to transformation into E. coli TOP10.

Write a Python protocol for a **Tecan Freedom EVO** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.

## Source paper

The method is in AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab robots (Synth. Biol. 2022, doi:10.1093/synbio/ysac032, CC BY). Its text is at **`/data/paper.txt`** (read-only). The labware, the starting contents and the j5/AssemblyTron design below are fixed; everything else comes from the paper.

## The protocol contract

- Define `async def run(evo, comment)`. `evo` is the initialized Tecan Freedom EVO device object with an empty
  deck. Do not create, connect, configure or initialize the device yourself: skip the "connect to the device" parts
  of the documentation. `mca_discard_location` is already configured, so `discard_tips()` works.
- `comment(text)` records a step that cannot be simulated (see below).
- Import only from `unitelabs`, `asyncio`, `__future__`, `collections`, `dataclasses`, `functools`, `itertools`, `math`, `string`, `typing`. From `asyncio`, use only `create_task`, `gather`, `sleep`, `timeout`, `wait`, `wait_for` (and its lock, event, queue and
  exception classes); nothing that starts processes or opens connections.

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

## The labware

The operator has prepared the labware below. Choose suitable labware classes (and carriers, where the device uses
them) from the SDK's labware library, arrange them on the deck as you see fit, and give each labware **exactly the
identifier listed**: the labware is identified by its identifier.

- `primer_plate`: a 96-well plate (up to 360 µL per well); j5-designed primers at 1 µM working stock: forward primers in A1:G1, reverse primers in A2:G2 (fragments 1-7).
- `template_plate`: a 96-well plate (up to 360 µL per well); Linearized template plasmids diluted to 0.5 ng/µL.
- `pcr_plate`: a 96-well plate (up to 360 µL per well); PCR / DpnI / fragment plate (stands in for 100 µL PCR tubes in the thermocycler block); column 1 wells A1:G1 = fragments 1-7.
- `assembly_plate`: a 96-well plate (up to 360 µL per well); Golden Gate reactions A1:D1.
- `cells_plate`: a 96-well plate (up to 360 µL per well); Chemically competent E. coli TOP10 for transformation, A1:D1.
- `tubes_50ml_1`: a rack of tubes (50 mL tube) holding:
  - `water` at A1: Nuclease-free molecular grade water
- `tubes_1_5ml_1`: a rack of tubes (1.5 mL tube) holding:
  - `q5_buffer` at A1: 5X Q5 reaction buffer (NEB)
  - `dntp` at B1: 10 mM dNTP mix
  - `q5_pol` at C1: Q5 High-Fidelity DNA Polymerase (NEB)
  - `pcr_mm` at D1: PCR master mix (buffer, dNTPs, polymerase, water) for 8 reactions
  - `rcutsmart` at A2: rCutSmart Buffer (NEB)
  - `dpni` at B2: DpnI (NEB)
  - `t4_buffer` at C2: 10X T4 DNA Ligase Buffer
  - `gg_enzyme` at D2: Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase)
- `tubes_15ml_1`: a rack of tubes (15 mL tube) holding:
  - `lb_dextrose` at A1: LB + 0.2% (w/v) dextrose (LB with catabolite repression) recovery medium

  Tubes may also be provided as labware of their own (a tube in a carrier's tube spot): then give each tube its own name as identifier (e.g. `water`) instead of a rack identifier and well.

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

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
- `assembly_plate`: empty at the start (Golden Gate reactions A1:D1).

Declare these starting contents on the labware (see the liquids documentation); "plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.

## The protocol to implement

There are no listed steps: work them out from the paper and the design above.

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Constraints

- Work out the volumes, step order, times and temperatures from the paper. Where the paper leaves something open, make a sound choice and say so in a comment.
- Record each step the robot can't carry out itself (for example sealing, off-deck incubation or thermocycling, column clean-ups) with `comment('...')` at the point it happens.
- Every well must end holding exactly the volume the task implies, and the robot must never pipette without a tip,
  dispense more than it holds, aspirate from an empty well or finish holding a tip.
- Steps that are not pipetting (incubating, magnet, drying, thermocycling) cannot be simulated; record each one with
  `comment('...')` at the point it happens.
- Simulate with: `simulate /app/protocol.py`. It runs your protocol on the simulated Tecan Freedom EVO and prints what the
  robot did, or the error. Your protocol must run without errors. A completed run does not mean the protocol is
  correct: check yourself that it does exactly what the brief asks, and that the real instrument could do it.
- The SDK documentation is under `/docs/content/`: start with `01.get-started/`, `04.concepts/03.operate/`,
  `06.liquid-handling-and-robots/` and `07.labware/`. The installed SDK source is under
  `/opt/ul/lib/python3.13/site-packages/unitelabs/`. No internet access besides the model API.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.

## If this protocol cannot be run on this device

Not every protocol suits every instrument: the pipetting hardware may make a step impossible to carry out as
specified (not merely inconvenient). If that is the case here, do **not** write `/app/protocol.py`. Instead write
**`/app/INFEASIBLE.md`** naming the step and the hardware limitation that rules it out. A protocol that runs in the
simulator but could not do what the task asks on the real instrument is wrong; so is declaring a feasible protocol
infeasible.
