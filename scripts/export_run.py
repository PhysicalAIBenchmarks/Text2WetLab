"""Copy Harbor jobs into results/runs/<run>/ so a benchmark run can be committed, read and re-analysed.

    python scripts/export_run.py results/runs/2026-10-07-openrouter JOB_DIR [JOB_DIR ...] [--regraded DIR] [--via openrouter]

Per trial this writes <model>/<task>/ with trial.json (rewards, exception, cost, tokens, times), protocol.py (what was
graded), reward.json and grader.json (lint, traps, simulator summary, every check, the judge's verdicts). With
--regraded (the --out folder of scripts/regrade_jobs.py) a regraded trial's reward and grader record replace the
originals, and the original rewards are kept in trial.json as original_rewards. Transcripts and logs are not copied.

Claude Code prices every model as a Claude model, so its cost_usd is wrong for any other model. With --prices (a saved
copy of https://openrouter.ai/api/v1/models) cost_usd is recomputed from the token counts at that model's OpenRouter
prices, and Claude Code's figure is kept as claude_code_cost_usd. The run's prices are saved next to it as prices.json.
"""
import argparse
import json
import pathlib
import shutil


def record(verifier: pathlib.Path) -> dict:
    return next((json.loads((verifier / n).read_text()) for n in ("result.json", "judge.json") if (verifier / n).exists()), {})


def openrouter_cost(agent: dict, pricing: dict) -> float:
    """Uncached input at the prompt price, cached input at the cache-read price, output at the completion price."""
    cached = agent.get("n_cache_tokens") or 0
    uncached = (agent.get("n_input_tokens") or 0) - cached
    return round(uncached * float(pricing["prompt"]) + cached * float(pricing.get("input_cache_read") or pricing["prompt"])
                 + (agent.get("n_output_tokens") or 0) * float(pricing["completion"]), 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", type=pathlib.Path)
    ap.add_argument("jobs", nargs="+", type=pathlib.Path)
    ap.add_argument("--regraded", type=pathlib.Path)
    ap.add_argument("--via", default="openrouter")
    ap.add_argument("--prices", type=pathlib.Path, help="saved OpenRouter /api/v1/models response")
    a = ap.parse_args()
    prices = {m["id"]: m["pricing"] for m in json.loads(a.prices.read_text())["data"]} if a.prices else {}
    used = {}
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
                     "finished_at": t.get("finished_at"), "cache_tokens": agent.get("n_cache_tokens")}
            if not model_name.startswith("anthropic/") and model_name in prices and agent:
                trial["claude_code_cost_usd"] = trial["cost_usd"]
                trial["cost_usd"] = openrouter_cost(agent, prices[model_name])
                used[model_name] = prices[model_name]
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
    if used:
        saved = a.dest / "prices.json"
        old = json.loads(saved.read_text()) if saved.exists() else {}
        saved.write_text(json.dumps({**old, **used}, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
