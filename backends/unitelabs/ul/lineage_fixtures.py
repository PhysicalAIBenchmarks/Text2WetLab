"""Pin what the SDK's lineage stream and the adapter make of every reference protocol, so a change in either shows up.

    $UL_PYTHON ul/lineage_fixtures.py [--write] [--jobs 6]

Runs every reference (references/<device>/<task>.py) with runner.py under the SDK, checks every lineage event
against the SDK's payload contract (`unitelabs.sdk.automate.lineage.validate_event`), turns the stream into run-log
events (lineage_events.py) and compares a digest of those events with tests/fixtures/lineage/digests.json. Small runs
are also pinned in full (tests/fixtures/lineage/<device>__<task>.json: the lineage stream, entity map, comments and
the expected events), which tests/test_lineage_events.py replays without the SDK. Tip identifiers are random per
run, so they are renamed t1, t2, ... by first appearance before anything is pinned.

`--write` rewrites the fixtures instead of comparing; review the diff like any other change of expected output.
Needs the SDK: run it with UL_PYTHON (see paths.py). Exit 1 on any contract violation or digest mismatch.
"""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ul"))
import lineage_events  # noqa: E402

FIXTURES = ROOT / "tests/fixtures/lineage"
FULL_MAX_EVENTS = 100            # pin runs up to this many lineage events in full; larger ones by digest only


def normalize_tips(lineage: list[dict]) -> list[dict]:
    names: dict[str, str] = {}
    out = []
    for e in lineage:
        extras = e.get("extras")
        if extras and "tip" in extras:
            e = dict(e, extras=dict(extras, tip=names.setdefault(extras["tip"], f"t{len(names) + 1}")))
        out.append(e)
    return out


def digest(events: list[dict]) -> str:
    return hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()[:16]


def record(pair: tuple[str, str]) -> dict:
    """Run one reference; its normalized lineage, entity map, comments and adapter events, or the run's error."""
    import runner
    from unitelabs.sdk import Operation
    from unitelabs.sdk.automate.lineage import validate_event

    device, task = pair
    result = runner.main(device, str(ROOT / "references" / device / f"{task}.py"), raw=True)
    if not result["ok"]:
        return {"pair": pair, "error": result["error"]}
    lineage = normalize_tips(result["lineage"])
    problems = [f"event {i} ({e['operation']}): {p}" for i, e in enumerate(lineage)
                for p in validate_event(Operation(e["operation"]), e["inputs"], e["outputs"], e.get("extras"),
                                        event_type=e.get("type", "lineage"))]
    comments = [list(c) for c in result["lineage_comments"]]
    events, errors = lineage_events.to_events(lineage, result["entities"], [tuple(c) for c in comments])
    return {"pair": pair, "lineage": lineage, "entities": result["entities"], "comments": comments, "events": events,
            "errors": errors, "problems": problems}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    pairs = sorted((p.parent.name, p.stem) for p in (ROOT / "references").glob("*/*.py"))
    with concurrent.futures.ProcessPoolExecutor(args.jobs) as pool:
        runs = list(pool.map(record, pairs))
    if args.write:
        FIXTURES.mkdir(parents=True, exist_ok=True)
    digests_path = FIXTURES / "digests.json"
    pinned = json.loads(digests_path.read_text()) if digests_path.exists() else {}
    digests, bad = {}, 0
    for run in runs:
        name = "__".join(run["pair"])
        if "error" in run:
            print(f"FAIL {name}: the reference did not run: {run['error']}")
            bad += 1
            continue
        for problem in run["problems"][:5]:
            print(f"FAIL {name}: lineage contract: {problem}")
        bad += bool(run["problems"])
        digests[name] = {"lineage": len(run["lineage"]), "events": len(run["events"]), "sha256": digest(run["events"])}
        full = len(run["lineage"]) <= FULL_MAX_EVENTS
        if args.write:
            if full:
                fixture = {k: run[k] for k in ("lineage", "entities", "comments", "events")}
                (FIXTURES / f"{name}.json").write_text(json.dumps(fixture, indent=1, sort_keys=True) + "\n")
        elif pinned.get(name) != digests[name]:
            print(f"FAIL {name}: adapter output changed: pinned {pinned.get(name)}, now {digests[name]}")
            bad += 1
    if args.write:
        digests_path.write_text(json.dumps(digests, indent=1, sort_keys=True) + "\n")
        print(f"wrote {len(digests)} digests and {sum(1 for r in runs if len(r.get('lineage', [])) <= FULL_MAX_EVENTS)} full fixtures")
    else:
        print(f"{len(digests) - bad} of {len(pairs)} references match their pinned lineage")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
