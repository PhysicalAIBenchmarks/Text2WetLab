"""
Reproduce the pipeline end to end from a clean checkout and write a report with no timestamps or
absolute paths, so two runs can be compared byte for byte.

    uv sync --group dev --group eval
    OT_VENV=<py3.10 venv with opentrons==7.5.0> uv run python scripts/reproduce.py --out report.json

Stages (what is, and is not, reproducible):
  ir          every IR validates; check.py and render.py re-run offline and are compared with the
              committed check.json / protocol.txt. The LLM stages (paper -> IR) are NOT re-run: they
              need an API key and the response cache is not committed.
  simulate    every reference / fixture script is simulated on Harbor's stack (Opentrons 7.5.0,
              Python 3.10) with Harbor's own runlog.py; failures are classified.
  criteria    scripts/criteria_matrix.py (faulty protocols x criteria sets).
  render      2D + 3D renders of three IRs, compared by decoded-frame hash.
  provenance  PROVENANCE.csv regenerated from git + GitHub and compared with the committed copy.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "scripts")]
OT = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path.home() / "Desktop/ot-sim-venv"))
HARBOR = ROOT / "tasks/opentrons-rna-extraction/harbor"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def stage_ir():
    from paper2protocol.check import check
    from paper2protocol.models import Protocol
    from paper2protocol.render import render

    out = {}
    for ir in sorted(ROOT.glob("tasks/*/public/ir.json")) + sorted(ROOT.glob("sources/*/pipeline/exp*/protocol.json")):
        proto = Protocol.model_validate_json(ir.read_text())
        issues = [i.model_dump() for i in check(proto)]
        row = {"sha": sha(ir.read_bytes()), "steps": len(proto.steps), "check_issues": len(issues)}
        d = ir.parent
        if (d / "check.json").exists():
            row["check_json_reproduces"] = json.loads((d / "check.json").read_text()) == issues
        if (d / "protocol.txt").exists():
            row["protocol_txt_reproduces"] = (d / "protocol.txt").read_text().endswith(render(proto))
        out[str(ir.relative_to(ROOT))] = row
    return out


def classify(err: str) -> str:
    for key, label in (("downgrade", "needs removed Opentrons API v1"),
                       ("not supported by this robot software", "needs a newer API level than 7.5.0 supports"),
                       ("Custom Labware", "needs a custom labware definition that is not in the repo"),
                       ("RUNTIME_PARAMETER", "needs a runtime-parameter CSV")):
        if key in err:
            return label
    from spec_check import error_kind

    return error_kind(err)


def stage_simulate():
    from spec_check import simulate

    harbor_lab = str(HARBOR / "environment/data/labware")
    jobs = [("tasks/split-200ul-two-wells/private/solution/protocol.py", None),
            ("tests/fixtures/a1_a12/good_protocol.py", None),
            ("tests/fixtures/a1_a12/bad_protocol.py", None),
            ("sources/hulp-rna-extraction/code/viral_rna_extraction_protocol.py", harbor_lab),
            ("tasks/opentrons-rna-extraction/harbor/solution/protocol.py", harbor_lab)]
    jobs += [(str(p.relative_to(ROOT)), None) for p in sorted((ROOT / "sources/dna-bot/code/scripts").glob("*.py"))]
    jobs += [(str(p.relative_to(ROOT)), str(ROOT / "sources/botany/code/labware")) for p in sorted((ROOT / "sources/botany/code/scripts").glob("*.py"))]
    jobs += [(str(p.relative_to(ROOT)), None) for p in sorted((ROOT / "sources/transporter-screening/code/scripts").glob("*.py"))]
    out, events = {}, {}
    for rel, lab in jobs:
        j = simulate(str(ROOT / rel), lab)
        if j["ok"]:
            events[rel] = j["events"]
            out[rel] = {"ok": True, "commands": j["n_commands"], "events": dict(sorted(collections.Counter(e["kind"] for e in j["events"]).items())),
                        "events_sha": sha(json.dumps(j["events"], sort_keys=True).encode())}
        else:
            out[rel] = {"ok": False, "why": classify(j["error"])}
    import importlib.util

    spec = importlib.util.spec_from_file_location("slowpoke_assemble", ROOT / "sources/slowpoke/code/assemble.py")
    assemble = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assemble)
    with tempfile.TemporaryDirectory() as d:  # the authors' generators, minus the GUI, bind the shipped CSVs into the templates
        for name in assemble.JOBS:
            f = pathlib.Path(d, name)
            f.write_text(assemble.build(name))
            j = simulate(str(f), None)
            rel = f"sources/slowpoke/code (assembled) {name}"
            if j["ok"]:
                out[rel] = {"ok": True, "commands": j["n_commands"], "events": dict(sorted(collections.Counter(e["kind"] for e in j["events"]).items())),
                            "events_sha": sha(json.dumps(j["events"], sort_keys=True).encode())}
            else:
                out[rel] = {"ok": False, "why": classify(j["error"])}
    h, s = "sources/hulp-rna-extraction/code/viral_rna_extraction_protocol.py", "tasks/opentrons-rna-extraction/harbor/solution/protocol.py"
    out["_harbor_solution_trace_equals_author_script_trace"] = bool(h in events and s in events and events[h] == events[s])
    return out


def stage_criteria():
    import criteria_matrix

    res = criteria_matrix.run_all()
    return {"sha": sha(json.dumps(res, sort_keys=True).encode()), "result": res}


def stage_render():
    import numpy as np
    try:
        import imageio
        import ir_mujoco
        import ir_viz
        from paper2protocol.models import Protocol
    except Exception as e:  # missing optional dependency
        return {"skipped": f"{type(e).__name__}: {e}"}
    out = {}
    for rel in ("tasks/split-200ul-two-wells/public/ir.json", "tasks/a1-a12-100ul/public/ir.json",
                "tasks/ecoli-heat-shock-transformation/public/ir.json"):
        proto = Protocol.model_validate_json((ROOT / rel).read_text())
        row = {}
        with tempfile.TemporaryDirectory() as d:
            gif = pathlib.Path(d, "x.gif")
            ir_viz.render(proto, gif)
            frames = imageio.mimread(gif, memtest=False)
            row["2d"] = {"frames": len(frames), "sha": sha(b"".join(np.asarray(f).tobytes() for f in frames))}
        try:
            *_, frames3d, track = ir_mujoco.build_frames(proto)
            pick = [frames3d[0][0], frames3d[len(frames3d) // 2][0], frames3d[-1][0]]
            row["3d"] = {"frames": len(frames3d), "sha": sha(b"".join(f.tobytes() for f in pick)),
                         "collisions": int(track["collision"].sum()), "max_tip_ul": float(track["held"].max())}
        except Exception as e:
            row["3d"] = {"skipped": f"{type(e).__name__}: {str(e)[:60]}"}
        out[rel] = row
    return out


def stage_provenance():
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode:
        return {"skipped": "gh not authenticated"}
    with tempfile.TemporaryDirectory() as d:
        regen = pathlib.Path(d, "regen.csv")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/make_provenance_csv.py"), "--out", str(regen)],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode:
            return {"skipped": r.stderr.strip()[-120:]}
        new = {x["record_id"]: x for x in csv.DictReader(open(regen))}
    old = {x["record_id"]: x for x in csv.DictReader(open(ROOT / "PROVENANCE.csv"))}
    volatile = {"branches_with_commit"}  # changes whenever someone creates a branch
    diffs = []
    for rid in sorted(set(old) | set(new)):
        if rid not in old or rid not in new:
            diffs.append({"record": rid, "diff": "only in " + ("regenerated" if rid in new else "committed")})
            continue
        for col in old[rid]:
            if col not in volatile and old[rid][col] != new[rid][col]:
                diffs.append({"record": rid, "column": col, "committed": old[rid][col][:60], "regenerated": new[rid][col][:60]})
    byte_ok = [x for x in new.values() if x["record_type"] == "reference" and x["upstream_repo"]]
    return {"rows": len(new), "references_byte_identical_to_upstream": sum(x["verified_vs_upstream"] == "byte-identical" for x in byte_ok),
            "references_checked": len(byte_ok), "differs_from_committed_csv": diffs}


STAGES = {"ir": stage_ir, "simulate": stage_simulate, "criteria": stage_criteria, "render": stage_render,
          "provenance": stage_provenance}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--skip", nargs="*", default=[], choices=list(STAGES))
    a = ap.parse_args()
    report = {}
    for name, fn in STAGES.items():
        if name in a.skip:
            continue
        print(f"[{name}] ...", flush=True)
        report[name] = fn()
    pathlib.Path(a.out).write_text(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
