# AMPure XP magnetic bead cleanup of PCR products

Clean up 50 µL PCR products using 0.8× AMPure XP magnetic beads: add 40 µL beads to each well, incubate 5 minutes, engage the magnet and remove the supernatant, wash twice with 200 µL 80% ethanol, dry 5 minutes, then elute in 50 µL nuclease-free water.

Write a Python protocol for a **Hamilton Vantage** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.

## The protocol contract

- Define `async def run(vantage, comment)`. `vantage` is the initialized Hamilton Vantage device object with an empty
  deck. Do not create, connect, configure or initialize the device yourself: skip the "connect to the device" parts
  of the documentation.
- `comment(text)` records a step that cannot be simulated (see below).
- Import only from `unitelabs`, `asyncio`, `__future__`, `collections`, `dataclasses`, `functools`, `itertools`, `math`, `string`, `typing`. From `asyncio`, use only `create_task`, `gather`, `sleep`, `timeout`, `wait`, `wait_for` (and its lock, event, queue and
  exception classes); nothing that starts processes or opens connections.

## The labware

The operator has prepared the labware below. Choose suitable labware classes (and carriers, where the device uses
them) from the SDK's labware library, arrange them on the deck as you see fit, and give each labware **exactly the
identifier listed**: the labware is identified by its identifier.

- `sample_plate`: a 96-well plate (up to 360 µL per well); 96-well plate with 50 µL PCR products on magnetic module.
- `beads_reservoir`: a single-well reservoir (trough); AMPure XP bead suspension (well-mixed before use).
- `ethanol_reservoir`: a single-well reservoir (trough); Freshly prepared 80% ethanol.
- `water_reservoir`: a single-well reservoir (trough); Nuclease-free water for elution.
- `waste`: a waste reservoir (trough); Liquid waste container.
- `elution_plate`: a 96-well plate (up to 360 µL per well); Clean 96-well plate to receive eluate.

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

## What is in the labware at the start

- `sample_plate` wells A1:H12: PCR product, 50 µL each.
- `beads_reservoir`: AMPure XP beads, plenty (more than the protocol needs).
- `ethanol_reservoir`: ethanol 80pct, plenty (more than the protocol needs).
- `water_reservoir`: nuclease free water, plenty (more than the protocol needs).
- `waste` well A1: empty at the start (Liquid waste container).
- `elution_plate`: empty at the start (Clean 96-well plate to receive eluate).

Declare these starting contents on the labware (see the liquids documentation); "plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them in this order.

1. Transfer 40 µL of AMPure XP beads from `beads_reservoir` (well A1) to `sample_plate` wells A1:H12. Mix 10 times after dispensing.
2. (Not simulated, record with `comment`) Incubate sample_plate 5 min at room temperature (beads bind DNA)
3. (Not simulated, record with `comment`) Engage magnetic module; wait 5 min until solution clears
4. Transfer 90 µL of supernatant from `sample_plate` wells A1:H12 to `waste` (well A1).
5. Transfer 200 µL of ethanol 80pct from `ethanol_reservoir` (well A1) to `sample_plate` wells A1:H12.
6. Transfer 200 µL of ethanol waste 1 from `sample_plate` wells A1:H12 to `waste` (well A1).
7. Transfer 200 µL of ethanol 80pct from `ethanol_reservoir` (well A1) to `sample_plate` wells A1:H12.
8. Transfer 200 µL of ethanol waste 2 from `sample_plate` wells A1:H12 to `waste` (well A1).
9. (Not simulated, record with `comment`) Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny
10. (Not simulated, record with `comment`) Disengage magnetic module
11. Transfer 50 µL of nuclease free water from `water_reservoir` (well A1) to `sample_plate` wells A1:H12. Mix 10 times after dispensing.
12. (Not simulated, record with `comment`) Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min
13. Transfer 45 µL of cleaned DNA from `sample_plate` wells A1:H12 to `elution_plate` wells A1:H12.

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Constraints

- Every well must end holding exactly the volume the task implies, and the robot must never pipette without a tip,
  dispense more than it holds, aspirate from an empty well or finish holding a tip.
- Steps that are not pipetting (incubating, magnet, drying, thermocycling) cannot be simulated; record each one with
  `comment('...')` at the point it happens.
- Simulate with: `simulate /app/protocol.py`. It runs your protocol on the simulated Hamilton Vantage and prints what the
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
