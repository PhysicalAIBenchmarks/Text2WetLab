"""Collect every Harbor eval round from git history into rounds.json (one row per trial, with judge evidence)."""
import json, subprocess, sys
REPO = sys.argv[1]
ROUNDS = [  # (commit, label) in time order, 2026-10-04
    ("39c9b19", "R0 06:05 fixed grader (Sonnet only)"),
    ("6c70dc3", "R1 08:21 first 3-model run (judge on RNA only)"),
    ("7a2fd8a", "R2 09:56 + Sonnet rubric judge"),
    ("f39bdee", "R3 10:07 binary 5-item rubric"),
    ("071a421", "R4 10:47 + 10 reward-hack traps"),
    ("8beadb3", "R5 11:20 run-log judge (6 tasks)"),
    ("9984c6a", "R6 11:29 run-log judge (RNA too)"),
    ("48836f1", "R7 11:35 clean re-run, 21 trials"),
    ("6a0478a", "R8 12:36 lLegon: easy/hard, 75/25"),
]
def show(c, p):
    r = subprocess.run(["git", "-C", REPO, "show", f"{c}:{p}"], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
out = []
for c, label in ROUNDS:
    summ = show(c, "results/summary.json") or []
    if isinstance(summ, dict):
        summ = summ.get("trials") or summ.get("results") or list(summ.values())
    for t in summ:
        if not isinstance(t, dict) or "task" not in t:
            continue
        model = t.get("model") or t.get("agent_model") or "claude-sonnet-5-5"
        res = show(c, f"results/{model}/{t['task']}/result.json") or show(c, f"results/{model}/{t['task']}/judge.json") or {}
        judge = res.get("judge") or {}
        items = {i["id"]: i for i in judge.get("items", [])}
        rw = show(c, f"results/{model}/{t['task']}/reward.json") or {}
        rubric = t.get("rubric") or {k[7:]: v for k, v in t.items() if k.startswith("rubric_")} \
            or {k[7:]: v for k, v in rw.items() if k.startswith("rubric_")}
        fails = [{"item": k, "evidence": (items.get(k, {}).get("evidence") or "")[:400]} for k, v in rubric.items() if v is not None and v < 1]
        failed_checks = [ch["name"] for ch in (res.get("checks") or []) if isinstance(ch, dict) and not ch.get("pass", True)]
        if isinstance(res.get("checks"), dict):
            failed_checks = [ch["name"] for ch in res["checks"].get("checks", []) if not ch.get("pass", True)]
        out.append(dict(commit=c, round=label, model=model, task=t["task"], reward=t.get("reward"),
                        sim_pass=t.get("sim_pass"), checks_frac=t.get("checks_frac"), judge_mean=t.get("judge_mean"),
                        hack=t.get("hack_detected"), critical=t.get("critical_fail"), traps=t.get("traps"),
                        cost=t.get("cost_usd"), tok_in=t.get("input_tokens"), tok_out=t.get("output_tokens"),
                        dur=t.get("duration_s"), exception=t.get("exception"), rubric=rubric,
                        failed_items=fails, failed_checks=failed_checks, judge_summary=(judge.get("summary") or "")[:500]))
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(len(out), "trials")
