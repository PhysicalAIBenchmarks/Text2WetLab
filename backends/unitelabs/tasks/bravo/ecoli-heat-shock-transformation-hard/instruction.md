# Automated heat shock transformation with APEX on an Agilent Bravo thermocycler (from the paper)

Implement **APEX Protocol 1, the heat shock transformation**, as described in the paper, for **8 plasmids** on the
deck below. Use the transformation volumes the paper selected for its automated runs and run every temperature step on
the thermocycler module.

Write a Python protocol for an **Agilent Bravo** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.

## Source paper

The method is in APEX: Automated Protein EXpression in Escherichia coli (Kasprzyk, Herrera and Stracquadanio,
bioRxiv 2024, doi:10.1101/2024.08.13.607171). Its text is at **`/data/paper.txt`** (read-only). The deck and the
starting contents below are fixed; everything else comes from the paper.

## The protocol contract

- Define `async def run(bravo, comment)`. `bravo` is the initialized Agilent Bravo device object with an empty
  deck. Do not create, connect, configure or initialize the device yourself: skip the "connect to the device" parts
  of the documentation.
- `comment(text)` records a step that cannot be simulated (see below).
- Import only from `unitelabs`, `asyncio`, `__future__`, `collections`, `dataclasses`, `functools`, `itertools`, `math`, `string`, `typing`. From `asyncio`, use only `create_task`, `gather`, `sleep`, `timeout`, `wait`, `wait_for` (and its lock, event, queue and
  exception classes); nothing that starts processes or opens connections.

## The labware

The operator has prepared the labware below. Choose suitable labware classes (and carriers, where the device uses
them) from the SDK's labware library, arrange them on the deck as you see fit, and give each labware **exactly the
identifier listed**: the labware is identified by its identifier.

- `plasmid_plate`: a 96-well plate (up to 360 µL per well); Plasmids pEX01-pEX08, one per well A1:H1.
- `transformation_plate`: a 96-well plate (up to 360 µL per well); Competent DH5alpha cells, 10 uL per well A1:H1.
- `soc_reservoir`: a single-well reservoir (trough); SOC medium.

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

## What is in the labware at the start

- `plasmid_plate` wells A1:H1: plasmid DNA, 10 µL each.
- `transformation_plate` wells A1:H1: competent cells, 10 µL each.
- `soc_reservoir`: SOC medium, plenty (more than the protocol needs).

Declare these starting contents on the labware (see the liquids documentation); "plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.

## The protocol to implement

There are no listed steps: work them out from the paper and the design above.

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Constraints

- Work out the volumes, step order, times and temperatures from the paper. Where the paper leaves something open, make a sound choice and say so in a comment.
- Steps after recovery (spotting on agar, Protocol 2) are out of scope.
- Every well must end holding exactly the volume the task implies, and the robot must never pipette without a tip,
  dispense more than it holds, aspirate from an empty well or finish holding a tip.
- Steps that are not pipetting (incubating, magnet, drying, thermocycling) cannot be simulated; record each one with
  `comment('...')` at the point it happens.
- Simulate with: `simulate /app/protocol.py`. It runs your protocol on the simulated Agilent Bravo and prints what the
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
