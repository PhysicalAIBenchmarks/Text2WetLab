#!/usr/bin/env python3
"""Deterministic grader for an IR task: lint, simulate /app/protocol.py, then check the end state against the IR.

Reward: 1.0 if every check passes; otherwise up to 0.5 for the fraction of end-state checks right (halved if a safety rule
was broken); 0 if the file fails the lint, the simulator fails, or nothing was written. There is no LLM judge, so a judge outage cannot zero a correct protocol.
Paths can be overridden for local runs: TESTS_DIR, PROTOCOL_PATH, VERIFIER_OUT, OT_PYTHON, RUNLOG.
"""
import json
import os
import sys
from pathlib import Path

TESTS = Path(os.environ.get("TESTS_DIR", "/tests"))
os.environ.setdefault("OT_PYTHON", "/opt/ot/bin/python")
os.environ.setdefault("RUNLOG", str(TESTS / "runlog.py"))
sys.path.insert(0, str(TESTS))
from paper2protocol.models import Protocol  # noqa: E402
from protocol_lint import violations  # noqa: E402
from spec_check import check, simulate  # noqa: E402

PROTOCOL = Path(os.environ.get("PROTOCOL_PATH", "/app/protocol.py"))
OUT = Path(os.environ.get("VERIFIER_OUT", "/logs/verifier"))


def grade(protocol: Path = PROTOCOL) -> tuple[dict, dict]:
    rewards = {"reward": 0.0, "sim_pass": 0.0, "checks_frac": 0.0, "lint_violations": 0.0}
    record: dict = {}
    if not protocol.exists():
        record["error"] = "missing protocol"
        return rewards, record
    bad = violations(protocol.read_text())
    record["lint"] = bad
    if bad:
        rewards["lint_violations"] = float(len(bad))
        record["error"] = "protocol uses something a protocol does not need and is not graded"
        return rewards, record
    sim = simulate(str(protocol), os.environ.get("LABWARE_DIR"))
    record["simulation"] = {k: v for k, v in sim.items() if k not in ("events", "labware")}
    if not sim.get("ok"):
        record["error"] = "simulator gate failed"
        return rewards, record
    rewards["sim_pass"] = 1.0
    ir = Protocol.model_validate_json((TESTS / "ir.json").read_text())
    deck = json.loads((TESTS / "deck.json").read_text())
    free = frozenset(json.loads((TESTS / "checks.json").read_text())["free_wells"])
    res = check(ir, sim, free, deck)
    passed = sum(c["pass"] for c in res["checks"])
    rewards["checks_frac"] = round(passed / len(res["checks"]), 4)
    # Partial credit counts only the substantive checks (right labware in the right slot, right end state), so a protocol
    # that does nothing scores 0 instead of passing the safety rules vacuously. Breaking a safety rule halves it.
    substantive = [c for c in res["checks"] if c["name"].startswith(("deck_labware", "end_state"))]
    safety_broken = any(not c["pass"] for c in res["checks"] if c not in substantive)
    frac = sum(c["pass"] for c in substantive) / max(len(substantive), 1)
    rewards["reward"] = 1.0 if res["passed"] else round(0.5 * frac * (0.5 if safety_broken else 1.0), 4)
    record["checks"] = res["checks"]
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
