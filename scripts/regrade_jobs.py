"""Regrade saved Harbor trials with the current graders, without re-running any agent.

    python scripts/regrade_jobs.py JOB_DIR [JOB_DIR ...] [--judge] [--data TASK=DIR ...] [--out DIR]

Each trial's graded protocol (verifier/protocol.py) goes back through tasks/<task>/tests/grade.py outside Docker.
Without --judge only the deterministic layers run (SKIP_JUDGE=1, free). With --judge the LLM judge runs too, but only for
trials whose deterministic result changed; the others keep their original judge reward. Prints old vs new per trial.
--data points a task at a local copy of its /data (e.g. a paper fetched at image build time).
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OT = pathlib.Path(os.environ.get("OT_VENV", ROOT / ".venv-ot")) / "bin/python"


def grade(task: pathlib.Path, protocol: pathlib.Path, data: pathlib.Path, judge: bool, out: pathlib.Path) -> dict:
    env = dict(os.environ, TESTS_DIR=str(task / "tests"), PROTOCOL_PATH=str(protocol), VERIFIER_OUT=str(out),
               OT_PYTHON=str(OT), RUNLOG=str(task / "tests/runlog.py"), DATA_DIR=str(data))
    if not judge:
        env["SKIP_JUDGE"] = "1"
    if (data / "labware").is_dir():
        env["LABWARE_DIR"] = str(data / "labware")
    subprocess.run([sys.executable, str(task / "tests/grade.py")], capture_output=True, text=True, env=env, timeout=900)
    rec = next((json.loads((out / n).read_text()) for n in ("result.json", "judge.json") if (out / n).exists()), {})
    checks = rec.get("checks")
    if isinstance(checks, dict):
        checks = checks.get("checks", [])
    return {"rewards": json.loads((out / "reward.json").read_text()) if (out / "reward.json").exists() else {},
            "failed": sorted(c["name"] for c in checks or [] if not c["pass"]), "judge": rec.get("judge") or {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+", type=pathlib.Path)
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--data", nargs="*", default=[])
    ap.add_argument("--out", type=pathlib.Path)
    a = ap.parse_args()
    data_for = dict(x.split("=", 1) for x in a.data)
    rows = []
    for job in a.jobs:
        for f in sorted(job.glob("*/result.json")):
            trial = json.loads(f.read_text())
            name = trial["task_name"].split("/")[-1]
            old = (trial.get("verifier_result") or {}).get("rewards") or {}
            protocol = f.parent / "verifier/protocol.py"
            if trial.get("exception_info") or not protocol.exists():
                rows.append({"job": job.name, "task": name, "skipped": (trial.get("exception_info") or {}).get("exception_type", "no protocol")})
                continue
            old_rec = next((json.loads((f.parent / "verifier" / n).read_text()) for n in ("result.json", "judge.json")
                            if (f.parent / "verifier" / n).exists()), {})
            old_checks = old_rec.get("checks")
            if isinstance(old_checks, dict):
                old_checks = old_checks.get("checks", [])
            old_failed = sorted(c["name"] for c in old_checks or [] if not c["pass"])
            task = ROOT / "tasks" / name
            data = pathlib.Path(data_for.get(name, task / "environment/data"))
            with tempfile.TemporaryDirectory() as tmp:
                new = grade(task, protocol, data, False, pathlib.Path(tmp))
            changed = new["failed"] != old_failed or new["rewards"].get("deterministic_reward") != old.get("deterministic_reward")
            row = {"job": job.name, "task": name, "old": old, "old_failed": old_failed, "new_det": new["rewards"],
                   "new_failed": new["failed"], "changed": changed}
            if changed and a.judge:
                out = (a.out / job.name / name) if a.out else pathlib.Path(tempfile.mkdtemp())
                out.mkdir(parents=True, exist_ok=True)
                row["new"] = grade(task, protocol, data, True, out)
            rows.append(row)
    print("| Job | Task | Old reward / det | New det | New reward | Checks that changed |\n|---|---|---|---|---|---|")
    for r in rows:
        if "skipped" in r:
            print(f"| {r['job']} | `{r['task']}` | {r['skipped']} | - | - | - |")
            continue
        o = r["old"]
        nd = r["new_det"].get("deterministic_reward")
        nr = (r.get("new") or {}).get("rewards", {}).get("reward", o.get("reward") if not r["changed"] else None)
        diff = sorted(set(r["old_failed"]) ^ set(r["new_failed"]))
        print(f"| {r['job']} | `{r['task']}` | {o.get('reward', 0):.2f} / {o.get('deterministic_reward', 0):.2f} | "
              f"{nd if nd is None else f'{nd:.2f}'} | {'-' if nr is None else f'{nr:.2f}'} | "
              + (", ".join(("+" if d in r["new_failed"] else "-") + d for d in diff) or "none") + " |")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "regrade.json").write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
