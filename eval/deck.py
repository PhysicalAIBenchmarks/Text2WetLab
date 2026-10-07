"""A fixed OT-2 deck for an IR: which labware sits in which slot, under which label, and where each tube is.

    plan_deck(protocol) -> dict      (JSON-serialisable; written to harbor/tests/deck.json and shown in the agent brief)

Every IR container becomes one labware, except tubes, which are packed into racks. The labware label IS the IR
container name (or the rack's name), so the checker can map the simulator's events back to IR containers without
guessing: the protocol must `load_labware(load_name, slot, label=...)` exactly as the deck says.

Slots 10 and 11 hold the tip racks; labware gets 1..9. A protocol that needs more raises, so a task whose IR does not
fit is found when the Harbor folder is generated, not when a model fails it.
"""
from paper2protocol.models import Protocol

LOAD = {
    "plate_96": "corning_96_wellplate_360ul_flat",
    "plate_96_deep": "usascientific_96_wellplate_2.4ml_deep",
    "reservoir": "nest_1_reservoir_195ml",
    "waste": "nest_1_reservoir_195ml",
}
# tube kind -> (rack load name, wells in filling order, short name for labels)
RACKS = {
    "tube_1.5ml": ("opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", [f"{r}{c}" for c in range(1, 7) for r in "ABCD"], "tubes_1_5ml"),
    "tube_15ml": ("opentrons_15_tuberack_falcon_15ml_conical", [f"{r}{c}" for c in range(1, 6) for r in "ABC"], "tubes_15ml"),
    "tube_50ml": ("opentrons_6_tuberack_falcon_50ml_conical", [f"{r}{c}" for c in range(1, 4) for r in "AB"], "tubes_50ml"),
}
TIPS = {"300": ("opentrons_96_tiprack_300ul", 11), "20": ("opentrons_96_tiprack_20ul", 10)}
PIPETTES = {"p20_single_gen2": ("left", "20"), "p300_single_gen2": ("right", "300")}
MAX_SLOT = 9


def plan_deck(proto: Protocol) -> dict:
    slots, containers, racks = {}, {}, {}
    nxt = iter(range(1, MAX_SLOT + 1))

    def take(load_name, label, kind):
        try:
            slot = next(nxt)
        except StopIteration:
            raise ValueError(f"{proto.title!r} needs more than {MAX_SLOT} labware slots") from None
        slots[str(slot)] = {"load_name": load_name, "label": label, "kind": kind}
        return slot

    for c in proto.containers:
        if c.kind in RACKS:
            load, wells, short = RACKS[c.kind]
            rack = racks.setdefault(c.kind, {"used": 0, "list": []})
            idx = rack["used"]
            if idx % len(wells) == 0:                       # a new rack when the last one is full
                n = len(rack["list"]) + 1
                label = f"{short}_{n}"
                rack["list"].append((label, take(load, label, c.kind)))
            label, slot = rack["list"][idx // len(wells)]
            containers[c.name] = {"label": label, "load_name": load, "slot": slot, "well": wells[idx % len(wells)]}
            rack["used"] += 1
        else:
            load = LOAD[c.kind]
            containers[c.name] = {"label": c.name, "load_name": load, "slot": take(load, c.name, c.kind)}
            if c.kind in ("reservoir", "waste"):
                containers[c.name]["well"] = "A1"
    return {"slots": slots, "containers": containers,
            "tips": {s: {"load_name": ln, "slot": sl} for s, (ln, sl) in TIPS.items()},
            "pipettes": {n: {"mount": m, "tips": t} for n, (m, t) in PIPETTES.items()}}
