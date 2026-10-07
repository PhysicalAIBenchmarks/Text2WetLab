"""Copy Harbor jobs into results/runs/<run>/ so a benchmark run can be committed, read and re-analysed.

    python scripts/export_run.py results/runs/2026-10-07-openrouter JOB_DIR [JOB_DIR ...] [--regraded DIR] [--via openrouter]

Per trial this writes <model>/<task>/ with trial.json (rewards, exception, cost, tokens, times), protocol.py (what was
graded), reward.json and grader.json (lint, traps, simulator summary, every check, the judge's verdicts). With
--regraded (the --out folder of scripts/regrade_jobs.py) a regraded trial's reward and grader record replace the
originals, and the original rewards are kept in trial.json as original_rewards. Transcripts and logs are not copied.
"""
import argparse
import json
import pathlib
import shutil


def record(verifier: pathlib.Path) -> dict:
    return next((json.loads((verifier / n).read_text()) for n in ("result.json", "judge.json") if (verifier / n).exists()), {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", type=pathlib.Path)
    ap.add_argument("jobs", nargs="+", type=pathlib.Path)
    ap.add_argument("--regraded", type=pathlib.Path)
    ap.add_argument("--via", default="openrouter")
    a = ap.parse_args()
    for job in a.jobs:
        for f in sorted(job.glob("*/result.json")):
            t = json.loads(f.read_text())
            task = t["task_name"].split("/")[-1]
            model_name = t["config"]["agent"]["model_name"]
            out = a.dest / model_name.split("/")[-1] / task
            if out.exists():
                shutil.rmtree(out)
            out.mkdir(parents=True)
            agent = t.get("agent_result") or {}
            rewards = (t.get("verifier_result") or {}).get("rewards")
            trial = {"task": task, "model": model_name, "agent": t["config"]["agent"]["name"], "via": a.via,
                     "rewards": rewards, "exception": (t.get("exception_info") or {}).get("exception_type"),
                     "cost_usd": agent.get("cost_usd"), "input_tokens": agent.get("n_input_tokens"),
                     "output_tokens": agent.get("n_output_tokens"), "started_at": t.get("started_at"),
                     "finished_at": t.get("finished_at")}
            verifier = f.parent / "verifier"
            grader = record(verifier)
            regraded = a.regraded / job.name / task if a.regraded else None
            if regraded and (regraded / "reward.json").exists():
                trial["original_rewards"] = rewards
                trial["rewards"] = json.loads((regraded / "reward.json").read_text())
                grader = record(regraded)
            (out / "trial.json").write_text(json.dumps(trial, indent=1) + "\n")
            if trial["rewards"] is not None:
                (out / "reward.json").write_text(json.dumps(trial["rewards"]) + "\n")
            if grader:
                (out / "grader.json").write_text(json.dumps(grader, indent=1) + "\n")
            if (verifier / "protocol.py").exists():
                shutil.copy(verifier / "protocol.py", out / "protocol.py")
            print(f"{model_name:32} {task:40} {trial['rewards'] and trial['rewards'].get('reward')}"
                  + (f"  (was {rewards.get('reward')})" if "original_rewards" in trial and rewards else ""))


if __name__ == "__main__":
    main()
