"""Gate a `harbor run -a oracle` job: every task ran, and every reference solution passed its own grader.

    harbor run -p tasks -a oracle -n 11 -y -o jobs --job-name oracle
    python scripts/check_oracle_rewards.py jobs/oracle [--min-judge 0.5]

Per task the oracle must: finish without an exception, trip no reward-hacking trap, get deterministic_reward 1.0
(lint, simulator, end-state checks), and get a judge reward of at least --min-judge with no judge error. The judge bar
is a floor, not 1.0: the rubric judge does not give the reference full marks on every task (RNA scores about 0.6-0.7).
Writes a markdown table to $GITHUB_STEP_SUMMARY when set.
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job", type=pathlib.Path)
    ap.add_argument("--min-judge", type=float, default=0.5)
    a = ap.parse_args()
    want = {f"text2wetlab/{p.name}" for p in (ROOT / "tasks").iterdir() if (p / "task.toml").exists()}
    rows, bad, seen = [], [], set()
    for f in sorted(a.job.glob("*/result.json")):
        trial = json.loads(f.read_text())
        name = trial.get("task_name", f.parent.name)
        seen.add(name)
        r = (trial.get("verifier_result") or {}).get("rewards") or {}
        why = []
        if trial.get("exception_info"):
            why.append(f"exception: {str(trial['exception_info'])[:120]}")
        if r.get("hack_detected"):
            why.append("reward-hacking trap fired on the reference")
        if r.get("deterministic_reward") != 1.0:
            why.append(f"deterministic_reward={r.get('deterministic_reward')}")
        if r.get("judge_error"):
            why.append("judge error")
        elif r.get("reward", 0.0) < a.min_judge:
            why.append(f"reward={r.get('reward')} < {a.min_judge}")
        rows.append(f"| `{name}` | {r.get('deterministic_reward')} | {r.get('reward')} | {'; '.join(why) or 'ok'} |")
        bad += [f"{name}: {w}" for w in why]
    bad += [f"{t}: no trial in {a.job}" for t in sorted(want - seen)]
    table = "| Task | Deterministic | Reward (judge) | Status |\n|---|---|---|---|\n" + "\n".join(rows)
    print(table)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as s:
            s.write("## Harbor oracle run\n\n" + table + "\n")
    if bad:
        print("\nFAILED:\n  " + "\n  ".join(bad), file=sys.stderr)
        return 1
    print(f"\nall {len(seen)} oracle trials passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
