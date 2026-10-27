"""Turn the SDK's lineage stream into the run-log events spec_check reads: the backend adapter.

The liquid-handling SDK records what a liquid handler physically did as events on the active run context
(`unitelabs.sdk.Audit`, payload contract in `unitelabs.sdk.automate.lineage`): tip pick-ups, put-downs and discards,
aspirates, dispenses and in-place mixes, one event per channel, with the physical tip, the volume requested and the
volume the liquid model moved; and, from the labware model, labware loaded and unloaded and the liquid seeded into
containers. runner.py captures that stream with `Audit.capture()`; this module only reads plain dicts, so it runs
without the SDK.

    pick_up_tip                  -> {"kind": "pick", "instrument", "channels": 1, "tip"}
    put_down_tip, discard_tip    -> {"kind": "drop", "instrument", "channels": 1, "tip"}
    aspirate, dispense           -> {"kind", "instrument", "channels": 1, "volume", "moved", "well", "labware"}
    mix_in_place                 -> {"kind": "mix", "instrument", "channels": 1, "cycles", "volume", "well", "labware"}

`volume` is what the protocol asked for (`volume_requested_ul`; absent when it left the volume to the SDK, which then
moves what fits, so `volume_ul` stands in), `moved` what the liquid model moved (`volume_ul`). Labware loads, unloads,
seeds and the other operations are not run-log events. Events of type "error" (a channel that failed an operation)
are returned separately: the run raised, so they are for the record. Events of type "audit" (a container's known
volume corrected outside a robot action) are not actions and are skipped; runner.py keeps them with the run.

Entities: a channel is `channel:<actor>:<module>:<n>`; it becomes the instrument `channel_<n>` on the `pipettes`
module and `nozzle_<n>` on a `pipette_head`. A mix names its well, not its channel, so its instrument is the one
holding its tip. A well is `<labware>:<address>`, a trough compartment or a tube its own identifier. `entities` maps
every well, compartment and tube on the deck to the (labware name, well label) the checks use, e.g.
{"plate:A1": ["plate on 7.0", "A1"], "water": ["tube_rack on 13.0", "B2"]}.
"""
import re

LIQUID = {"aspirate": "aspirate", "dispense": "dispense"}
TIPS = {"pick_up_tip": "pick", "put_down_tip": "drop", "discard_tip": "drop"}
INSTRUMENTS = {"pipettes": "channel", "pipette_head": "nozzle"}
CHANNEL = re.compile(r"^channel:[^:]+:([^:]+):(0|[1-9]\d*)$")


def instrument_of(entity_id: str) -> str:
    """The instrument a channel entity (`channel:<actor>:<module>:<n>`) names, e.g. `channel_3` or `nozzle_95`."""
    match = CHANNEL.match(entity_id or "")
    if match is None:
        raise ValueError(f"not a channel entity: {entity_id!r}")
    module, index = match.groups()
    return f"{INSTRUMENTS.get(module, module)}_{index}"


def to_events(lineage: list[dict], entities: dict[str, list[str]],
              comments: list[tuple[int, str]] = ()) -> tuple[list[dict], list[dict]]:
    """(events, errors) from a lineage stream. `comments` are (number of events recorded before the comment, text),
    so each lands in order."""
    events: list[dict] = []
    errors: list[dict] = []
    holder: dict[str, str] = {}                  # tip -> the instrument it is on
    pending = sorted(comments, key=lambda c: c[0])
    k = 0

    def well(entity_id: str) -> tuple[str, str]:
        if entity_id not in entities:
            raise ValueError(f"lineage names {entity_id!r}, which is not a well, compartment or tube on the deck")
        labware, label = entities[entity_id]
        return labware, label

    for i, e in enumerate(lineage):
        while k < len(pending) and pending[k][0] <= i:
            events.append({"kind": "comment", "text": pending[k][1]})
            k += 1
        kind = e.get("type", "lineage")
        if kind == "error":
            errors.append(e)
        if kind != "lineage":
            continue
        op, extras = e["operation"], e.get("extras") or {}
        source, target = (e.get("inputs") or {}).get("entity_id"), (e.get("outputs") or {}).get("entity_id")
        if op in TIPS:
            instrument = instrument_of(target if op == "pick_up_tip" else source)
            tip = extras.get("tip")
            if tip is not None:
                if op == "pick_up_tip":
                    holder[tip] = instrument
                else:
                    holder.pop(tip, None)
            events.append({"kind": TIPS[op], "instrument": instrument, "channels": 1, "tip": tip})
        elif op in LIQUID:
            channel_entity, well_entity = (target, source) if op == "aspirate" else (source, target)
            labware, label = well(well_entity)
            moved = float(extras["volume_ul"])
            volume = float(extras.get("volume_requested_ul", moved))
            events.append({"kind": op, "instrument": instrument_of(channel_entity), "channels": 1,
                           "volume": volume, "moved": round(moved, 6), "well": label, "labware": labware})
        elif op == "mix_in_place":
            labware, label = well(source)
            instrument = holder.get(extras.get("tip"))
            if instrument is None:
                raise ValueError(f"mix in {source!r} with tip {extras.get('tip')!r}, which no channel picked up")
            events.append({"kind": "mix", "instrument": instrument, "channels": 1, "cycles": int(extras["cycles"]),
                           "volume": float(extras["volume_ul"]), "well": label, "labware": labware})
        # Labware loads and seeds, labware moves and tools don't change what the checks read.
    events += [{"kind": "comment", "text": text} for _, text in pending[k:]]
    return events, errors
