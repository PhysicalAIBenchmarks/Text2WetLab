"""Measure an OT-2 RNA-extraction run log against the paper's protocol."""
from __future__ import annotations

import re

ROWS = "ABCDEFGH"
REAGENT_COLUMNS = {2: "beads", 4: "elution", 6: "isopropanol", 7: "isopropanol",
                   9: "ethanol", 10: "ethanol", 11: "ethanol", 12: "ethanol"}
EXPECTED = {"beads": 40, "isopropanol": 250, "sample": 250, "ethanol": 500, "elution": 100}
PATTERN = ["beads", "isopropanol", "sample", "remove", "ethanol", "remove",
           "ethanol", "remove", "elution", "recover"]
N_SAMPLES = 48
TOLERANCE = 0.05
RESERVOIR_WELL_UL = 15000  # nest_12_reservoir_15ml: no column can give more than it holds


SLOT_ROLES = {"4": "mag", "6": "elution_plate", "7": "tube", "10": "tube", "5": "reservoir"}


def role(labware: str) -> str:
    """Classify labware by its fixed deck slot, so agent-chosen labels can't change the result."""
    match = re.search(r" on (?:slot )?(\d+)\s*$", labware)
    slot = match[1] if match else ""
    return SLOT_ROLES.get(slot, "waste")


def expand(event: dict) -> list[str]:
    well = event["well"]
    if event["channels"] == 8 and role(event["labware"]) in {"mag", "elution_plate"}:
        return [row + well[1:] for row in ROWS] if well[0] == "A" else [well]
    return [well]


def close(value: float, target: float) -> bool:
    return abs(value - target) <= TOLERANCE * target


