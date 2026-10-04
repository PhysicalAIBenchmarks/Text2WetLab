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
from paper2protocol.models import Protocol  # noqa: E402
from paper2protocol.timeline import timeline  # noqa: E402

OT_VENV = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path.home() / "Desktop/ot-sim-venv"))
ROWS = "ABCDEFGH"
KIND_WORDS = {  # IR container kind -> words in the Opentrons labware display name
    "plate_96_deep": ("deep",),
    "plate_96": ("well plate", "wellplate", "pcr plate"),
    "reservoir": ("reservoir", "trough"),
    "tube_1.5ml": ("tube rack", "tuberack"), "tube_15ml": ("tube rack", "tuberack"), "tube_50ml": ("tube rack", "tuberack"),
}
STOCK_WORDS = ("reservoir", "trough", "tube rack", "tuberack")  # sources assumed to have ample volume


def simulate(protocol: str, labware_dir: str | None = None, timeout: int = 600) -> dict:
    """Run eval/runlog.py in the Opentrons environment. Returns {"ok", "events"} or {"ok": False, "error"}."""
    with tempfile.TemporaryDirectory() as empty:
        r = subprocess.run([str(OT_VENV / "bin/python"), str(ROOT / "eval/runlog.py"), protocol, labware_dir or empty],
                           capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": (r.stderr.strip().splitlines() or ["runlog produced no output"])[-1]}


def error_kind(err: str) -> str:
    """The specific simulator error type, e.g. TipNotAttachedError. The raw message embeds a fresh UUID and
    timestamp on every run, so it must never be stored or compared."""
    kinds = re.findall(r"errorType='(\w+)'", err)
    return kinds[-1] if kinds else (err.split(":")[0].strip() or "unknown")[:80]


def is_stock(labware: str) -> bool:
    return any(w in labware.lower() for w in STOCK_WORDS)


@dataclass
class State:
    tip: bool = False
    held: float = 0.0
    wells: dict = field(default_factory=dict)      # (labware, well) -> uL
    errors: list = field(default_factory=list)     # (event index, code)
    aspirations: int = 0


def wells_of(event) -> list[str]:
    well = event["well"]
    if event.get("channels") == 8 and not is_stock(event["labware"]) and well[0] == "A":
        return [r + well[1:] for r in ROWS]
    return [well]


def replay(events: list[dict], initial: dict | None = None) -> State:
    """Apply atomic events in order. `initial` = {(labware, well): uL} for non-stock wells."""
    st = State(wells=dict(initial or {}))
    for i, e in enumerate(events):
        kind = e["kind"]
        if kind == "pick":
            if st.tip:
                st.errors.append((i, "already_has_tip"))
            st.tip, st.held = True, 0.0
        elif kind == "drop":
            st.tip, st.held = False, 0.0
        elif kind in ("aspirate", "dispense"):
            vol = e["volume"]
            if not st.tip:
                st.errors.append((i, "NoTipError"))
                continue
            if kind == "aspirate":
                st.aspirations += 1
                if not is_stock(e["labware"]):
                    for w in wells_of(e):
                        if st.wells.get((e["labware"], w), 0.0) < vol - 1e-9:
                            st.errors.append((i, "aspirate_from_empty"))
                            break
                        st.wells[(e["labware"], w)] -= vol
                st.held += vol
            else:
                if vol > st.held + 1e-9:
                    st.errors.append((i, "overdispense"))
                for w in wells_of(e):
                    st.wells[(e["labware"], w)] = st.wells.get((e["labware"], w), 0.0) + vol
                st.held = max(st.held - vol, 0.0)
    return st


def _labware_for(kind: str, events) -> set[str]:
    words = KIND_WORDS.get(kind, ())
    names = {e["labware"] for e in events if e["kind"] in ("aspirate", "dispense")}
    if kind == "plate_96":
        return {n for n in names if any(w in n.lower() for w in words) and "deep" not in n.lower()}
    return {n for n in names if any(w in n.lower() for w in words)}


def _map_containers(proto: Protocol, events) -> dict:
    """IR container name -> run labware name, only where the match is unique on both sides."""
    mapping = {}
    for kind in {c.kind for c in proto.containers}:
        irs = [c.name for c in proto.containers if c.kind == kind]
        run = _labware_for(kind, events)
        if len(irs) == 1 and len(run) == 1:
            mapping[irs[0]] = next(iter(run))
    return mapping


def check(proto: Protocol, run: dict, free_wells: frozenset = frozenset()) -> dict:
    """Verdict for one simulated run against an IR. `run` is simulate()'s result."""
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    if not run.get("ok"):
        add("simulator_ran", False, error_kind(run.get("error", "")))
        return {"passed": False, "checks": checks}
    add("simulator_ran", True)
    events = run["events"]
    mapping = _map_containers(proto, events)
    kinds = {c.name: c.kind for c in proto.containers}
    states, _ = timeline(proto)
    initial = {}
    for c in proto.initial_contents:
        lab = mapping.get(c.container)
        if lab and not is_stock(lab) and c.volume_ul:
            for (cn, w), v in states[0].items():
                if cn == c.container and v:
                    initial[(lab, w)] = v
    st = replay(events, initial)
    codes = lambda *names: sorted({(i, c) for i, c in st.errors if c in names})
    add("tip_before_aspirate", not codes("NoTipError"), str(codes("NoTipError")[:3]))
    add("no_overdispense", not codes("overdispense"), str(codes("overdispense")[:3]))
    add("no_aspirate_from_empty_well", not codes("aspirate_from_empty"), str(codes("aspirate_from_empty")[:3]))
    add("tip_dropped_at_end", not st.tip)
    final, na = states[-1], []
    for cname, lab in mapping.items():
        if kinds[cname] == "reservoir":
            continue
        want = {w: v for (cn, w), v in final.items() if cn == cname and v}
        got = {w: round(v, 6) for (lb, w), v in st.wells.items() if lb == lab and v > 1e-9}
        if cname in free_wells:  # the instruction does not name the wells: judge the volumes, not the positions
            ok = sorted(want.values()) == sorted(got.values())
            add(f"end_state:{cname}", ok, f"expected volumes {sorted(want.values())}, got {sorted(got.values())} (positions free)")
        else:
            ok = want == got
            add(f"end_state:{cname}", ok, "" if ok else f"expected {want}, got {got}"[:160])
    if not mapping:
        na.append("end_state (no IR container matched a unique run labware)")
    return {"passed": all(c["pass"] for c in checks), "checks": checks, "not_applicable": na,
            "aspirations": st.aspirations}


def free_wells(task_dir) -> frozenset:
    """Containers whose well positions the task leaves open, from task.toml [checks]."""
    import tomllib

    f = pathlib.Path(task_dir) / "task.toml"
    return frozenset(tomllib.loads(f.read_text()).get("checks", {}).get("free_wells", [])) if f.exists() else frozenset()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("task", help="task folder containing ir.json")
    ap.add_argument("protocol")
    ap.add_argument("--labware")
    a = ap.parse_args()
    task = pathlib.Path(a.task)
    proto = Protocol.model_validate_json((task / "ir.json").read_text())
    res = check(proto, simulate(a.protocol, a.labware), free_wells(task))
    for c in res["checks"]:
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['name']:34} {c['detail']}")
    for n in res.get("not_applicable", []):
        print(f"n/a   {n}")
    print("VERDICT:", "PASS" if res["passed"] else "FAIL")
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
