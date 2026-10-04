#!/usr/bin/env python3
"""Grader: lint, reward-hacking traps, simulate /app/protocol.py, then a rubric LLM judge that reads the simulator run log.

Reward = mean of 5 pass/fail judge items (20% each); 0 if lint, a trap or simulation fails.
Paths can be overridden for local runs: TESTS_DIR, PROTOCOL_PATH, VERIFIER_OUT, OT_PYTHON, LABWARE_DIR.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(os.environ.get("TESTS_DIR", "/tests"))
OT_PYTHON = os.environ.get("OT_PYTHON", "/opt/ot/bin/python")
sys.path.insert(0, str(TESTS))
from protocol_lint import violations  # noqa: E402
from anti_hack import tripped  # noqa: E402
from judge_layer import JUDGE_MODEL, judge  # noqa: E402

PROTOCOL = Path(os.environ.get("PROTOCOL_PATH", "/app/protocol.py"))
OUT = Path(os.environ.get("VERIFIER_OUT", "/logs/verifier"))


def simulate(protocol: Path, labware_dir: str | None = None, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory() as empty:
        out = Path(empty, "result.json")      # a file, not stdout: a protocol can print a forged result and exit early
        r = subprocess.run([OT_PYTHON, str(TESTS / "runlog.py"), str(protocol), labware_dir or empty, str(out)],
                           capture_output=True, text=True, timeout=timeout)
        if out.exists():
            return json.loads(out.read_text())
    return {"ok": False, "error": (r.stderr.strip().splitlines() or ["runlog produced no result"])[-1]}


def grade(protocol: Path = PROTOCOL) -> tuple[dict, dict]:
    rewards = {"reward": 0.0, "sim_pass": 0.0, "lint_violations": 0.0}
    record: dict = {}
    if not protocol.exists():
        record["error"] = "missing protocol"
        return rewards, record
    OUT.mkdir(parents=True, exist_ok=True)
    code = protocol.read_text()
    (OUT / "protocol.py").write_text(code)     # keep what was graded next to the verdict
    bad = violations(code)
    record["lint"] = bad
    if bad:
        rewards["lint_violations"] = float(len(bad))
        record["error"] = "protocol uses something a protocol does not need and is not graded"
        return rewards, record
    traps = tripped(code)
    record["traps"] = traps
    rewards["hack_detected"] = float(bool(traps))
    if traps:
        record["error"] = "reward-hacking trap tripped"
        return rewards, record
    sim = simulate(protocol, os.environ.get("LABWARE_DIR"))
    record["simulation"] = {k: v for k, v in sim.items() if k not in ("events", "labware")}
    if not sim.get("ok"):
        record["error"] = "simulator gate failed"
        return rewards, record
    rewards["sim_pass"] = 1.0
    (OUT / "events.json").write_text(json.dumps(sim["events"]))
    verdict = judge(TESTS, sim["events"], code, Path("/data/paper.txt"))
    record["judge"] = verdict | {"model": JUDGE_MODEL}
    if "error" in verdict:
        rewards["judge_error"] = 1.0
        return rewards, record
    mean = sum(verdict["scores"].values()) / len(verdict["scores"])
    rewards["judge_mean"] = rewards["reward"] = round(mean, 4)
    for key, score in verdict["scores"].items():
        rewards[f"rubric_{key}"] = score
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