def analyze(events: list[dict], level: str = "easy") -> dict:
    """Run-log checks. level "hard" (paper only) drops recover_about_80ul: the paper says only "collect the
    supernatant" after a 100 uL elution, and the 80 uL is in the authors' code, not in anything the agent is given."""
    time = 0.0
    magnet = False
    engaged_at = 0.0
    temps: list[tuple[float, float]] = []
    tip_counter = 0
    tip: dict[str, int | None] = {}
    content: dict[str, tuple] = {}
    identity: dict[int, frozenset] = {}
    violations: list[str] = []
    ops: dict[str, list[dict]] = {}
    sample_of: dict[str, str] = {}
    sample_tips: list[int] = []
    recovered_to: dict[str, set[str]] = {}
    liquid: dict[str, float] = {}
    drawn: dict[int, float] = {}  # reservoir column -> net uL taken out by all channels

    def contact(key: str, ids: set) -> None:
        current = tip.get(key)
        if current is None or not ids:
            return
        ids = frozenset(ids)
        if current not in identity:
            identity[current] = ids
        elif identity[current] != ids:
            violations.append(f"tip {current} touched two different samples")

    def add(well: str, op: str, volume: float, key: str) -> None:
        ops.setdefault(well, []).append({
            "op": op, "volume": volume, "t": time, "magnet": magnet,
            "since_engage": time - engaged_at if magnet else None, "tip": tip.get(key)})

    for event in events:
        kind, key = event["kind"], event["instrument"]
        if kind == "delay":
            time += event["seconds"]
        elif kind == "engage":
            if not magnet:
                engaged_at = time
            magnet = True
        elif kind == "disengage":
            magnet = False
        elif kind == "temp":
            temps.append((time, event["celsius"]))
        elif kind == "pick":
            tip_counter += 1
            tip[key] = tip_counter
            liquid[key] = 0.0
        elif kind == "drop":
            tip[key] = None
            liquid[key] = 0.0
        elif kind == "aspirate":
            liquid[key] = liquid.get(key, 0.0) + event["volume"]
            where = role(event["labware"])
            if where == "reservoir":
                column = int(event["well"][1:])
                drawn[column] = drawn.get(column, 0.0) + event["volume"] * event["channels"]  # 8 tips, one trough
                content[key] = ("reagent", REAGENT_COLUMNS.get(column, f"column {column}"))
            elif where == "tube":
                tube = f"{event['labware']}:{event['well']}"
                content[key] = ("tube", tube)
                contact(key, {tube})
            elif where == "mag":
                wells = tuple(expand(event))
                content[key] = ("mag", wells)
                contact(key, {sample_of[w] for w in wells if w in sample_of})
            else:
                content[key] = ("other", event["labware"])
        elif kind == "dispense":
            source = content.get(key, ("none",))
            where = role(event["labware"])
            wells = expand(event)
            # Air gaps are not logged as aspirations, so only credit liquid actually held.
            volume = min(event["volume"], liquid.get(key, 0.0))
            liquid[key] = liquid.get(key, 0.0) - volume
            if where == "reservoir":  # mixing in the trough puts liquid back: count only what leaves it
                column = int(event["well"][1:])
                drawn[column] = drawn.get(column, 0.0) - volume * event["channels"]
            if volume <= 0:
                continue
            if where == "mag":
                if source[0] == "reagent":
                    for well in wells:
                        add(well, source[1], volume, key)
                elif source[0] == "tube":
                    for well in wells:
                        if sample_of.get(well, source[1]) != source[1]:
                            violations.append(f"two samples dispensed into {well}")
                        sample_of[well] = source[1]
                        add(well, "sample", volume, key)
                    if tip.get(key) is None or tip.get(key) not in sample_tips:
                        sample_tips.append(tip.get(key) or 0)
                elif source[0] == "mag":
                    if tuple(wells) == source[1]:
                        for well in wells:
                            add(well, "mix", volume, key)
                    else:
                        violations.append(f"liquid moved between sample wells {source[1][0]} -> {wells[0]}")
                else:
                    violations.append(f"unexpected liquid into {wells[0]}")
            elif source[0] == "mag":
                if where == "elution_plate":
                    for src, dst in zip(source[1], wells):
                        add(src, "recover", volume, key)
                        recovered_to.setdefault(src, set()).add(dst)
                elif where == "waste":
                    for src in source[1]:
                        add(src, "remove", volume, key)
                else:
                    violations.append(f"sample-well liquid returned to {where}")

    sample_wells = sorted(sample_of)
    tubes = set(sample_of.values())
    sequences: dict[str, list[dict]] = {}
    mixes_after_sample: dict[str, int] = {}
    for well in sample_wells:
        merged: list[dict] = []
        after_sample = None
        for op in ops[well]:
            if op["op"] == "mix":
                if after_sample is not None:
                    mixes_after_sample[well] = mixes_after_sample.get(well, 0) + 1
                continue
            if merged and merged[-1]["op"] == op["op"]:
                merged[-1]["volume"] += op["volume"]
                merged[-1]["parts"].append(op)
            else:
                merged.append({**op, "parts": [op]})
            after_sample = 1 if op["op"] == "sample" else (None if op["op"] == "remove" else after_sample)
        # The paper lists beads, isopropanol, sample but its prose mixes sample and
        # isopropanol first, so any order of the three binding reagents is accepted.
        if len(merged) >= 3 and sorted(m["op"] for m in merged[:3]) == sorted(PATTERN[:3]):
            merged[:3] = sorted(merged[:3], key=lambda m: PATTERN.index(m["op"]))
        sequences[well] = merged

    def fraction(test) -> tuple[int, int]:
        ok = sum(1 for well in sample_wells if test(well))
        return ok, len(sample_wells)

    def pattern_ok(well: str) -> bool:
        return [s["op"] for s in sequences[well]] == PATTERN

    def token(well: str, index: int) -> dict:
        return sequences[well][index]

    def volumes_ok(well: str, names: list[str]) -> bool:
        if not pattern_ok(well):
            return False
        for index, name in enumerate(PATTERN):
            if name in names and not close(token(well, index)["volume"], EXPECTED[name]):
                return False
        return True

    def removals_ok(well: str) -> bool:
        if not pattern_ok(well):
            return False
        loaded = [sum(EXPECTED[n] for n in ("beads", "isopropanol", "sample")),
                  EXPECTED["ethanol"], EXPECTED["ethanol"]]
        removes = [s for s in sequences[well] if s["op"] == "remove"]
        return all(r["volume"] >= 0.9 * load for r, load in zip(removes, loaded))

    def magnet_during_removal(well: str) -> bool:
        parts = [p for s in sequences[well] if s["op"] in {"remove", "recover"} for p in s["parts"]]
        return bool(parts) and all(p["magnet"] for p in parts)

    def separation(well: str) -> bool:
        removes = [s for s in sequences[well] if s["op"] == "remove"]
        return bool(removes) and (removes[0]["parts"][0]["since_engage"] or 0) >= 240

    def incubation(well: str) -> bool:
        seq = sequences[well]
        samples = [s for s in seq if s["op"] == "sample"]
        removes = [s for s in seq if s["op"] == "remove"]
        if not samples or not removes or removes[0]["since_engage"] is None:
            return False
        engaged = removes[0]["t"] - removes[0]["since_engage"]
        return engaged - samples[0]["parts"][-1]["t"] >= 300

    def drying(well: str) -> bool:
        seq = sequences[well]
        removes = [s for s in seq if s["op"] == "remove"]
        elution = [s for s in seq if s["op"] == "elution"]
        return bool(removes and elution) and elution[0]["t"] - removes[-1]["parts"][-1]["t"] >= 240

    def elution_magnet(well: str) -> bool:
        seq = sequences[well]
        elution = [s for s in seq if s["op"] == "elution"]
        recover = [s for s in seq if s["op"] == "recover"]
        if not elution or not recover:
            return False
        first = recover[0]["parts"][0]
        return (not any(p["magnet"] for p in elution[0]["parts"])
                and first["since_engage"] is not None and first["since_engage"] >= 90
                and first["t"] - first["since_engage"] >= elution[0]["t"])

    def recovery(well: str) -> bool:
        recover = [s for s in sequences[well] if s["op"] == "recover"]
        return bool(recover) and 70 <= recover[-1]["volume"] <= 100 and len(recovered_to.get(well, ())) == 1

    def recovery_leaves_beads(well: str) -> bool:
        # the paper and the task take ~80 uL of the 100 uL eluate so the pellet stays behind; the whole 100 uL does not
        recover = [s for s in sequences[well] if s["op"] == "recover"]
        return bool(recover) and 70 <= recover[-1]["volume"] <= 90

    first_recover = min((p["t"] for w in sample_wells for s in sequences[w]
                         if s["op"] == "recover" for p in s["parts"]), default=None)
    cold = first_recover is not None and any(t <= first_recover and abs(c - 4) < 0.5 for t, c in temps)
    targets = [next(iter(recovered_to[w])) for w in sample_wells if len(recovered_to.get(w, ())) == 1]
    odd = all(int(w[1:]) % 2 == 1 for w in sample_wells)

    def check(name: str, result: tuple[int, int] | bool, detail: str = "") -> dict:
        if isinstance(result, tuple):
            ok, total = result
            passed = total == N_SAMPLES and ok == total
            detail = detail or f"{ok}/{total} sample wells"
        else:
            passed = bool(result)
        return {"name": name, "pass": passed, "detail": detail}

    checks = [
        check("48_samples_to_odd_columns",
              len(sample_wells) == N_SAMPLES and len(tubes) == N_SAMPLES and odd,
              f"{len(tubes)} tubes -> {len(sample_wells)} wells, odd columns only: {odd}"),
        check("step_order", fraction(pattern_ok),
              "expected per well: " + " > ".join(PATTERN)),
        check("binding_volumes_40_250_250", fraction(lambda w: volumes_ok(w, ["beads", "isopropanol", "sample"]))),
        check("mix_5x_after_sample", fraction(lambda w: mixes_after_sample.get(w, 0) >= 5)),
        check("incubation_5min_before_magnet", fraction(incubation)),
        check("magnet_4min_before_first_removal", fraction(separation)),
        check("supernatant_removed_each_step", fraction(removals_ok)),
        check("magnet_engaged_for_all_removals", fraction(magnet_during_removal)),
        check("two_500ul_ethanol_washes", fraction(lambda w: volumes_ok(w, ["ethanol"]))),
        check("air_dry_4min", fraction(drying)),
        check("elution_100ul", fraction(lambda w: volumes_ok(w, ["elution"]))),
        check("elution_off_magnet_then_90s_on", fraction(elution_magnet)),
        check("recover_70_100ul_one_well_each", fraction(recovery)),
        check("distinct_elution_wells", len(targets) == N_SAMPLES and len(set(targets)) == N_SAMPLES,
              f"{len(set(targets))} distinct elution wells"),
        check("elution_plate_4C_before_recovery", cold, f"temperatures set: {temps}"),
        check("fresh_tip_per_sample_no_cross_contact",
              not violations and len(set(sample_tips)) == len(sample_tips) == N_SAMPLES,
              f"{len(set(sample_tips))} distinct tips for {len(sample_tips)} sample transfers; "
              f"violations: {violations[:5]}"),
        check("reservoir_columns_within_15ml", all(v <= RESERVOIR_WELL_UL * (1 + TOLERANCE / 5) for v in drawn.values()),
              "uL drawn per reservoir column: " + ", ".join(f"{c}: {v:g}" for c, v in sorted(drawn.items()))),
    ]
    if level == "easy":  # the easy task's step 13 says "Transfer 80 uL of eluate"
        checks.append(check("recover_about_80ul", fraction(recovery_leaves_beads),
                            "70-90 uL of the 100 uL eluate, as the task's step 13 says; "
                            + "{}/{} sample wells".format(*fraction(recovery_leaves_beads))))
    example = sample_wells[0] if sample_wells else None
    return {
        "checks": checks,
        "checks_passed": sum(c["pass"] for c in checks),
        "checks_total": len(checks),
        "total_delay_min": round(time / 60, 1),
        "example_well": example,
        "example_sequence": [
            f"{s['op']} {s['volume']:g}uL" + (" (magnet)" if s["parts"][0]["magnet"] else "")
            for s in sequences.get(example, [])
        ],
    }
