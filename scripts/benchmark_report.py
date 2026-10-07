"""Fine-grained report for Harbor runs: per task, per risk check, per rubric item, with the ground-truth evidence.

    python scripts/benchmark_report.py JOB_DIR [JOB_DIR ...] [--json out.json]

Each JOB_DIR is a `harbor run -o ... --job-name ...` folder, or a results/runs/<run>/<model>/ folder from
scripts/export_run.py. A "risk" is one deterministic check the grader runs against
the ground truth: the IR's end state (end_state:<container>), the fixed deck (deck_labware:<container>), and the
physical safety rules (tips, overdispense, empty wells, cross-contamination). The RNA task has its own 16 run-log checks.
"""
import argparse
import collections
import json
import pathlib
import re

RISK_GROUPS = {  # check name prefix -> the risk it guards against
    "simulator_ran": "protocol runs in the simulator",
    "deck_labware": "right labware, label and slot (fixed deck)",
    "end_state": "end-state volumes match the IR ground truth",
    "tip_before_aspirate": "never pipettes without a tip",
    "no_overdispense": "never dispenses more than it holds",
    "no_aspirate_from_empty_well": "never aspirates from an empty well",
    "tip_dropped_at_end": "does not finish holding a tip",
    "no_cross_contamination": "no cross-contamination between wells",
}


def task_of(trial: dict, folder: pathlib.Path) -> str:
    return trial.get("task_name", folder.name).split("/")[-1]


def load_exported(folder: pathlib.Path):
    """A results/runs/<run>/<model>/ folder written by scripts/export_run.py."""
    for f in sorted(folder.glob("*/trial.json")):
        trial = json.loads(f.read_text())
        rec = json.loads((f.parent / "grader.json").read_text()) if (f.parent / "grader.json").exists() else {}
        checks = rec.get("checks")
        if isinstance(checks, dict):
            checks = checks.get("checks", [])
        yield {"model": folder.name, "task": trial["task"], "rewards": trial.get("rewards") or {},
               "exception": trial.get("exception"), "checks": checks or [], "traps": rec.get("traps", []),
               "lint": rec.get("lint", []), "judge": rec.get("judge") or {}, "error": rec.get("error"),
               "cost": trial.get("cost_usd"), "tokens": (trial.get("input_tokens"), trial.get("output_tokens"))}


def load_trials(job: pathlib.Path):
    if any(job.glob("*/trial.json")):
        yield from load_exported(job)
        return
    model = job.name.removeprefix("bench-").removeprefix("oracle-")
    for f in sorted(job.glob("*/result.json")):
        trial = json.loads(f.read_text())
        v = f.parent / "verifier"
        rec = {}
        for name in ("result.json", "judge.json"):
            if (v / name).exists():
                rec = json.loads((v / name).read_text())
                break
        checks = rec.get("checks")
        if isinstance(checks, dict):                       # RNA: {"checks": [...], "checks_passed": n, ...}
            checks = checks.get("checks", [])
        agent = trial.get("agent_result") or {}
        yield {
            "model": model, "task": task_of(trial, f.parent),
            "rewards": (trial.get("verifier_result") or {}).get("rewards") or {},
            "exception": (trial.get("exception_info") or {}).get("exception_type"),
            "checks": checks or [], "traps": rec.get("traps", []), "lint": rec.get("lint", []),
            "judge": rec.get("judge") or {}, "error": rec.get("error"),
            "cost": agent.get("cost_usd"), "tokens": (agent.get("n_input_tokens"), agent.get("n_output_tokens")),
        }


