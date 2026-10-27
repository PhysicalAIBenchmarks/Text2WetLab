"""
Judge a simulated Opentrons run against a task's IR. One checker for every task.

    python eval/spec_check.py tasks/a1-a12-100ul protocol.py [--labware DIR]

The run is simulated on Harbor's stack (Opentrons 7.5.0, Python 3.10; see OT_VENV) by eval/runlog.py,
which yields atomic events. The checker replays them and applies:

  generic rules (every task)        tip before aspirate, no overdispense, no draw from an empty
                                    non-stock well, tip dropped at the end
  end state (derived from the IR)   what every mapped container must hold when the run finishes

The expected end state comes from paper2protocol.timeline, not from hand-written numbers, so a
protocol is judged on what it achieves and not on how: transfer(), distribute() and explicit
aspirate/dispense loops all pass if the plate ends up right. A task whose instruction does not name
the wells declares `[checks] free_wells = ["plate"]` in task.toml; for those containers only the
multiset of volumes is judged, not the positions.

Pipette capacity is NOT replayed here: the simulator rejects an over-capacity aspirate itself
(`simulator_ran` fails), and replaying it would misjudge distribute(), whose disposal volume is
blown out without an event in the log.

IR containers are matched to run labware by kind. If that match is ambiguous the end-state check
reports "not applicable" instead of guessing.

Other backends (backends/<name>/) feed the same checker their own runs. The contract:
  events     {"kind": "pick" | "drop" | "aspirate" | "dispense", "instrument", "labware", "well", "volume",
             optional "channels"}; a pick may name the physical tip ("tip"), so a used tip put back and picked up
             again keeps what it touched. Tip state is kept per instrument (a channel, a head), well volumes are shared.
  labware    {run labware name: load name}, as run["labware"].
  geometry   optional {run labware name: {"family": "plate" | "trough" | "tube" | "tube_rack" | ..., "wells": n,
             "volumes": [uL, ...]}}: what the labware is, preferred over its name for kind and stock checks.
  deck       a container with no "slot" is matched by role: exactly one labware carries its label, anywhere on the
             deck, and it is of the container's kind. Containers with a slot keep the fixed OT-2 layout.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # a Harbor tests/ folder carries paper2protocol/ beside this file
from paper2protocol.models import Protocol  # noqa: E402
from paper2protocol.timeline import timeline  # noqa: E402

OT_VENV = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path(__file__).resolve().parent.parent / ".venv-ot"))  # scripts/setup_ot_venv.sh
ROWS = "ABCDEFGH"
KIND_WORDS = {  # IR container kind -> words in the Opentrons labware display name
    "plate_96_deep": ("deep",),
    "plate_96": ("well plate", "wellplate", "pcr plate"),
    "reservoir": ("reservoir", "trough"),
    "tube_1.5ml": ("tube rack", "tuberack"), "tube_15ml": ("tube rack", "tuberack"), "tube_50ml": ("tube rack", "tuberack"),
}
STOCK_WORDS = ("reservoir", "trough", "tube rack", "tuberack")  # sources assumed to have ample volume


def simulate(protocol: str, labware_dir: str | None = None, timeout: int = 600) -> dict:
    """Run runlog.py in the Opentrons environment. Returns {"ok", "events", "labware"} or {"ok": False, "error"}.
    OT_PYTHON and RUNLOG override the interpreter and script (inside a Harbor container they are /opt/ot and /tests)."""
    python = os.environ.get("OT_PYTHON", str(OT_VENV / "bin/python"))
    runlog = os.environ.get("RUNLOG", str(ROOT / "eval/runlog.py"))
    with tempfile.TemporaryDirectory() as empty:
        out = pathlib.Path(empty, "result.json")      # a file, not stdout: a protocol can print a forged result and exit early
        r = subprocess.run([python, runlog, protocol, labware_dir or empty, str(out)], capture_output=True, text=True, timeout=timeout)
        if out.exists():
            return json.loads(out.read_text())
    return {"ok": False, "error": (r.stderr.strip().splitlines() or ["runlog produced no result (the protocol exited early?)"])[-1]}


def error_kind(err: str) -> str:
    """The specific simulator error type, e.g. TipNotAttachedError. The raw message embeds a fresh UUID and
    timestamp on every run, so it must never be stored or compared."""
    kinds = re.findall(r"errorType='(\w+)'", err)
    return kinds[-1] if kinds else (err.split(":")[0].strip() or "unknown")[:80]


RESERVOIR_WORDS = ("reservoir", "trough")


def is_stock(labware: str, loadnames: dict | None = None, geometry: dict | None = None) -> bool:
    """A source with ample volume. With the simulator's load names (new traces) only reservoirs are stock and tubes
    are tracked exactly; for old traces without them the display name is all there is and tube racks count as stock.
    A run's geometry, where it has one, decides first: only single-trough labware is stock."""
    if geometry and labware in geometry:
        return geometry[labware]["family"] == "trough"
    if loadnames and labware in loadnames:
        return any(w in loadnames[labware].lower() for w in RESERVOIR_WORDS)
    return any(w in labware.lower() for w in STOCK_WORDS)


