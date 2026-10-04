"""
Criteria sensitivity matrix: push deliberately broken protocols through every criterion set and
record which criteria catch which fault.

    python scripts/criteria_matrix.py [--json out.json]

Needs an Opentrons 7.5.0 environment on Python 3.10 (the Harbor image's stack):
    uv venv --python 3.10 $OT_VENV && uv pip install --python $OT_VENV/bin/python \
        opentrons==7.5.0 opentrons-shared-data==7.5.0 "pydantic<2"
$OT_VENV defaults to ~/Desktop/ot-sim-venv. The scoring side needs numpy and gymnasium.

Three families, each with ground truth ("is this a correct solution to the instruction?"):
  L1   serial dilution   -> simulator gate, WetLabEnv errors, T1-T6, proposed end-state check E1
  A12  100 uL into A1-A12 -> simulator gate, WetLabEnv errors, proposed end-state check E1
  RNA  HULP extraction   -> simulator gate, Harbor checks.py (16 checks) + critical-check cap
"""
import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
OT = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path.home() / "Desktop/ot-sim-venv"))
sys.path.insert(0, str(ROOT / "eval"))
from trace_replay import replay  # noqa: E402

HARBOR = ROOT / "tasks/L2/opentrons-rna-extraction"
spec = importlib.util.spec_from_file_location("harbor_checks", HARBOR / "tests/checks.py")
harbor_checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harbor_checks)
CRITICAL = {"48_samples_to_odd_columns", "step_order", "supernatant_removed_each_step",
            "two_500ul_ethanol_washes", "recover_70_100ul_one_well_each",
            "fresh_tip_per_sample_no_cross_contact"}  # copied from tests/grade.py CRITICAL_CHECKS


def simulate_text(src: str):
    """(ok, run log text or last error line) from the opentrons_simulate CLI."""
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d, "protocol.py")
        f.write_text(src)
        r = subprocess.run([str(OT / "bin/opentrons_simulate"), str(f)], capture_output=True, text=True, timeout=300)
    if r.returncode:
        err = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return False, err[:110]
    return True, r.stdout


# ---------------------------------------------------------------- L1: 200 uL -> two wells
L1_HEAD = '''metadata = {"apiLevel": "2.16"}
def run(p):
    tr = p.load_labware("opentrons_96_tiprack_1000ul", 1)
    pl = p.load_labware("corning_96_wellplate_360ul_flat", 2)
    rs = p.load_labware("agilent_1_reservoir_290ml", 3)
    pip = p.load_instrument("p1000_single_gen2", "right", tip_racks=[tr])
'''
# name -> (body, is a correct solution?, expected end state)
L1 = {
    "correct":              ("pip.pick_up_tip(); pip.aspirate(200, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1']); pip.drop_tip()", True),
    "other_two_wells":      ("pip.pick_up_tip(); pip.aspirate(200, rs['A1']); pip.dispense(100, pl['C5']); pip.dispense(100, pl['D7']); pip.drop_tip()", True),
    "transfer_api":         ("pip.transfer(100, rs['A1'], [pl['A1'], pl['B1']], new_tip='once')", True),
    "distribute_api":       ("pip.distribute(100, rs['A1'], [pl['A1'], pl['B1']])", True),
    "extra_mix_touch":      ("pip.pick_up_tip(); pip.aspirate(200, rs['A1']); pip.dispense(100, pl['A1']); pip.touch_tip(); pip.dispense(100, pl['B1']); pip.mix(2, 50, pl['B1']); pip.drop_tip()", True),
    "no_tip_pickup":        ("pip.aspirate(200, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1'])", False),
    "no_drop_tip":          ("pip.pick_up_tip(); pip.aspirate(200, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1'])", False),
    "aspirate_100_only":    ("pip.pick_up_tip(); pip.aspirate(100, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1']); pip.drop_tip()", False),
    "same_well_twice":      ("pip.pick_up_tip(); pip.aspirate(200, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['A1']); pip.drop_tip()", False),
    "over_pipette_max":     ("pip.pick_up_tip(); pip.aspirate(1100, rs['A1']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1']); pip.drop_tip()", False),
    "aspirate_from_plate":  ("pip.pick_up_tip(); pip.aspirate(200, pl['H12']); pip.dispense(100, pl['A1']); pip.dispense(100, pl['B1']); pip.drop_tip()", False),
}

