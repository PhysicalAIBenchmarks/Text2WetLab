# E. coli heat shock transformation with SOC recovery

Transform competent E. coli with 2 µL plasmid DNA per tube, heat shock at 42°C for 45 seconds, then add 250 µL SOC medium to each tube.

Write a Python protocol for a **Beckman Biomek i-Series** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.

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

- `plasmid_plate`: a 96-well plate (up to 360 µL per well); Source plate holding plasmid DNA stocks (one per well).
- `soc_reservoir`: a single-well reservoir (trough); SOC medium pre-warmed to room temperature.
- `tubes_1_5ml_1`: a rack of tubes (1.5 mL tube) holding:
  - `cells_rack` at A1: 50 µL competent E. coli aliquots on ice, one tube per transformation

  Tubes may also be provided as labware of their own (a tube in a carrier's tube spot): then give each tube its own name as identifier (e.g. `water`) instead of a rack identifier and well.

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

## What is in the labware at the start

- `plasmid_plate` wells A1: plasmid DNA, plenty (more than the protocol needs).
- `tubes_1_5ml_1` well A1: competent cells, 50 µL each.
- `soc_reservoir`: SOC medium, plenty (more than the protocol needs).

Declare these starting contents on the labware (see the liquids documentation); "plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them in this order.

1. Transfer 2 µL of plasmid DNA from `plasmid_plate` wells A1 to `tubes_1_5ml_1` (well A1).
2. (Not simulated, record with `comment`) Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min
3. Transfer 250 µL of SOC medium from `soc_reservoir` (well A1) to `tubes_1_5ml_1` (well A1).
4. (Not simulated, record with `comment`) Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Constraints

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