@dataclass
class State:
    tip: bool = False
    held: float = 0.0
    wells: dict = field(default_factory=dict)      # (labware, well) -> uL
    errors: list = field(default_factory=list)     # (event index, code)
    aspirations: int = 0
    fed: dict = field(default_factory=dict)        # (labware, well) -> labware it received liquid from


def wells_of(event, loadnames=None, geometry=None) -> list[str]:
    well = event["well"]
    if event.get("channels") == 8 and not is_stock(event["labware"], loadnames, geometry) and well[0] == "A":
        return [r + well[1:] for r in ROWS]
    return [well]


TIP_KINDS = ("pick", "drop", "aspirate", "dispense")


def _holder(events: list[dict]):
    """Which tip an event belongs to: its instrument when every tip event names one (a STAR channel, an OT-2 pipette),
    else one shared tip, as for traces recorded without instruments."""
    if all(e.get("instrument") for e in events if e["kind"] in TIP_KINDS):
        return lambda e: e["instrument"]
    return lambda e: ""


def replay(events: list[dict], initial: dict | None = None, ample: frozenset = frozenset(), loadnames: dict | None = None,
           geometry: dict | None = None) -> State:
    """Apply atomic events in order. `initial` = {(labware, well): uL} for non-stock wells; `ample` = (labware, well)
    pairs the IR declares as stocks with unlimited volume (aspirating from them is never an error and is not counted).
    Each instrument holds its own tip and volume; well volumes are shared."""
    st = State(wells=dict(initial or {}))
    holder, tips = _holder(events), {}             # instrument -> {"tip", "held", "drawn": labware aspirated from}
    for i, e in enumerate(events):
        kind = e["kind"]
        if kind not in TIP_KINDS:
            continue
        t = tips.setdefault(holder(e), {"tip": False, "held": 0.0, "drawn": set()})
        if kind == "pick":
            if t["tip"]:
                st.errors.append((i, "already_has_tip"))
            t.update(tip=True, held=0.0, drawn=set())
        elif kind == "drop":
            t.update(tip=False, held=0.0, drawn=set())
        else:
            vol = e["volume"]
            if not t["tip"]:
                st.errors.append((i, "NoTipError"))
                continue
            if kind == "aspirate":
                st.aspirations += 1
                if not is_stock(e["labware"], loadnames, geometry):
                    for w in wells_of(e, loadnames, geometry):
                        if (e["labware"], w) in ample:
                            continue
                        if st.wells.get((e["labware"], w), 0.0) < vol - 1e-9:
                            st.errors.append((i, "aspirate_from_empty"))
                            break
                        st.wells[(e["labware"], w)] -= vol
                t["held"] += vol
                t["drawn"].add(e["labware"])
            else:
                if vol > t["held"] + 1e-9:
                    st.errors.append((i, "overdispense"))
                for w in wells_of(e, loadnames, geometry):
                    st.wells[(e["labware"], w)] = st.wells.get((e["labware"], w), 0.0) + vol
                    st.fed.setdefault((e["labware"], w), set()).update(t["drawn"] - {e["labware"]})
                t["held"] = max(t["held"] - vol, 0.0)
    st.tip = any(t["tip"] for t in tips.values())  # tip_dropped_at_end: no instrument may still hold one
    st.held = sum(t["held"] for t in tips.values())
    return st


