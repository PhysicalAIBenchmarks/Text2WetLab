"""Turn Harbor job output into the leaderboard: per model and device, the mean reward over feasible tasks with its
spread, the share of infeasible tasks recognized, cost, and how trials failed (gate, checks, judge, refusal).

    uv run ul/leaderboard.py jobs/<job> [jobs/<job> ...] [--reference jobs/<oracle job> ...] [--out FILE]

Reads every trial's result.json (Harbor) and verifier/result.json (our grader). A trial counts as refused when the
agent produced no protocol and its final message declines the task; refusals are reported, not scored, like upstream.
Trials whose judge failed are left out of the means and listed for re-judging; a trial without a verifier result
(the verifier timed out or crashed) scores 0. A row is one model, device and judge configuration (judge model,
provider, votes, or skipped): trials graded differently are never averaged together.
Infeasible tasks are a separate column, so declaring everything infeasible cannot lift the protocol mean.
Next to the judged mean, the deterministic mean (checks only, no LLM judge) and, with --reference (the oracle's jobs),
efficiency: the trial's estimated run time over the reference's for the same device and task, averaged over trials
that passed every check. Neither is part of the reward.
Prints a markdown table and writes the JSON the website table is built from.
"""
import argparse
import json
import pathlib
import statistics
import sys

REFUSAL_WORDS = ("can't help", "cannot help", "unable to help", "not able to help", "I can't assist", "I cannot assist")


def trials(job: pathlib.Path):
    for trial in sorted(p for p in job.iterdir() if p.is_dir()):
        meta = trial / "result.json"
        if not meta.exists():
            continue
        harbor = json.loads(meta.read_text())
        verifier = trial / "verifier" / "result.json"
        record = json.loads(verifier.read_text()) if verifier.exists() else {}
        yield trial, harbor, record


def classify(harbor: dict, record: dict) -> str:
    if not record:
        return "verifier_missing"
    verdict = record.get("verdict", "")
    if verdict.startswith("correctly declared infeasible"):
        return "infeasible_recognized"
    if verdict.startswith("wrote a protocol for a task this device cannot run"):
        return "infeasible_missed"
    if record.get("error", "").startswith("declared infeasible, but"):
        return "wrongly_declared_infeasible"
    if record.get("error", "").startswith("declared infeasible without naming"):
        return "infeasible_wrong_reason"
    if record.get("error") == "missing protocol":
        text = json.dumps(harbor).lower()
        return "refused" if any(w.lower() in text for w in REFUSAL_WORDS) else "no_protocol"
    if record.get("error"):
        return {"protocol uses something a protocol does not need and is not graded": "lint",
                "reward-hacking trap tripped": "trap", "simulator gate failed": "simulator"}.get(record["error"], "error")
    if record.get("rewards", {}).get("judge_error"):
        return "judge_error"
    if record.get("critical_failures"):
        return "critical_check"
    if (record.get("judge_config") or {}).get("skipped") or (record.get("judge") or {}).get("skipped"):
        return "judge_skipped"
    return "graded"


def judge_label(record: dict) -> str:
    """The judge configuration a trial was scored under, as part of its row key."""
    cfg = record.get("judge_config")
    if cfg is None:                                   # recorded before judge_config existed
        judge = record.get("judge") or {}
        if judge.get("skipped"):
            return "no judge"
        if not judge.get("provider"):
            return "judge not recorded"
        cfg = {"model": judge.get("model"), "provider": judge.get("provider"), "votes": judge.get("votes")}
    if cfg.get("skipped"):
        return "no judge"
    return f"judge {cfg.get('model')}/{cfg.get('provider')}/x{cfg.get('votes')}"


def cost_of(harbor: dict) -> float | None:
    cost = (harbor.get("agent_result") or {}).get("cost_usd")
    return float(cost) if isinstance(cost, (int, float)) else None


def model_of(harbor: dict) -> str:
    """Harbor's agent_info: {"name": "claude-code", "model_info": {"name": ..., "provider": ...}} (oracle: no model)."""
    info = harbor.get("agent_info") or {}
    model = info.get("model_info")
    if isinstance(model, dict):
        return str(model.get("name") or model.get("model_name") or model)
    return str(model or info.get("name") or "?")


