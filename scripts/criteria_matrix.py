"""
Criteria sensitivity matrix: push deliberately broken protocols through the checker and record
which criteria catch which fault, against ground truth ("is this a correct solution?").

    python scripts/criteria_matrix.py [--json out.json]

Needs an Opentrons 7.5.0 environment on Python 3.10 (the Harbor image's stack), see eval/spec_check.py.

  split / a1-a12   eval/spec_check.py (generic rules + end state derived from the task's IR)
  rna              the Harbor task's checks.py (16 checks) + critical-check cap, on mutants of the
                   authors' script (the LLM judge is not run)
"""
import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval")]
from paper2protocol.models import Protocol  # noqa: E402
from spec_check import check, free_wells, simulate  # noqa: E402

HARBOR = ROOT / "tasks/opentrons-rna-extraction"
spec = importlib.util.spec_from_file_location("harbor_checks", HARBOR / "tests/checks.py")
harbor_checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harbor_checks)
CRITICAL = {"48_samples_to_odd_columns", "step_order", "supernatant_removed_each_step",
            "two_500ul_ethanol_washes", "recover_70_100ul_one_well_each",
            "fresh_tip_per_sample_no_cross_contact"}  # copied from tests/grade.py CRITICAL_CHECKS


# ---------------------------------------------------------------- split: 200 uL -> two wells
SPLIT_HEAD = '''metadata = {"apiLevel": "2.16"}
def run(p):
    tr = p.load_labware("opentrons_96_tiprack_1000ul", 1)
    pl = p.load_labware("corning_96_wellplate_360ul_flat", 2)
    rs = p.load_labware("agilent_1_reservoir_290ml", 3)
    pip = p.load_instrument("p1000_single_gen2", "right", tip_racks=[tr])
'''
# name -> (body, is a correct solution?, expected end state)
SPLIT = {
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

# ---------------------------------------------------------------- a1-a12: 100 uL -> A1..A12
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


def eval_task(head, family, task):
    task_dir = ROOT / "tasks" / task
    proto = Protocol.model_validate_json((task_dir / "ir.json").read_text())
    free = free_wells(task_dir)
    rows = []
    for name, (body, truth) in family.items():
        src = head + "    " + (body if "\n" in body else body.replace("; ", "\n    ")) + "\n"
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d, "protocol.py")
            f.write_text(src)
            res = check(proto, simulate(str(f)), free)
        failed = [c["name"] for c in res["checks"] if not c["pass"]]
        detail = next((c["detail"] for c in res["checks"] if c["name"] == "simulator_ran" and not c["pass"]), "")
        rows.append({"mutant": name, "truth_valid": truth, "verdict_pass": res["passed"], "failed": failed,
                     "sim_error": detail[:100]})
    return rows


# ---------------------------------------------------------------- RNA: HULP script mutants
HULP = ROOT / "references/hulp-rna-extraction/viral_rna_extraction_protocol.py"
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
        out = simulate(str(f), str(HARBOR / "environment/data/labware"))
    if not out["ok"]:
        return {"sim_ok": False, "detail": out["error"][-110:]}
    res = harbor_checks.analyze(out["events"])
    failed = [c["name"] for c in res["checks"] if not c["pass"]]
    return {"sim_ok": True, "passed": res["checks_passed"], "total": res["checks_total"], "failed": failed,
            "critical_failed": sorted(set(failed) & CRITICAL), "events": len(out["events"])}


def run_all():
    return {"split-200ul-two-wells": eval_task(SPLIT_HEAD, SPLIT, "split-200ul-two-wells"),
            "a1-a12-100ul": eval_task(A12_HEAD, A12, "a1-a12-100ul"),
            "rna-extraction": {k: run_rna(v) for k, v in RNA.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    out = run_all()
    wrong = 0
    for task in ("split-200ul-two-wells", "a1-a12-100ul"):
        print(f"\n== {task}: spec_check verdict vs ground truth")
        print(f"{'mutant':22} {'valid?':6} {'verdict':8} outcome    failed checks")
        for r in out[task]:
            ok = r["verdict_pass"] == r["truth_valid"]
            wrong += not ok
            outcome = "ok" if ok else ("FALSE NEG" if r["truth_valid"] else "FALSE POS")
            print(f"{r['mutant']:22} {str(r['truth_valid']):6} {'pass' if r['verdict_pass'] else 'fail':8} {outcome:10} "
                  f"{', '.join(r['failed']) or '-'}{'  [' + r['sim_error'] + ']' if r['sim_error'] else ''}")
    print(f"\nmisjudged protocols: {wrong}")
    print("\n== rna-extraction: Harbor checks.py on mutants of the authors' script (deterministic part only)")
    for k, r in out["rna-extraction"].items():
        if not r["sim_ok"]:
            print(f"{k:20} SIM FAIL {r['detail']}")
            continue
        cap = " -> reward capped at 0.3" if r["critical_failed"] else ""
        print(f"{k:20} {r['passed']}/{r['total']}  failed={r['failed'] or '-'}  critical={r['critical_failed'] or '-'}{cap}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