def cross_contamination(events: list[dict], waste: frozenset = frozenset()) -> list:
    """(event index, well) where one tip carries liquid between wells it should not (see _tip_contamination), judged
    per physical tip: a pick that names its tip ("tip") continues that tip's history, so a used tip put back and picked
    up again still carries what it touched; a pick without one is a fresh tip. Dispensing into `waste` (run labware
    names) is never contamination: waste receives whatever a tip carries."""
    holder, current, groups = _holder(events), {}, {}
    for i, e in enumerate(events):
        if e["kind"] in ("pick", "drop"):
            current[holder(e)] = ("tip", e["tip"]) if e["kind"] == "pick" and e.get("tip") else ("event", i)
        elif e["kind"] in ("aspirate", "dispense"):
            groups.setdefault(current.get(holder(e), ("start", holder(e))), []).append(i)
    bad = []
    for idx in groups.values():
        bad += [(idx[j], well) for j, well in _tip_contamination([events[i] for i in idx])]
    return sorted((i, well) for i, well in bad if not (events[i]["kind"] == "dispense" and events[i]["labware"] in waste))


def _tip_contamination(events: list[dict]) -> list:
    """(index, well) where one tip's aspirates and dispenses carry liquid between wells they should not. A tip may go
    back to wells it dispensed into (mixing) and to the one well it started from (multi-dispense). Once it has mixed in
    a destination (drawn from a well it dispensed into that was not one of its sources), it carries that well's
    contents: dispensing into any other well, or drawing from any other well (the stock included), is contamination
    until a fresh tip. Mixing in a source before drawing from it (resuspending a colony or beads) carries nothing the
    transfer is not meant to move. A tip whose only destination so far is one well, drawing from that well, holds only
    that well's liquid (adding water to a well and then moving the eluate with the same tip): it starts over with that
    well as its only source."""
    bad, sources, own, carried = [], set(), set(), set()
    for i, e in enumerate(events):
        key = (e["labware"], e["well"])
        if e["kind"] == "dispense":
            if carried - {key}:
                bad.append((i, key[1]))
            own.add(key)
        elif e["kind"] == "aspirate":
            if own == {key} and carried <= {key}:   # moving the one well this tip filled
                sources, own, carried = {key}, set(), set()
                continue
            if (sources and key not in sources and key not in own) or carried - {key}:
                bad.append((i, key[1]))
            if key in own and key not in sources:   # mixing in a destination
                carried.add(key)
            elif key not in own:
                sources.add(key)
    return bad


def _labware_for(kind: str, events) -> set[str]:
    words = KIND_WORDS.get(kind, ())
    names = {e["labware"] for e in events if e["kind"] in ("aspirate", "dispense")}
    if kind == "plate_96":
        return {n for n in names if any(w in n.lower() for w in words) and "deep" not in n.lower()}
    return {n for n in names if any(w in n.lower() for w in words)}


def _map_containers(proto: Protocol, events) -> dict:
    """Legacy mapping (no deck): IR container name -> run labware name, only where the match is unique on both sides."""
    mapping = {}
    for kind in {c.kind for c in proto.containers}:
        irs = [c.name for c in proto.containers if c.kind == kind]
        run = _labware_for(kind, events)
        if len(irs) == 1 and len(run) == 1:
            mapping[irs[0]] = next(iter(run))
    return mapping


