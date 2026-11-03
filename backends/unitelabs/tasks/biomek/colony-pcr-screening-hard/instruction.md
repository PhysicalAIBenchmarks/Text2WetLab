# Colony PCR screening on a Beckman Biomek i-Series (from the paper)

Screen 96 transformant colonies by colony PCR on a Beckman Biomek i-Series, following the paper's OT-2 colony PCR workflow and adapting it to the reagents loaded on the deck below (a Q5 Hot Start 2x master mix and a separate primer pair for each colony).

Write a Python protocol for a **Beckman Biomek i-Series** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.

## Source paper

The method is in Slowpoke: Golden Gate cloning and colony PCR on OT-2/Flex (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629, CC BY). Its text is at **`/data/paper.txt`** (read-only). The labware and the starting contents below are fixed; everything else comes from the paper.

## The protocol contract

- Define `async def run(biomek, comment)`. `biomek` is the initialized Beckman Biomek i-Series device object with an empty
  deck. Do not create, connect, configure or initialize the device yourself: skip the "connect to the device" parts
  of the documentation. The deck positions are already configured (plate positions P1.., tip positions TL1.., waste TR1).
- `comment(text)` records a step that cannot be simulated (see below).
- Import only from `unitelabs`, `asyncio`, `__future__`, `collections`, `dataclasses`, `functools`, `itertools`, `math`, `string`, `typing`. From `asyncio`, use only `create_task`, `gather`, `sleep`, `timeout`, `wait`, `wait_for` (and its lock, event, queue and
  exception classes); nothing that starts processes or opens connections.

## The labware

The operator has prepared the labware below. Choose suitable labware classes (and carriers, where the device uses
them) from the SDK's labware library, arrange them on the deck as you see fit, and give each labware **exactly the
identifier listed**: the labware is identified by its identifier.

- `colony_plate`: a 96-well plate (up to 360 µL per well); Colony templates: picked colonies resuspended in nuclease-free water, one per well.
- `pcr_plate`: a 96-well plate (up to 360 µL per well); Destination 96-well PCR plate (0.2 mL, semi-skirted).
- `master_mix_reservoir`: a single-well reservoir (trough); 2× Q5 Hot Start Master Mix (NEB M0494).
- `primer_plate`: a 96-well plate (up to 360 µL per well); Pre-dispensed primer pairs (10 µM each), one column per construct.

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

## What is in the labware at the start

- `colony_plate` wells A1:H12: colony template, plenty (more than the protocol needs).
- `master_mix_reservoir`: Q5 master mix 2x, plenty (more than the protocol needs).
- `primer_plate` wells A1:H12: primer pairs, plenty (more than the protocol needs).
- `pcr_plate`: empty at the start (Destination 96-well PCR plate (0.2 mL, semi-skirted)).

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
- Simulate with: `simulate /app/protocol.py`. It runs your protocol on the simulated Beckman Biomek i-Series and prints what the
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
