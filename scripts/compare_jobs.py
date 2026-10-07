"""Compare Harbor jobs: wall-clock time, where the time goes per trial, cost and reward, task by task.

    python scripts/compare_jobs.py LABEL=JOB_DIR [LABEL=JOB_DIR ...] [--prices OPENROUTER_MODELS_JSON]

Use it to compare backends (local Docker vs Modal) for the same model, or repeated runs of one model (run-to-run
variation at pass@1). Times come from each trial's result.json; a job's wall clock runs from its first trial's start to
its last trial's finish. Rewards are as graded at run time (not any later regrade). With --prices, non-Claude models'
cost comes from their tokens at OpenRouter prices (Claude Code prices every model as Claude; see export_run.py).
"""
import json
import pathlib
import statistics
import sys
from datetime import datetime

from export_run import openrouter_cost


def ts(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def span(d: dict | None) -> float | None:
    if not d or not d.get("started_at") or not d.get("finished_at"):
        return None
    return (ts(d["finished_at"]) - ts(d["started_at"])).total_seconds()


PRICES: dict = {}


def load(job: pathlib.Path) -> dict:
    trials = {}
    for f in sorted(job.glob("*/result.json")):
        t = json.loads(f.read_text())
        r = (t.get("verifier_result") or {}).get("rewards") or {}
        agent, model = t.get("agent_result") or {}, t["config"]["agent"]["model_name"]
        cost = (openrouter_cost(agent, PRICES[model]) if agent and model in PRICES and not model.startswith("anthropic/")
                else agent.get("cost_usd") or 0.0)
        trials[t["task_name"].split("/")[-1]] = {
            "reward": r.get("reward"), "exception": (t.get("exception_info") or {}).get("exception_type"),
            "cost": cost,
            "start": ts(t.get("started_at")), "end": ts(t.get("finished_at")), "total": span(t),
            "env": span(t.get("environment_setup")), "agent": span(t.get("agent_execution")), "verify": span(t.get("verifier"))}
    return trials


def fmt_s(v: float | None) -> str:
    return "-" if v is None else f"{v / 60:.1f} min" if v >= 90 else f"{v:.0f} s"


def main() -> int:
    jobs, args = {}, sys.argv[1:]
    if "--prices" in args:
        i = args.index("--prices")
        PRICES.update({m["id"]: m["pricing"] for m in json.loads(pathlib.Path(args[i + 1]).read_text())["data"]})
        del args[i:i + 2]
    for arg in args:
        label, _, path = arg.partition("=")
        jobs[label] = load(pathlib.Path(path).expanduser())
    print("| Job | Trials | Wall clock | Median trial | Median env setup | Median agent | Median verifier | Agent cost | Mean reward (answered) |")
    print("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for label, tr in jobs.items():
        done = [t for t in tr.values() if t["end"]]
        wall = (max(t["end"] for t in done) - min(t["start"] for t in done)).total_seconds() if done else None
        med = lambda k: statistics.median([t[k] for t in tr.values() if t[k] is not None]) if any(t[k] is not None for t in tr.values()) else None
        answered = [t["reward"] for t in tr.values() if t["reward"] is not None and not t["exception"]]
        score = f"{statistics.mean(answered):.3f} (n={len(answered)})" if answered else "-"
        print(f"| {label} | {len(tr)} | {fmt_s(wall)} | {fmt_s(med('total'))} | {fmt_s(med('env'))} | {fmt_s(med('agent'))} | "
              f"{fmt_s(med('verify'))} | ${sum(t['cost'] for t in tr.values()):.2f} | {score} |")
    tasks = sorted({k for tr in jobs.values() for k in tr}, key=lambda k: (k.endswith("-hard"), k))
    labels = list(jobs)
    print("\n| Task | " + " | ".join(labels) + " |\n|---|" + ":---:|" * len(labels))
    for k in tasks:
        cells = []
        for label in labels:
            t = jobs[label].get(k)
            cells.append("-" if not t else t["exception"] or ("-" if t["reward"] is None else f"{t['reward']:.2f}"))
        print(f"| `{k}` | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