MODULE_LABWARE = re.compile(r"^(?P<label>.+?) on \w+Context at (?P<where>.+?) lw .*$")


def labware_names(run: dict) -> dict:
    """run["labware"] with module labware named the way the pipetting events name it. From API 2.14 the simulator keys
    labware on a module as "<label> on ThermocyclerContext at Thermocycler Module GEN1 on 7 lw <label>" while its
    aspirate/dispense events say "<label> on Thermocycler Module GEN1 on 7"; without this a correct deck fails."""
    out = {}
    for name, load in (run.get("labware") or {}).items():
        m = MODULE_LABWARE.match(name)
        out[f"{m['label']} on {m['where']}" if m else name] = load
    return out


KIND_GEOMETRY = {   # IR container kind -> (families, wells or None for any, [low, high) uL a well of that kind holds)
    "plate_96": (("plate",), 96, (0, 1000)),
    "plate_96_deep": (("plate",), 96, (1000, 5000)),
    "reservoir": (("trough",), 1, (0, float("inf"))),
    "waste": (("trough",), 1, (0, float("inf"))),
    "tube_1.5ml": (("tube", "tube_rack"), None, (1000, 2500)),
    "tube_15ml": (("tube", "tube_rack"), None, (10000, 20000)),
    "tube_50ml": (("tube", "tube_rack"), None, (40000, 60000)),
}


def kind_matches(kind: str, load_name: str, geometry: dict | None = None) -> bool:
    """Whether a labware is of an IR container kind: by its geometry when the run records one, else by its name."""
    if geometry and kind in KIND_GEOMETRY:
        families, wells, (low, high) = KIND_GEOMETRY[kind]
        return (geometry["family"] in families and (wells is None or geometry["wells"] == wells)
                and any(low <= v < high for v in geometry["volumes"]))
    name = load_name.lower()
    if kind == "plate_96" and "deep" in name:
        return False
    return any(w in name for w in KIND_WORDS.get(kind, (kind,)))


def _deck_mapping(proto, run, deck, add):
    """With a deck: container -> (run labware string, {IR well -> real well}).
    Fixed layout (a container with a slot, see eval/deck.py): a container is only mapped if the protocol loaded a
    labware under the deck's label AND that labware really is the deck's load name, so a plate labelled as a reservoir
    (or the reverse) cannot stand in for it. By role (no slot): exactly one labware carries the label, anywhere on the
    deck, and it is of the container's kind; a tube may be its own labware named after the tube instead of a rack's well."""
    loadnames = labware_names(run)
    geometry = run.get("geometry") or {}
    used = {s.source for s in proto.steps if s.source} | {s.dest for s in proto.steps if s.dest}
    mapping = {}
    for cname, spec in deck["containers"].items():
        if cname not in used:
            continue
        hits = [n for n in loadnames if n.startswith(spec["label"] + " on ")]
        if "slot" not in spec:
            well = spec.get("well", "")
            if spec["label"] != cname and well and not hits:
                hits, well = [n for n in loadnames if n.startswith(cname + " on ")], "A1"
            if len(hits) != 1:
                add(f"deck_labware:{cname}", False, f"expected exactly one labware with identifier {spec['label']!r}"
                    + (f" (or a tube {cname!r})" if spec["label"] != cname else "") + f", found {len(hits)}")
            elif spec.get("load_name") and loadnames[hits[0]] != spec["load_name"]:
                add(f"deck_labware:{cname}", False, f"{spec['label']!r} must be {spec['load_name']}, got {loadnames[hits[0]]}")
            elif spec.get("kind") and not kind_matches(spec["kind"], loadnames[hits[0]], geometry.get(hits[0])):
                add(f"deck_labware:{cname}", False, f"{spec['label']!r} must be {spec['kind']}, got {loadnames[hits[0]]}")
            else:
                mapping[cname] = (hits[0], well)
            continue
        if len(hits) == 1 and hits[0] != f"{spec['label']} on {spec['slot']}":
            add(f"deck_labware:{cname}", False, f"{spec['label']!r} must be in slot {spec['slot']}, found {hits[0]!r}")
            continue
        if len(hits) != 1:
            add(f"deck_labware:{cname}", False, f"expected exactly one labware labelled {spec['label']!r}, found {len(hits)}")
        elif loadnames[hits[0]] != spec["load_name"]:
            add(f"deck_labware:{cname}", False, f"{spec['label']!r} must be {spec['load_name']}, got {loadnames[hits[0]]}")
        else:
            mapping[cname] = (hits[0], spec.get("well", ""))
    return mapping