def risk(name: str) -> str:
    return re.split(r"[:\[]", name, maxsplit=1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", nargs="+", type=pathlib.Path)
    ap.add_argument("--json", type=pathlib.Path)
    a = ap.parse_args()
    trials = [t for j in a.jobs for t in load_trials(j)]
    models = list(dict.fromkeys(t["model"] for t in trials))
    tasks = sorted({t["task"] for t in trials})
    by = {(t["model"], t["task"]): t for t in trials}
    out = []

    out.append("## Reward per task (judge-weighted reward / deterministic reward)\n")
    out.append("| Task | " + " | ".join(models) + " |\n|---|" + "---|" * len(models))
    for task in tasks:
        cells = []
        for m in models:
            t = by.get((m, task))
            if not t:
                cells.append("-")
            elif t["exception"] == "AgentSafetyRefusalError":
                cells.append("refused (not scored)")
            elif t["exception"]:
                cells.append(f"error: {t['exception']}")
            else:
                r = t["rewards"]
                cells.append(f"{r.get('reward', 0):.2f} / {r.get('deterministic_reward', 0):.2f}"
                             + (" ⚑trap" if r.get("hack_detected") else "") + (" ⚑critical" if r.get("critical_fail") else ""))
        out.append(f"| `{task}` | " + " | ".join(cells) + " |")
    # Refused tasks are not scored: a refusal is the provider's safety policy, not a protocol.
    refused = {m: [k for k in tasks if (m, k) in by and by[(m, k)]["exception"] == "AgentSafetyRefusalError"] for m in models}
    answered = {m: [k for k in tasks if (m, k) in by and not by[(m, k)]["exception"]] for m in models}
    common = [k for k in tasks if all(k in answered[m] for m in models)]
    mean = lambda m, ks: sum(by[(m, k)]["rewards"].get("reward", 0.0) for k in ks) / max(len(ks), 1)
    cost = {m: sum(by[(m, k)]["cost"] or 0 for k in tasks if (m, k) in by) for m in models}
    out.append(f"| **Mean over the {len(common)} tasks every model answered** | "
               + " | ".join(f"**{mean(m, common):.3f}**" for m in models) + " |")
    out.append("| **Mean over all tasks it answered** | " + " | ".join(f"{mean(m, answered[m]):.3f} (n={len(answered[m])})" for m in models) + " |")
    out.append("| Refused, not scored | " + " | ".join(str(len(refused[m])) for m in models) + " |")
    out.append("| Agent cost | " + " | ".join(f"${cost[m]:.2f}" for m in models) + " |\n")
    for m in models:
        if refused[m]:
            out.append(f"- {m} refused (Anthropic `[bio]` safeguard, `AgentSafetyRefusalError`): {', '.join(refused[m])}")
    out.append("")

    out.append("## Per risk: checks passed / checks run (all tasks)\n")
    out.append("| Risk | What it guards against | " + " | ".join(models) + " |\n|---|---|" + "---|" * len(models))
    groups = list(RISK_GROUPS) + sorted({risk(c["name"]) for t in trials for c in t["checks"]} - set(RISK_GROUPS))
    for g in groups:
        cells = []
        for m in models:
            cs = [c for t in trials if t["model"] == m for c in t["checks"] if risk(c["name"]) == g]
            cells.append(f"{sum(c['pass'] for c in cs)}/{len(cs)}" if cs else "-")
        if any(c != "-" for c in cells):
            out.append(f"| `{g}` | {RISK_GROUPS.get(g, 'RNA run-log check')} | " + " | ".join(cells) + " |")
    traps = {m: collections.Counter(x["trap"] for t in trials if t["model"] == m for x in t["traps"]) for m in models}
    out.append("| `traps` | reward hacking (any trap fired) | " + " | ".join(str(sum(traps[m].values())) or "0" for m in models) + " |")
    out.append("| `lint` | forbidden code (imports, file access, dunders) | "
               + " | ".join(str(sum(bool(t["lint"]) for t in trials if t["model"] == m)) for m in models) + " |\n")

    out.append("## Per rubric item: judge scored 1 / items judged\n")
    items = sorted({k for t in trials for k in t["rewards"] if k.startswith("rubric_")})
    out.append("| Rubric item | " + " | ".join(models) + " |\n|---|" + "---|" * len(models))
    for k in items:
        cells = []
        for m in models:
            vs = [t["rewards"][k] for t in trials if t["model"] == m and k in t["rewards"]]
            cells.append(f"{int(sum(vs))}/{len(vs)}" if vs else "-")
        out.append(f"| `{k.removeprefix('rubric_')}` | " + " | ".join(cells) + " |")
    providers = collections.Counter((t["judge"].get("provider"), t["judge"].get("model")) for t in trials if t["judge"])
    out.append(f"\nJudge: {', '.join(f'{p} {m} (x{n})' for (p, m), n in providers.items())}\n")

    out.append("## Every failure, with the ground-truth evidence\n")
    for t in sorted(trials, key=lambda t: (t["task"], t["model"])):
        fails = [c for c in t["checks"] if not c["pass"]]
        zero = [i for i in t["judge"].get("items", []) if i.get("score") == 0]
        if not (fails or zero or t["traps"] or t["lint"] or t["exception"] or t["error"]):
            continue
        out.append(f"**{t['task']} · {t['model']}** (reward {t['rewards'].get('reward', 0):.2f})")
        for c in fails:
            out.append(f"- check `{c['name']}` failed: {str(c.get('detail', ''))[:300]}")
        for x in t["traps"]:
            out.append(f"- trap `{x['trap']}`: {x['detail'][:200]}")
        for x in t["lint"][:3]:
            out.append(f"- lint: {x}")
        for i in zero:
            votes = f" (votes {i['votes']})" if i.get("votes") else ""
            out.append(f"- judge 0 on `{i['id']}`{votes}: {i.get('evidence', '')[:300]}")
        if t["judge"].get("failed_votes"):
            out.append(f"- judge: {t['judge']['votes']} of {t['judge']['votes'] + t['judge']['failed_votes']} votes returned (network errors)")
        if t["exception"] or (t["error"] and not fails):
            out.append(f"- {t['exception'] or t['error']}")
        out.append("")
    print("\n".join(out))
    if a.json:
        a.json.write_text(json.dumps(trials, indent=1, default=str))


if __name__ == "__main__":
    main()
