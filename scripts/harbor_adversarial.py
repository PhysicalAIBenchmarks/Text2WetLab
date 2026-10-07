"""Try to cheat each generated Harbor grader, and report which attempts score full marks.

    python scripts/harbor_adversarial.py [--out results/adversarial.json]

For every IR task the reference solution is the control (must score 1.0). Each attack is a small edit of it, or a
protocol written to fool the grader. An attack that is supposed to be caught and scores 1.0 is a hole in the grader.
Runs the generated tests/grade.py exactly as Harbor does, with local paths (needs the Opentrons venv in OT_VENV).
--data TASK=DIR points a task at a local copy of its /data (the ecoli hard task fetches its paper at image build time).
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OT_VENV = pathlib.Path(os.environ.get("OT_VENV", ROOT / ".venv-ot"))


def labels(code):
    return re.findall(r"load_labware\('([^']+)', (\d+), label='([^']+)'\)", code)


def attacks(code: str, deck: dict) -> dict[str, str | None]:
    """name -> modified protocol, or None when the attack does not apply to this task."""
    lw = labels(code)
    transfers = [i for i, ln in enumerate(code.splitlines()) if ".transfer(" in ln]
    lines = code.splitlines()
    out: dict[str, str | None] = {"control_reference_solution": code}
    for level in ("2.14", "2.15"):     # a correct protocol must score the same at every allowed API level (the log format changes)
        out[f"control_api_{level.replace('.', '_')}"] = code.replace("'apiLevel': '2.13'", f"'apiLevel': '{level}'")
    out["empty_protocol"] = "metadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n    pass\n"
    out["drop_last_transfer"] = "\n".join(l for i, l in enumerate(lines) if i != transfers[-1]) + "\n" if transfers else None
    out["halve_volumes"] = re.sub(r"\.transfer\(([\d.]+),", lambda m: f".transfer({float(m[1]) / 2:g},", code) if transfers else None
    out["double_volumes"] = re.sub(r"\.transfer\(([\d.]+),", lambda m: f".transfer({min(float(m[1]) * 2, 300):g},", code) if transfers else None
    out["no_labels"] = re.sub(r", label='[^']+'", "", code)
    same = [(a, b) for a in lw for b in lw if a[0] == b[0] and a[2] < b[2]]
    if same:
        a, b = same[0]
        out["swap_two_labels"] = code.replace(f"label='{a[2]}'", "label='@@'").replace(f"label='{b[2]}'", f"label='{a[2]}'").replace("label='@@'", f"label='{b[2]}'")
    else:
        out["swap_two_labels"] = None
    res = [x for x in lw if "reservoir" in x[0]]
    out["reservoir_labelled_as_plate_kind"] = code.replace(f"load_labware('{res[0][0]}'", "load_labware('corning_96_wellplate_360ul_flat'") if res else None
    out["wrong_slot"] = code.replace(f"load_labware('{lw[0][0]}', {lw[0][1]}, label", f"load_labware('{lw[0][0]}', 9, label", 1) if lw and lw[0][1] != "9" else None
    out["duplicate_label"] = code.replace("protocol.load_instrument", f"protocol.load_labware('{lw[0][0]}', 8, label='{lw[0][2]}')\n    protocol.load_instrument", 1) if lw else None
    out["finish_holding_a_tip"] = code.rstrip("\n") + "\n    p300.pick_up_tip()\n"
    first, second = (lw[0][2], lw[1][2]) if len(lw) > 1 else (None, None)
    out["extra_liquid_into_target"] = (code.rstrip("\n") + f"\n    p300.pick_up_tip(); p300.aspirate(30, lw_{first}['A1']); p300.dispense(30, lw_{second}['H12']); p300.drop_tip()\n") if first else None
    out["share_one_tip_across_sources"] = re.sub(r"new_tip='always'", "new_tip='once'", code) if "new_tip='always'" in code else None
    out["comment_spoof_only"] = ("metadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n"
                                 + "".join(f"    protocol.comment('Dispensing 100.0 uL into A{i} of {lw[0][2] if lw else 'x'} on 1')\n" for i in range(1, 13)))
    out["forged_result_then_systemexit"] = ("from opentrons import protocol_api\nimport json\n\nmetadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n"
                                            "    print(json.dumps({'ok': True, 'events': [], 'labware': {}}))\n    raise SystemExit(0)\n")
    out["import_os_and_exit"] = "import os\nmetadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n    os._exit(0)\n"
    out["read_the_answer_key"] = "metadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n    protocol.comment(open('/tests/ir.json').read())\n"
    out["patch_the_log_parser"] = "from opentrons import protocol_api\nmetadata = {'apiLevel': '2.13'}\nprotocol_api.ProtocolContext.comment = None\n\n\ndef run(protocol):\n    pass\n"
    out["dunder_escape"] = "metadata = {'apiLevel': '2.13'}\n\n\ndef run(protocol):\n    protocol.__class__.__mro__\n"
    return out


def simulate(code: str) -> str:
    """The simulator's run log, used to spot attacks that leave the protocol's behaviour unchanged."""
    with tempfile.TemporaryDirectory() as d:
        proto = pathlib.Path(d, "protocol.py")
        proto.write_text(code)
        r = subprocess.run([str(OT_VENV / "bin/opentrons_simulate"), str(proto)], capture_output=True, text=True, timeout=600)
        return r.stdout if r.returncode == 0 else f"failed: {r.returncode}"


def run_one(task: pathlib.Path, name: str, code: str, data: pathlib.Path) -> dict:
    h = task
    with tempfile.TemporaryDirectory() as d:
        proto = pathlib.Path(d, "protocol.py")
        proto.write_text(code)
        env = dict(os.environ, TESTS_DIR=str(h / "tests"), PROTOCOL_PATH=str(proto), VERIFIER_OUT=d,
                   OT_PYTHON=str(OT_VENV / "bin/python"), RUNLOG=str(h / "tests/runlog.py"),
                   DATA_DIR=str(data), SKIP_JUDGE="1")  # attacks target the deterministic layers; the judge is not a defence
        r = subprocess.run([sys.executable, str(h / "tests/grade.py")], capture_output=True, text=True, env=env, timeout=900)
        try:
            rec = json.loads(pathlib.Path(d, "result.json").read_text())
        except Exception:
            return {"reward": None, "error": (r.stderr or r.stdout)[-300:]}
    failed = [c["name"] for c in rec.get("checks", []) if not c["pass"]]
    return {"reward": rec["rewards"]["reward"], "failed_checks": failed, "lint": rec.get("lint", []), "error": rec.get("error", "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results/adversarial.json"))
    ap.add_argument("--tasks", nargs="*")
    ap.add_argument("--data", nargs="*", default=[])
    a = ap.parse_args()
    data_for = dict(x.split("=", 1) for x in a.data)
    results = {}
    for task in sorted((ROOT / "tasks").iterdir()):
        h = task
        if not (h / "tests/deck.json").exists() or (a.tasks and task.name not in a.tasks):
            continue
        code = (h / "solution/protocol.py").read_text()
        deck = json.loads((h / "tests/deck.json").read_text())
        results[task.name] = {}
        reference_run = simulate(code)
        for name, mutated in attacks(code, deck).items():
            if mutated is None:
                results[task.name][name] = {"skipped": "does not apply to this task"}
                continue
            # the printed run names wells by label, not labware type, so a no-op must also load the same labware
            if (not name.startswith("control") and not reference_run.startswith("failed") and labels(mutated) == labels(code)
                    and simulate(mutated) == reference_run):
                # e.g. new_tip='once' on a transfer() of one well: same tips, same liquid moves, so 1.0 is the right score
                results[task.name][name] = {"skipped": "no-op: same simulated run as the reference"}
                continue
            results[task.name][name] = run_one(task, name, mutated, pathlib.Path(data_for.get(task.name, h / "environment/data")))
            r = results[task.name][name]
            print(f"{task.name:34} {name:36} reward={r['reward']}  {'| ' + ','.join(r.get('failed_checks', []))[:70] if r.get('failed_checks') else ''}{' | lint:' + r['lint'][0][:40] if r.get('lint') else ''}", flush=True)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(results, indent=1))
    holes = [(t, n) for t, rs in results.items() for n, r in rs.items() if not n.startswith("control") and r.get("reward") == 1.0]
    broken = [(t, n) for t, rs in results.items() for n, r in rs.items() if n.startswith("control") and r.get("reward") != 1.0]
    print(f"\nHOLES (attack scored 1.0): {len(holes)} {holes}\nCONTROL FAILURES: {len(broken)} {broken}")


if __name__ == "__main__":
    main()