def check(proto: Protocol, run: dict, free_wells: frozenset = frozenset(), deck: dict | None = None,
          not_from_paper: dict | frozenset = frozenset()) -> dict:
    """Verdict for one simulated run against an IR. `run` is simulate()'s result; `deck` pins every container to a labware."""
    checks = []
    if not isinstance(not_from_paper, dict):
        not_from_paper = {c: None for c in not_from_paper}

    def add(name, ok, detail=""):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    if not run.get("ok"):
        add("simulator_ran", False, error_kind(run.get("error", "")))
        return {"passed": False, "checks": checks}
    add("simulator_ran", True)
    events, loadnames, geometry = run["events"], labware_names(run) or None, run.get("geometry") or None
    kinds = {c.name: c.kind for c in proto.containers}
    states, _ = timeline(proto)
    if deck:
        dm = _deck_mapping(proto, run, deck, add)
        mapping = {c: lab for c, (lab, _w) in dm.items()}
        tube_well = {c: w for c, (_l, w) in dm.items() if w}   # tubes and reservoirs sit at one named well
    else:
        mapping, tube_well = _map_containers(proto, events), {}
    initial, ample = {}, set()
    for c in proto.initial_contents:
        lab = mapping.get(c.container)
        if not lab:
            continue
        for (cn, w), v in states[0].items():
            if cn != c.container:
                continue
            rw = tube_well.get(cn) if w == "" and tube_well.get(cn) else w
            if v is None:
                ample.add((lab, rw))          # volume null in the IR = a stock with ample volume
            elif not is_stock(lab, loadnames, geometry):
                initial[(lab, rw)] = v
    st = replay(events, initial, frozenset(ample), loadnames, geometry)
    codes = lambda *names: sorted({(i, c) for i, c in st.errors if c in names})
    add("tip_before_aspirate", not codes("NoTipError"), str(codes("NoTipError")[:3]))
    add("no_overdispense", not codes("overdispense"), str(codes("overdispense")[:3]))
    add("no_aspirate_from_empty_well", not codes("aspirate_from_empty"), str(codes("aspirate_from_empty")[:3]))
    add("tip_dropped_at_end", not st.tip)
    if deck:    # fresh tip whenever the source changes; only judged against a fixed deck, where wells are unambiguous
        cc = cross_contamination(events, frozenset(lab for c, lab in mapping.items() if kinds[c] == "waste"))
        add("no_cross_contamination", not cc, str(cc[:3]))
    final, na = states[-1], []
    for cname, lab in mapping.items():
        if kinds[cname] in ("reservoir", "waste"):
            continue
        want = {(tube_well[cname] if w == "" and tube_well.get(cname) else w): v for (cn, w), v in final.items() if cn == cname and v}
        only = tube_well.get(cname)        # tubes share a rack: look at this tube's well only
        got = {w: round(v, 6) for (lb, w), v in st.wells.items() if lb == lab and v > 1e-9 and (lb, w) not in ample and (only is None or w == only)}
        if cname in not_from_paper:  # the paper does not fix these volumes: judge what it does fix
            add(f"composition:{cname}", *_composition(cname, lab, want, got, st.fed, proto, mapping,
                                                      not_from_paper[cname],
                                                      cname in free_wells))
            na.append(f"end_state:{cname} (the source paper does not determine the exact volumes; composition checked instead)")
            continue
        if cname in free_wells:  # the instruction does not name the wells: judge the volumes, not the positions
            ok = sorted(round(v, 6) for v in want.values()) == sorted(got.values())
            add(f"end_state:{cname}", ok, f"expected volumes {sorted(want.values())}, got {sorted(got.values())} (positions free)")
        else:
            ok = {w: round(v, 6) for w, v in want.items()} == got
            add(f"end_state:{cname}", ok, "" if ok else f"expected {want}, got {got}")
    if not mapping:
        na.append("end_state (no IR container matched a unique run labware)")
    return {"passed": all(c["pass"] for c in checks), "checks": checks, "not_applicable": na,
            "aspirations": st.aspirations}