# ---------------------------------------------------------------- A12: 100 uL -> A1..A12
A12_HEAD = '''metadata = {"apiLevel": "2.16"}
def run(p):
    tr = p.load_labware("opentrons_96_tiprack_300ul", 1)
    pl = p.load_labware("corning_96_wellplate_360ul_flat", 2)
    rs = p.load_labware("agilent_1_reservoir_290ml", 3)
    pip = p.load_instrument("p300_single_gen2", "right", tip_racks=[tr])
'''
LOOP = ("pip.pick_up_tip()\n    left = 0\n    for i in range({n}):\n        if left < {v}:\n"
        "            pip.aspirate({a}, rs['A1'])\n            left += {a}\n"
        "        pip.dispense({v}, pl.rows()[{row}][i])\n        left -= {v}\n    {tail}")
A12 = {
    "correct_reaspirates":  (LOOP.format(n=12, v=100, a=300, row=0, tail="pip.drop_tip()"), True),
    "small_aspirates":      (LOOP.format(n=12, v=100, a=150, row=0, tail="pip.drop_tip()"), True),
    "transfer_api":         ("pip.transfer(100, rs['A1'], pl.rows()[0])", True),
    "distribute_api":       ("pip.distribute(100, rs['A1'], pl.rows()[0])", True),
    "single_aspirate":      ("pip.pick_up_tip()\n    pip.aspirate(300, rs['A1'])\n    for i in range(12):\n        pip.dispense(100, pl.rows()[0][i])\n    pip.drop_tip()", False),
    "wrong_row_B":          (LOOP.format(n=12, v=100, a=300, row=1, tail="pip.drop_tip()"), False),
    "only_11_wells":        (LOOP.format(n=11, v=100, a=300, row=0, tail="pip.drop_tip()"), False),
    "wrong_volume_50":      (LOOP.format(n=12, v=50, a=300, row=0, tail="pip.drop_tip()"), False),
    "no_drop_tip":          (LOOP.format(n=12, v=100, a=300, row=0, tail="pass"), False),
    "no_tip_pickup":        (LOOP.format(n=12, v=100, a=300, row=0, tail="pip.drop_tip()").replace("pip.pick_up_tip()\n    ", "", 1), False),
}


def end_state_ok(r, family):
    """Proposed criterion E1, the specified end state, with no tip left on.
    L1 (wells not named in the instruction): exactly two wells hold 100 uL each.
    A12 (wells named): A1..A12 hold 100 uL each and nothing else is filled."""
    plate = r["plate_ul"]
    if family == "L1":
        ok = sorted(plate[plate > 0].tolist()) == [100.0, 100.0]
    else:
        want = np.zeros((8, 12))
        want[0, :] = 100
        ok = bool(np.allclose(plate, want))
    return ok and not r["tip_attached"]


def eval_family(head, family, name_, t_criteria):
    rows = []
    for name, (body, truth) in family.items():
        src = head + "    " + (body if "\n" in body else body.replace("; ", "\n    ")) + "\n"
        ok, log = simulate_text(src)
        row = {"mutant": name, "truth_valid": truth, "sim_ok": ok}
        if not ok:
            row.update(detail=log, current_pass=False, errors=[], t_failed=[], e1=None)
        else:
            r = replay(log)
            errs = sorted({e for _, e in r["errors"]})
            t_failed = [k for k, v in r["criteria"].items() if not v] if t_criteria else []
            row.update(errors=errs, t_failed=t_failed, current_pass=not errs and not t_failed,
                       e1=end_state_ok(r, name_), plate_total=float(r["plate_ul"].sum()),
                       detail="")
        rows.append(row)
    return rows