def reference_seconds(jobs: list[pathlib.Path]) -> dict[tuple[str, str], float]:
    """(device, task) -> the reference protocol's estimated run time, from oracle jobs."""
    out = {}
    for job in jobs:
        for trial, harbor, record in trials(job):
            name = (harbor.get("task_name") or trial.name).split("/")[-1]
            device, _, task = name.partition(".")
            seconds = (record.get("efficiency") or {}).get("est_seconds")
            if seconds:
                out[(device, task)] = float(seconds)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--reference", nargs="*", type=pathlib.Path, default=[],
                    help="oracle job(s): their estimated run times are the efficiency baseline")
    a = ap.parse_args()
    baseline = reference_seconds(a.reference)
    entries = []
    for job in a.jobs:
        for trial, harbor, record in trials(job):
            model = model_of(harbor)
            name = (harbor.get("task_name") or trial.name).split("/")[-1]   # text2wetlab-ul/<device>.<task>
            device, _, task = name.partition(".") if "." in name else (record.get("backend", "?").removeprefix("unitelabs-"), "", name)
            outcome = classify(harbor, record)
            entries.append((f"{model} @ {device}", judge_label(record) if record else None, task, {
                "trial": str(trial), "reward": 0.0 if outcome == "verifier_missing" else record.get("rewards", {}).get("reward"),
                "feasible": record.get("feasible", True), "deterministic": record.get("rewards", {}).get("deterministic_reward"),
                "outcome": outcome, "cost_usd": cost_of(harbor), "image": record.get("image"),
                "est_seconds": (record.get("efficiency") or {}).get("est_seconds"),
                "passed": record.get("rewards", {}).get("checks_frac") == 1.0,
            }))
    # A trial without a verifier result has no judge configuration; it joins its model's row when that is unambiguous.
    labels: dict[str, set] = {}
    for row, label, _, _ in entries:
        if label is not None:
            labels.setdefault(row, set()).add(label)
    rows: dict[tuple[str, str], list[dict]] = {}
    for row, label, task, t in entries:
        device = row.rsplit(" @ ", 1)[1]
        base = baseline.get((device, task))
        t["time_vs_reference"] = round(t["est_seconds"] / base, 3) if base and t["est_seconds"] and t["passed"] else None
        if label is None:
            known = labels.get(row, set())
            label = next(iter(known)) if len(known) == 1 else "?"
        rows.setdefault((f"{row} ({label})", task), []).append(t)
    models: dict[str, dict] = {}
    rejudge = []
    for (model, task), ts in sorted(rows.items()):
        rejudge += [t["trial"] for t in ts if t["outcome"] == "judge_error"]
        scored = [t["reward"] for t in ts if t["outcome"] not in ("refused", "judge_error") and t["reward"] is not None]
        m = models.setdefault(model, {"tasks": {}, "outcomes": {}, "cost_usd": 0.0, "trials": 0})
        det = [t["deterministic"] for t in ts if t["outcome"] not in ("refused",) and t["deterministic"] is not None]
        ratios = [t["time_vs_reference"] for t in ts if t["time_vs_reference"] is not None]
        m["tasks"][task] = {"mean": round(statistics.fmean(scored), 3) if scored else None,
                            "deterministic": round(statistics.fmean(det), 3) if det else None,
                            "time_vs_reference": round(statistics.fmean(ratios), 3) if ratios else None,
                            "spread": round(max(scored) - min(scored), 3) if len(scored) > 1 else 0.0,
                            "n": len(scored), "rewards": scored, "feasible": all(t["feasible"] for t in ts)}
        for t in ts:
            m["outcomes"][t["outcome"]] = m["outcomes"].get(t["outcome"], 0) + 1
            m["cost_usd"] += t["cost_usd"] or 0.0
            m["trials"] += 1
    for model, m in models.items():
        feasible = [t["mean"] for t in m["tasks"].values() if t["mean"] is not None and t["feasible"]]
        infeasible = [t["mean"] for t in m["tasks"].values() if t["mean"] is not None and not t["feasible"]]
        m["mean"] = round(statistics.fmean(feasible), 3) if feasible else None
        m["infeasible_recognized"] = round(statistics.fmean(infeasible), 3) if infeasible else None
        det = [t["deterministic"] for t in m["tasks"].values() if t["deterministic"] is not None and t["feasible"]]
        m["deterministic"] = round(statistics.fmean(det), 3) if det else None
        ratios = [t["time_vs_reference"] for t in m["tasks"].values() if t["time_vs_reference"] is not None]
        m["time_vs_reference"] = round(statistics.fmean(ratios), 3) if ratios else None
        m["cost_usd"] = round(m["cost_usd"], 2)
    tasks = sorted({t for m in models.values() for t in m["tasks"]})
    print("| model @ device (judge) | mean (feasible) | deterministic | infeasible recognized | time vs reference | "
          + " | ".join(tasks) + " | trials | outcomes | cost $ |")
    print("|---|---|---|---|---|" + "---|" * len(tasks) + "---|---|---|")
    for model, m in sorted(models.items(), key=lambda kv: -(kv[1]["mean"] or 0)):
        cells = [f"{m['tasks'][t]['mean']:.3f} ±{m['tasks'][t]['spread']:.2f}" if t in m["tasks"] and m["tasks"][t]["mean"] is not None else "–" for t in tasks]
        dash = lambda v: "–" if v is None else v  # noqa: E731
        print(f"| {model} | {m['mean']} | {dash(m['deterministic'])} | {dash(m['infeasible_recognized'])} | "
              f"{dash(m['time_vs_reference'])} | "
              + " | ".join(cells) + f" | {m['trials']} | {m['outcomes']} | {m['cost_usd']} |")
    if rejudge:
        print(f"\n{len(rejudge)} trial(s) left out because the judge failed; re-judge them:\n" + "\n".join(rejudge))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"models": models, "rejudge": rejudge, "jobs": [str(j) for j in a.jobs]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