def _composition(cname, lab, want, got, fed, proto, mapping, volume_range, free) -> tuple[bool, str]:
    """For a container whose exact volumes the paper does not fix: the same wells are filled (any wells if positions
    are free), each from every source container the IR sends there, the wells the IR fills equally hold equal volumes,
    and each volume is inside the range the paper supports."""
    problems = []
    if free and len(got) != len(want) or not free and set(got) != set(want):
        problems.append(f"filled {len(got)} wells, expected {len(want)}" + ("" if free else f" ({sorted(set(want) ^ set(got))[:4]} differ)"))
    need = {mapping[s.source] for s in proto.steps if s.kind == "transfer" and s.dest == cname and s.source in mapping}
    short = sorted(w for w in got if need - fed.get((lab, w), set()))
    if short:
        problems.append(f"{len(short)} wells lack an input, e.g. {short[0]} has none from {sorted(need - fed.get((lab, short[0]), set()))}")
    if len(set(want.values())) == 1 and len(set(got.values())) > 1:
        problems.append(f"unequal volumes {sorted(set(got.values()))[:4]}")
    if volume_range:
        lo, hi = volume_range
        off = sorted(v for v in set(got.values()) if not lo - 1e-6 <= v <= hi + 1e-6)
        if off:
            problems.append(f"volumes {off[:3]} outside the {lo:g}-{hi:g} uL the paper supports")
    return not problems, "; ".join(problems)


def not_from_paper(task_dir) -> dict:
    """Containers whose exact end state the task's source paper does not determine, from task.toml [checks]:
    {container: (min uL, max uL) the paper supports, or None}. A list of names (no range) is accepted too."""
    import tomllib

    f = pathlib.Path(task_dir) / "task.toml"
    nfp = tomllib.loads(f.read_text()).get("checks", {}).get("not_from_paper", []) if f.exists() else []
    return {c: None for c in nfp} if isinstance(nfp, list) else {c: tuple(r) if r else None for c, r in nfp.items()}


def free_wells(task_dir) -> frozenset:
    """Containers whose well positions the task leaves open, from task.toml [checks]."""
    import tomllib

    f = pathlib.Path(task_dir) / "task.toml"
    return frozenset(tomllib.loads(f.read_text()).get("checks", {}).get("free_wells", [])) if f.exists() else frozenset()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("task", help="task folder (reads public/ir.json and task.toml)")
    ap.add_argument("protocol")
    ap.add_argument("--labware")
    a = ap.parse_args()
    task = pathlib.Path(a.task)
    proto = Protocol.model_validate_json((task / "public/ir.json").read_text())
    res = check(proto, simulate(a.protocol, a.labware), free_wells(task))
    for c in res["checks"]:
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['name']:34} {c['detail']}")
    for n in res.get("not_applicable", []):
        print(f"n/a   {n}")
    print("VERDICT:", "PASS" if res["passed"] else "FAIL")
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
