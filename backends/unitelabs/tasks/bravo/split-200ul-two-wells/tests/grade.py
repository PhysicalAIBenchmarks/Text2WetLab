#!/usr/bin/env python3
"""Grader for a UniteLabs device task: lint, traps, run /app/protocol.py on the simulated device, check the end state
against the IR, then upstream's rubric LLM judge. The device counterpart of upstream's tasks/<task>/tests/grade.py,
with the same reward scheme: the weighted judge rubric score, capped at 0.3 if a critical check fails; 0 if lint, a
trap or the simulator fails. deterministic_reward is always recorded and becomes the reward when SKIP_JUDGE=1 or the
judge fails.

Feasibility: tests/task.json says whether the protocol can be run on this device at all, and why not. The agent may
answer with /app/INFEASIBLE.md instead of a protocol. A refusal of an infeasible task scores 1.0 only if it names the
limitation (one of task.json "accept", matched case-insensitively); an empty or wrong-reason refusal, a refusal of a
feasible task, and a protocol for an infeasible one score 0 (the protocol is still graded and recorded).

Time: the protocol run gets RUN_TIMEOUT s and every judge call JUDGE_TIMEOUT s with one retry, so the worst case
(two integrity checks, the run, 3 votes x 3 attempts) stays inside the task's verifier timeout (make_tasks.py).

Paths can be overridden for local runs: TESTS_DIR, PROTOCOL_PATH, VERIFIER_OUT, UL_PYTHON, DATA_DIR.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

TESTS = pathlib.Path(os.environ.get("TESTS_DIR", "/tests"))
sys.path.insert(0, str(TESTS))
import judge_layer  # noqa: E402
import gate  # noqa: E402
from check import check_run  # noqa: E402
from judge_text import prompt_for  # noqa: E402

TASK = json.loads((TESTS / "task.json").read_text())      # {"device", "device_name", "feasible", "reason"}
PROTOCOL = pathlib.Path(os.environ.get("PROTOCOL_PATH", "/app/protocol.py"))
INFEASIBLE = PROTOCOL.parent / "INFEASIBLE.md"
OUT = pathlib.Path(os.environ.get("VERIFIER_OUT", "/logs/verifier"))
UL_PYTHON = os.environ.get("UL_PYTHON", "/opt/ul/bin/python")
RUN_TIMEOUT = 300
JUDGE_TIMEOUT = 60
judge_layer.PROMPT = prompt_for(judge_layer.PROMPT, TASK["device_name"])
_judge_client = judge_layer.judge_client


def judge_client():
    """Upstream's client choice, with a per-call timeout so a slow judge cannot outlast the verifier."""
    client, model, provider = _judge_client()
    return client.with_options(timeout=JUDGE_TIMEOUT, max_retries=1), model, provider


judge_layer.judge_client = judge_client


def judge_config() -> dict:
    """What a score depends on besides the protocol; the leaderboard only averages trials that agree on it."""
    if os.environ.get("SKIP_JUDGE") == "1":
        return {"skipped": True}
    provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openrouter" if os.environ.get("OPENROUTER_API_KEY") else None
    return {"skipped": False, "model": judge_layer.JUDGE_MODEL, "provider": provider, "votes": judge_layer.JUDGE_VOTES}


def run_device(protocol: pathlib.Path, timeout: int = RUN_TIMEOUT) -> dict:
    """Run the protocol with the tests/ copy of the runner, from a temp dir so the protocol's cwd holds nothing, and
    without the API keys in its environment."""
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp, "result.json")
        try:
            proc = subprocess.run([UL_PYTHON, "-I", str(TESTS / "runner.py"), TASK["device"], str(protocol), str(out)],
                                  capture_output=True, text=True, timeout=timeout, cwd=tmp, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"TimeoutError: the protocol ran longer than {timeout} s"}
        if not out.exists():
            return {"ok": False, "error": "the run produced no result", "stderr": proc.stderr[-3000:]}
        return json.loads(out.read_text())


