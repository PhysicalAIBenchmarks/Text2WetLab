# Run events: the backend contract

What a backend hands the grader for one run, and what `spec_check` (`eval/spec_check.py`, behind its backend
contract) reads from it. Upstream's OT-2 backend produces it from the Opentrons simulator's run log
(`eval/runlog.py`); the UniteLabs backend produces it from the liquid-handling SDK's lineage stream
(`ul/lineage_events.py`).

## Run

```json
{"ok": true, "events": [...], "labware": {"<labware name>": "<class or load name>"},
 "geometry": {"<labware name>": {"class": "Cos_96_FB", "family": "plate", "wells": 96, "volumes": [360.0]}},
 "comments": ["..."]}
```

or `{"ok": false, "error": "...", "traceback": "..."}` when the protocol raised.

- **labware name**: `"<identifier> on <position>"`, the identifier the protocol gave the labware and its deck
  position in the device's own terms (`7.0`, `P1`, `4`). Checks match containers by identifier and kind; the position
  is for people, unless a task's `deck.json` pins a `slot`.
- **geometry** (optional): what the labware is, read from the backend's labware model rather than its name: base
  family (`plate`, `trough`, `tube_rack`, `tube`, `tip_rack`), number of separate liquid containers, their distinct
  volumes in µL. Lets a check tell a 96-well plate from a 384-well one, or a reservoir from a deep-well plate.

## Events

One event per channel, in the order the robot did them. A multi-channel action is one event per channel (upstream's
8-channel OT-2 events with `"channels": 8` are the exception the checks still accept).

| kind | fields | meaning |
| --- | --- | --- |
| `pick` | `instrument`, `channels`, `tip` | a channel picks up a tip |
| `drop` | `instrument`, `channels`, `tip` | a channel lets go of its tip: put back in a rack or discarded |
| `aspirate` | `instrument`, `channels`, `volume`, `moved`, `labware`, `well` | liquid from a well into the tip |
| `dispense` | `instrument`, `channels`, `volume`, `moved`, `labware`, `well` | liquid from the tip into a well |
| `mix` | `instrument`, `channels`, `cycles`, `volume`, `labware`, `well` | aspirate and dispense in place, `cycles` times |
| `comment` | `text` | a step the protocol could not run (incubate, centrifuge, ...), where it happened |

- **instrument**: the channel, stable for the run: `channel_<n>` for independent channels, `nozzle_<n>` for a
  multi-channel head. Tip state is kept per instrument.
- **tip**: the identity of the physical tip. A used tip put back and picked up again is the same tip, so what it
  touched before still counts for contamination. Without it, every `pick` counts as a fresh tip.
- **volume**: what the protocol asked for, in µL. **moved**: what the backend's liquid model actually moved (less on
  an over-aspiration, 0 from an empty tip). The checks judge `volume`, so asking for more than a well holds is
  visible even when the model caps it.
- **well**: `A1`-style. A tube or a single-well reservoir is its own labware, well `A1`, or a well of the rack it
  sits in.
- **mix** reaches the checks as one aspirate and one dispense of `volume` in the same well (`check.mix_as_pair`):
  the well must hold the volume, the channel must hold a tip, and a tip that mixed in a destination carries it.
  Further cycles change none of these.

## From the SDK's lineage stream

| lineage operation (`unitelabs.sdk.Operation`) | event |
| --- | --- |
| `PICK_UP_TIP` (tip slot → channel) | `pick` |
| `PUT_DOWN_TIP` (channel → tip slot), `DISCARD_TIP` (channel → `waste`) | `drop` |
| `ASPIRATE` (well → channel), `DISPENSE` (channel → well) | `aspirate`, `dispense`; `volume` = `volume_requested_ul`, else `volume_ul`; `moved` = `volume_ul` |
| `MIX_IN_PLACE` (well → same well) | `mix`, on the instrument holding its `tip` |
| `LOAD_LABWARE`, `UNLOAD_LABWARE`, `SEED_CONTAINER` | none (the checks take the deck from the task; kept in the stream) |
| `MOVE_LABWARE`, `PICK_UP_TOOL`, `PUT_DOWN_TOOL`, ... | none (the benchmark takes the gripper away) |
| any operation with type `error` | none; kept with the run as `lineage_errors` (the run raised) |
| `SEED_CONTAINER` with type `audit` | none; kept with the run as `lineage_audit` (a volume corrected outside a robot action, e.g. liquid the protocol removed through the liquid model) |

A channel is `channel:<actor>:<module>:<n>` (`unitelabs.sdk.automate.lineage.channel`): `channel_<n>` on the
`pipettes` module, `nozzle_<n>` on a `pipette_head` (EVO's `mca` and the Bravo and Biomek heads). The SDK names wells
`<labware>:<address>` and tubes and trough compartments by their own identifier; the runner exports a map from those
to (labware name, well) so the adapter needs no SDK. `ul/lineage_fixtures.py` pins the stream and the adapter's output
for every reference protocol and checks every event, of every type, against the SDK's payload contract
(`unitelabs.sdk.automate.lineage.validate_event`).

The labware loads and seeds come from the labware model's notifications (`unitelabs.labware.events`), so the gate
refuses that module along with `unitelabs.sdk` and the lineage package.
