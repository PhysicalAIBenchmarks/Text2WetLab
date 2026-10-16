"""Judge a device run with eval/spec_check.check(), from the files make_tasks.py writes into a task's tests/.

    python check.py <tests dir> result.json

The device-specific parts live in spec_check itself, behind its backend contract: tip state per instrument (a STAR
holds up to eight tips), contamination per physical tip, waste exempt from contamination, the run's labware geometry,
and the deck matched by role (identifier + kind) instead of slot and load name, since the agent arranges the deck.

This file is vendored into every task's tests/ next to spec_check.py and paper2protocol/, so it imports them from
its own directory (in the repo, the benchmark's eval/ and package root stand in).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if not (HERE / "spec_check.py").exists():                       # in the repo: the benchmark's eval/ and package root
    UPSTREAM = HERE.parents[2]
    sys.path.insert(0, str(UPSTREAM))
    sys.path.insert(0, str(UPSTREAM / "eval"))
import spec_check  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402


def mix_as_pair(events: list[dict]) -> list[dict]:
    """A `mix` event (lineage_events.py: one per channel, with its cycles) as one aspirate and one dispense of the mix
    volume in the same well, the way upstream's run log shows a mix. That is all the checks need from it: the well must
    hold the volume, the channel must have a tip, and a tip that mixed in a destination carries it; further cycles
    change none of these. `moved` 0: the liquid model counts a mix as no transfer."""
    out = []
    for e in events:
        if e["kind"] == "mix":
            pair = {k: e[k] for k in ("instrument", "channels", "well", "labware")} | {"volume": e["volume"], "moved": 0.0}
            out += [dict(pair, kind="aspirate"), dict(pair, kind="dispense")]
        else:
            out.append(e)
    return out


def check_run(tests: pathlib.Path, run: dict) -> dict:
    """The checks for a run, from a tests/ folder: ir.json, the generic deck.json and checks.json (free wells,
    quantities not from the paper), the files make_tasks.py writes there."""
    deck = json.loads((tests / "deck.json").read_text())
    ir = Protocol.model_validate_json((tests / "ir.json").read_text())
    cfg = json.loads((tests / "checks.json").read_text())
    if run.get("ok"):
        run = dict(run, events=mix_as_pair(run["events"]))
    return spec_check.check(ir, run, frozenset(cfg["free_wells"]), deck, cfg.get("not_from_paper", {}))


if __name__ == "__main__":
    res = check_run(pathlib.Path(sys.argv[1]), json.loads(pathlib.Path(sys.argv[2]).read_text()))
    for c in res["checks"]:
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['name']:34} {c['detail']}")
    for n in res.get("not_applicable", []):
        print(f"n/a   {n}")
    print("VERDICT:", "PASS" if res["passed"] else "FAIL")