# ---------------------------------------------------------------- RNA: HULP script mutants
HULP = ROOT / "ref/hulp-rna-extraction/viral_rna_extraction_protocol.py"
RNA = {  # name -> list of (1-based line, old, new); the faults each target one named check
    "baseline":            [],
    "incubation_1min":     [(152, "protocol.delay(minutes=5)", "protocol.delay(minutes=1)")],
    "separation_1min":     [(170, "protocol.delay(minutes=4)", "protocol.delay(minutes=1)")],
    "skip_first_magnet":   [(161, "mag_mod.engage(height_from_base=7)", "pass")],
    "elution_plate_25C":   [(323, "tempdeck.set_temperature(4)", "tempdeck.set_temperature(25)")],
    "no_air_dry":          [(285, "protocol.delay(minutes=4)", "protocol.delay(seconds=5)")],
    "ethanol_wash_67uL":   [(210, "transfer(167,", "transfer(67,"), (253, "transfer(167,", "transfer(67,")],
    "one_tip_all_samples": [(133, "p1000.pick_up_tip()", "if sample == 0: p1000.pick_up_tip()"),
                            (138, "p1000.drop_tip()", "if sample == sample_number - 1: p1000.drop_tip()")],
    "supernatant_70uL":    [(187, "transfer(175,", "transfer(70,")],
}


def run_rna(patches):
    lines = HULP.read_text().splitlines(keepends=True)
    for ln, old, new in patches:
        assert old in lines[ln - 1], (ln, old)
        lines[ln - 1] = lines[ln - 1].replace(old, new)
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d, "protocol.py")
        f.write_text("".join(lines))
        r = subprocess.run([str(OT / "bin/python"), str(HARBOR / "tests/runlog.py"), str(f),
                            str(HARBOR / "environment/data/labware")], capture_output=True, text=True, timeout=600)
    out = json.loads(r.stdout.strip().splitlines()[-1])
    if not out["ok"]:
        return {"sim_ok": False, "detail": out["error"][-110:]}
    res = harbor_checks.analyze(out["events"])
    failed = [c["name"] for c in res["checks"] if not c["pass"]]
    return {"sim_ok": True, "passed": res["checks_passed"], "total": res["checks_total"], "failed": failed,
            "critical_failed": sorted(set(failed) & CRITICAL), "events": len(out["events"])}


def run_all():
    return {"L1": eval_family(L1_HEAD, L1, "L1", True), "A12": eval_family(A12_HEAD, A12, "A12", False),
            "RNA": {k: run_rna(v) for k, v in RNA.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    out = run_all()
    for fam in ("L1", "A12"):
        print(f"\n== {fam}: current criteria vs ground truth  (E1 = proposed end-state check)")
        print(f"{'mutant':22} {'valid?':6} {'sim':5} {'current':8} {'E1':5} outcome   errors / failed T / sim error")
        for r in out[fam]:
            cur = r["current_pass"]
            outcome = ("ok" if cur == r["truth_valid"] else ("FALSE NEG" if r["truth_valid"] else "FALSE POS"))
            e1 = "-" if r["e1"] is None else ("pass" if r["e1"] else "fail")
            print(f"{r['mutant']:22} {str(r['truth_valid']):6} {'ok' if r['sim_ok'] else 'FAIL':5} "
                  f"{'pass' if cur else 'fail':8} {e1:5} {outcome:9} {','.join(r['errors'] + r['t_failed']) or r['detail']}")
    print("\n== RNA: Harbor checks.py on HULP-script mutants (deterministic part only; the LLM judge was not run)")
    for k, r in out["RNA"].items():
        if not r["sim_ok"]:
            print(f"{k:20} SIM FAIL {r['detail']}")
            continue
        cap = " -> reward capped at 0.3" if r["critical_failed"] else ""
        print(f"{k:20} {r['passed']}/{r['total']}  failed={r['failed'] or '-'}  critical={r['critical_failed'] or '-'}{cap}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