def grade_protocol(protocol: pathlib.Path, rewards: dict, record: dict) -> None:
    """Upstream's layers on one protocol file; fills rewards and record in place."""
    (OUT / "protocol.py").write_text(protocol.read_text())
    code = protocol.read_text()
    bad = gate.violations(code)
    record["lint"] = bad
    if bad:
        rewards["lint_violations"] = float(len(bad))
        record["error"] = "protocol uses something a protocol does not need and is not graded"
        return
    traps = gate.tripped(code)
    record["traps"] = traps
    rewards["hack_detected"] = float(bool(traps))
    if traps:
        record["error"] = "reward-hacking trap tripped"
        return
    sim = run_device(protocol)
    record["simulation"] = {k: v for k, v in sim.items() if k not in ("events", "labware", "geometry")}
    (OUT / "events.json").write_text(json.dumps({k: sim.get(k) for k in ("events", "labware", "geometry", "comments")}))
    if not sim.get("ok"):
        record["error"] = "simulator gate failed"
        return
    rewards["sim_pass"] = 1.0
    record["efficiency"] = sim.get("efficiency")      # reported next to the reward, never part of it
    res = check_run(TESTS, sim)
    record["not_applicable"] = res["not_applicable"]
    passed = sum(c["pass"] for c in res["checks"])
    rewards["checks_frac"] = round(passed / len(res["checks"]), 4)
    # Partial credit counts only the substantive checks (right labware, right end state), so a protocol that does
    # nothing scores 0 instead of passing the safety rules vacuously. Breaking a safety rule halves it.
    substantive = [c for c in res["checks"] if c["name"].startswith(("deck_labware", "end_state"))]
    safety_broken = any(not c["pass"] for c in res["checks"] if c not in substantive)
    frac = sum(c["pass"] for c in substantive) / max(len(substantive), 1)
    rewards["reward"] = 1.0 if res["passed"] else round(0.5 * frac * (0.5 if safety_broken else 1.0), 4)
    record["checks"] = res["checks"]
    rewards["deterministic_reward"] = rewards["reward"]
    if os.environ.get("SKIP_JUDGE") == "1":
        record["judge"] = {"skipped": "SKIP_JUDGE=1"}
        return
    paper = pathlib.Path(os.environ.get("DATA_DIR", "/data")) / "paper.txt"
    verdict = judge_layer.judge(TESTS, res["checks"], code, paper)
    record["judge"] = {"model": judge_layer.JUDGE_MODEL} | verdict
    if "error" in verdict:
        rewards["judge_error"] = 1.0             # not zeroed here; the leaderboard leaves these out until re-judged
        return
    score = verdict["score"]
    level = judge_layer.load_rubric(TESTS)["level"]
    critical = sorted(c["name"] for c in res["checks"] if not c["pass"] and judge_layer.is_critical(c["name"], level))
    record["critical_failures"] = critical
    rewards["judge_score"] = score
    rewards["critical_fail"] = float(bool(critical))
    rewards["reward"] = round(min(score, judge_layer.CRITICAL_CAP) if critical else score, 4)
    for key, item_score in verdict["scores"].items():
        rewards[f"rubric_{key}"] = item_score


def names_limitation(text: str) -> bool:
    """Whether INFEASIBLE.md names the hardware limitation that makes the task infeasible here (task.json "accept")."""
    return any(re.search(pattern, text, re.I) for pattern in TASK.get("accept", []))


def grade(protocol: pathlib.Path = PROTOCOL) -> tuple[dict, dict]:
    rewards = {"reward": 0.0, "sim_pass": 0.0, "checks_frac": 0.0, "lint_violations": 0.0}
    record: dict = {"backend": f"unitelabs-{TASK['device']}", "feasible": TASK["feasible"], "judge_config": judge_config()}
    image = pathlib.Path("/opt/ul_t2wl/image.json")
    if image.exists():
        record["image"] = json.loads(image.read_text())     # which SDK and docs commits the agent wrote against
    OUT.mkdir(parents=True, exist_ok=True)
    declared = INFEASIBLE.exists()
    record["declared_infeasible"] = declared
    if declared:
        record["infeasible_md"] = INFEASIBLE.read_text()[:4000]
        (OUT / "INFEASIBLE.md").write_text(INFEASIBLE.read_text())
    if not protocol.exists():
        if declared and not TASK["feasible"] and names_limitation(INFEASIBLE.read_text()):
            rewards["reward"] = rewards["deterministic_reward"] = 1.0
            record["verdict"] = "correctly declared infeasible"
        elif declared and not TASK["feasible"]:
            record["error"] = "declared infeasible without naming the limitation: " + TASK.get("reason", "")
        elif declared:
            record["error"] = "declared infeasible, but the protocol can be run on this device"
        else:
            record["error"] = "missing protocol"
        return rewards, record
    grade_protocol(protocol, rewards, record)
    if not TASK["feasible"]:
        # The protocol was graded for the record; the task cannot be run on this device, so the reward is 0.
        record["verdict"] = "wrote a protocol for a task this device cannot run: " + TASK.get("reason", "")
        record["graded_reward"] = rewards["reward"]
        rewards["reward"] = 0.0
        rewards["deterministic_reward"] = 0.0
    elif declared:
        record["verdict"] = "declared infeasible but also wrote a protocol; graded as a protocol"
    return rewards, record


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rewards, record = grade()
    record["rewards"] = rewards
    (OUT / "result.json").write_text(json.dumps(record, indent=2))
    (OUT / "reward.json").write_text(json.dumps(rewards))
    print(json.dumps(record, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
