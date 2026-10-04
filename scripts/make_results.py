"""Collect everything about every task into results/: per-task folders and one total.

    python scripts/make_results.py [--viz]

results/<task>/result.json     oracle reward, adversarial summary, every agent trial (model, reward, cost, failed checks)
results/<task>/ir_2d.gif       the IR drawn in 2D (eval/ir_viz.py)                            [IR tasks]
results/<task>/ir_3d.mp4,.gif,_frames.png   the IR in 3D with fill colour and physics strip (eval/ir_mujoco.py)   [IR tasks]
results/<task>/oracle_run.mp4  the reference solution as the simulator ran it, in the opentrons-mujoco-viz scene
results/<task>/best_run.mp4    the best agent protocol, same renderer
results/summary.json, SUMMARY.md   totals across tasks and models
Raw Harbor job folders (trajectories) are in results/harbor-jobs/, which is not committed.

Agent trials use pass@1 (single attempt). The job folder prefix is "agent-<model>-<task>".
v2 (pass@3 / best-of-3) runs are archived in results/harbor-jobs/ but not collected here.
"""
import argparse
import glob
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
PY = sys.executable
OT_ENV = dict(os.environ, OT_VENV=os.environ.get("OT_VENV", str(pathlib.Path.home() / "Desktop/ot-sim-venv")))


def jobs(pattern):
    for d in sorted(glob.glob(str(R / "harbor-jobs" / pattern))):
        for f in sorted(glob.glob(d + "/*/result.json")):
            r = json.loads(pathlib.Path(f).read_text())
            if r.get("verifier_result"):
                yield pathlib.Path(d).name, pathlib.Path(f).parent, r


def trial_row(job, trial_dir, r):
    v = r["verifier_result"]["rewards"]
    ag = r.get("agent_result") or {}
    failed = []
    vr = trial_dir / "verifier/result.json"
    if vr.exists():
        rec = json.loads(vr.read_text())
        failed = [c["name"] for c in rec.get("checks", []) if not c["pass"]] + [f"lint: {x}" for x in rec.get("lint", [])[:2]]
    elif (trial_dir / "verifier/judge.json").exists():
        j = json.loads((trial_dir / "verifier/judge.json").read_text())
        failed = [k for k, x in (j.get("judge") or {}).get("scores", {}).items() if x < 1] + j.get("critical_failures", [])
    return {"job": job, "reward": v.get("reward"), "sim_pass": v.get("sim_pass"), "cost_usd": round(ag.get("cost_usd") or 0, 4),
            "failed": failed, "protocol": str(trial_dir / "verifier/protocol.py") if (trial_dir / "verifier/protocol.py").exists() else None}


def sh(*cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, env=OT_ENV, **kw)
    if r.returncode:
        print("   !!", " ".join(cmd[-3:]), r.stderr.strip().splitlines()[-1:] or r.stdout.strip().splitlines()[-1:])
    return r.returncode == 0


def frames_png(mp4, out):
    import imageio.v3 as iio
    fr = list(iio.imiter(mp4))
    pick = [fr[0], fr[len(fr) // 2], fr[-1]]
    import numpy as np
    iio.imwrite(out, np.concatenate(pick, axis=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--viz", action="store_true", help="(re)render the videos")
    a = ap.parse_args()
    adv = json.loads((R / "adversarial.json").read_text()) if (R / "adversarial.json").exists() else {}
    summary = {}
    for task in sorted((ROOT / "tasks").iterdir()):
        out = R / task.name
        out.mkdir(parents=True, exist_ok=True)
        h, ir = task / "harbor", task / "public/ir.json"
        res = {"task": task.name, "grader": "LLM judge + 16 checks" if not ir.exists() else "deterministic end-state checker"}
        res["oracle"] = [trial_row(j, d, r) for j, d, r in jobs(f"oracle-{task.name}")]
        res["trials"] = [trial_row(j, d, r) for j, d, r in jobs(f"agent-*-{task.name}")]
        res["adversarial"] = {n: x.get("reward") for n, x in adv.get(task.name, {}).items()}
        if a.viz:
            if ir.exists():
                sh(PY, str(ROOT / "eval/ir_viz.py"), str(ir), "-o", str(out / "ir_2d.gif"))
                sh(PY, str(ROOT / "eval/ir_mujoco.py"), str(ir), "-o", str(out / "ir_3d.mp4"))
            labware = str(h / "environment/data/labware") if (h / "environment/data/labware").exists() else None
            for name, proto in (("oracle_run", h / "solution/protocol.py"),):
                cmd = [PY, str(ROOT / "scripts/render_run.py"), str(proto), str(out / f"{name}.mp4")] + (["--labware", labware] if labware else [])
                if sh(*cmd):
                    frames_png(out / f"{name}.mp4", out / f"{name}_frames.png")
            best = max((t for t in res["trials"] if t["protocol"]), key=lambda t: (t["reward"] or 0, -t["cost_usd"]), default=None)
            if best:
                cmd = [PY, str(ROOT / "scripts/render_run.py"), best["protocol"], str(out / "best_run.mp4")] + (["--labware", labware] if labware else [])
                if sh(*cmd):
                    frames_png(out / "best_run.mp4", out / "best_run_frames.png")
                    res["best_trial"] = {k: best[k] for k in ("job", "reward", "cost_usd")}
        (out / "result.json").write_text(json.dumps(res, indent=1))
        summary[task.name] = res
    # Job names are "agent-<model>-<task>"; extract model as everything between the first "-" and the task suffix.
    models = sorted({"-".join(t["job"].split("-")[1:4]) for r in summary.values() for t in r["trials"]})
    lines = ["# Results", "", "Harbor trials on Docker (colima), Claude Code agent, pass@1 (single attempt per task), grader as committed.", "",
             "| Task | Grader | Oracle | " + " | ".join(f"{m} mean (n)" for m in models) + " | Attacks that scored 1.0 |", "|---|---|---|" + "---|" * len(models) + "---|"]
    total = {m: [] for m in models}
    for t, r in summary.items():
        row = []
        for m in models:
            xs = [x["reward"] for x in r["trials"] if f"-{m}-" in x["job"] and x["reward"] is not None]
            total[m] += xs
            row.append(f"{sum(xs) / len(xs):.3f} ({len(xs)})" if xs else "-")
        o = r["oracle"][-1]["reward"] if r["oracle"] else "-"
        holes = [n for n, v in r["adversarial"].items() if not n.startswith("control") and v == 1.0]
        lines.append(f"| `{t}` | {r['grader']} | {o} | " + " | ".join(row) + f" | {len(holes) if r['adversarial'] else 'n/a'} |")
    lines += ["", "**All tasks:** " + "; ".join(f"{m} mean {sum(v) / len(v):.3f} over {len(v)} trials" for m, v in total.items() if v), ""]
    (R / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (R / "summary.json").write_text(json.dumps(summary, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
