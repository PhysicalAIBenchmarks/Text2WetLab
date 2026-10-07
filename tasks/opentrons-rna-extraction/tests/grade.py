#!/usr/bin/env python3
"""Grade /app/protocol.py: simulator gate, run-log checks, then a rubric LLM judge.

Reward = weighted rubric score from tests/rubric.json (robot practice, tips/contamination and fidelity 25% each; the
task-specific items share the other 25%), capped at 0.3 if a critical run-log check fails.

deterministic_reward is always recorded once the simulator passes: 1.0 if no critical run-log check fails, otherwise
0.5 x the fraction of checks passed. It becomes the reward when SKIP_JUDGE=1 (oracle checks in CI) and when the judge call
fails (judge_error=1 still flags it). Paths can be overridden for local runs: TESTS_DIR, DATA_DIR, PROTOCOL_PATH,
VERIFIER_OUT, OT_PYTHON.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

TESTS = Path(os.environ.get("TESTS_DIR", "/tests"))
DATA = Path(os.environ.get("DATA_DIR", "/data"))
sys.path.insert(0, str(TESTS))
from checks import analyze  # noqa: E402
from anti_hack import tripped  # noqa: E402

PROTOCOL = Path(os.environ.get("PROTOCOL_PATH", "/app/protocol.py"))
LABWARE = str(DATA / "labware")
PAPER = DATA / "paper.txt"
REFERENCE = TESTS / "reference_protocol.py"
VARIANT = TESTS / "variant.json"
OT_PYTHON = os.environ.get("OT_PYTHON", "/opt/ot/bin/python")
OUT = Path(os.environ.get("VERIFIER_OUT", "/logs/verifier"))
JUDGE_MODEL = os.environ.get("JUDGE_MODEL") or "claude-sonnet-5-5"
OPENROUTER_URL = "https://openrouter.ai/api"      # OpenRouter's Anthropic-compatible Messages API
OPENROUTER_MODELS = {"claude-sonnet-5-5": "anthropic/claude-sonnet-5.5", "claude-opus-5-5": "anthropic/claude-opus-5.5",
                     "claude-fable-5-1": "anthropic/claude-fable-5.1"}
CRITICAL_CAP = 0.3
CRITICAL_CHECKS = {
    "48_samples_to_odd_columns", "step_order", "supernatant_removed_each_step",
    "two_500ul_ethanol_washes", "recover_70_100ul_one_well_each",
    "fresh_tip_per_sample_no_cross_contact",
}
SAFE_ENV_KEYS = ["PATH", "HOME", "LANG", "LC_ALL"]
SUSPICIOUS = re.compile(r"broker|_implementation|_core\b|\.commands\.|publish\(|monkey|__dict__|setattr\(")

RUBRIC_FILE = TESTS / "rubric.json"
CORE_WEIGHT = 0.75  # robot practice, tips/contamination and fidelity share 75%; the task items share the other 25%


def load_rubric() -> dict:
    rubric = json.loads(RUBRIC_FILE.read_text())
    core, task = rubric["core"], rubric["task"]
    items = [dict(r, group="core", weight=CORE_WEIGHT / len(core)) for r in core]
    items += [dict(r, group="task", weight=(1 - CORE_WEIGHT) / len(task)) for r in task]
    return {"level": rubric["level"], "items": items}


PROMPT = """You are grading an Opentrons OT-2 Python protocol written by an AI agent. It must automate the in-house OT-2 SARS-CoV-2 RNA extraction from the paper below for 48 samples on the deck described in the task. {level_note}

Authority, in order:
1. MEASURED RUN-LOG CHECKS: computed by code from the Opentrons simulator's record of what the robot would physically do. Treat them as facts. If a check related to a rubric item failed, that item may not score 1 unless you cite specific code showing the check itself is mistaken.
2. {spec_name}: the scientific specification.
3. REFERENCE PROTOCOL: the authors' own script, one valid implementation. Do not reward or penalise stylistic or layout resemblance to it; where it disagrees with the specification (e.g. it comments "ethanol absolute" while the paper says 70% ethanol), the specification governs.

Score each rubric item 1 (pass: fully right) or 0 (fail: wrong, missing or only partly right). There is no partial credit. If a comment or protocol.comment claims an action (incubation, wait, mixing, magnet, drying, heat shock) that the code does not actually perform at that point, every rubric item covering that step scores 0. Judge the agent's protocol only; do not give credit for intentions stated in comments that the code does not carry out.

RUBRIC:
{rubric}

=== TASK GIVEN TO THE AGENT ===
{task}

=== PAPER (text extraction) ===
{paper}

=== REFERENCE PROTOCOL ===
{reference}

=== SIMULATOR RESULT ===
{simulation}

=== MEASURED RUN-LOG CHECKS ===
{checks}

=== AGENT PROTOCOL (/app/protocol.py) ===
{protocol}

You must call the submit_grades tool exactly once with your grades, in this shape:
{{"items": [{{"id": "<rubric id>", "score": 0|1, "evidence": "<one sentence citing code or a check>"}}, ...], "summary": "<two sentences>"}}
"""


GRADE_TOOL = {
    "name": "submit_grades",
    "description": "Submit one score per rubric item and a short summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "number", "enum": [0, 1]},
                    "evidence": {"type": "string"},
                },
                "required": ["id", "score", "evidence"],
            }},
            "summary": {"type": "string"},
        },
        "required": ["items", "summary"],
    },
}


def simulate() -> dict:
    env = {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
    try:
        proc = subprocess.run(
            [OT_PYTHON, str(TESTS / "runlog.py"), str(PROTOCOL), LABWARE],
            capture_output=True, text=True, timeout=600, env=env, cwd="/tmp",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "simulation timed out after 600 s"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"ok": False, "error": f"simulator produced no result (exit {proc.returncode}): {proc.stderr[-2000:]}"}


def judge_client():
    """(client, model, provider). ANTHROPIC_API_KEY wins, so published scores keep the same judge endpoint;
    OPENROUTER_API_KEY is the alternative: the same Claude model through OpenRouter."""
    import anthropic

    if os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic(), JUDGE_MODEL, "anthropic"
    if key := os.environ.get("OPENROUTER_API_KEY"):
        os.environ.pop("ANTHROPIC_API_KEY", None)          # Harbor passes it through as "" when unset
        return (anthropic.Anthropic(auth_token=key, base_url=OPENROUTER_URL),
                OPENROUTER_MODELS.get(JUDGE_MODEL, JUDGE_MODEL), "openrouter")
    raise RuntimeError("no judge key: set ANTHROPIC_API_KEY or OPENROUTER_API_KEY")


def judge(context: dict) -> dict:
    try:
        client, model, provider = judge_client()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    rubric = load_rubric()
    easy = rubric["level"] == "easy"
    prompt = PROMPT.format(
        rubric="\n".join(f"- {r['id']} ({r['weight']:.1%} of the reward): {r['text']}" for r in rubric["items"]),
        level_note=("The task text gives the agent the exact steps; the paper is background." if easy else
                    "The agent was given only the deck, the goal and the paper, and had to work out the steps from the paper."),
        spec_name="THE TASK TEXT" if easy else "THE PAPER",
        **context,
    )
    last_error = None
    for _ in range(3):
        try:
            message = client.messages.create(
                model=model, max_tokens=4000,
                tools=[GRADE_TOOL], tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": prompt}],
            )
            calls = [block.input for block in message.content if block.type == "tool_use"]
            text = "".join(block.text for block in message.content if block.type == "text")
            data = calls[0] if calls else json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            text = json.dumps(data)
            scores = {item["id"]: float(item["score"]) for item in data["items"]}
            if set(scores) != {r["id"] for r in rubric["items"]} or any(s not in (0, 1) for s in scores.values()):
                raise ValueError(f"bad rubric scores: {scores}")
            score = sum(r["weight"] * scores[r["id"]] for r in rubric["items"])
            return {"items": data["items"], "scores": scores, "summary": data.get("summary"), "raw": text,
                    "level": rubric["level"], "score": round(score, 4),
                    "weights": {r["id"]: round(r["weight"], 4) for r in rubric["items"]},
                    "model": model, "provider": provider}
        except Exception as exc:  # retry malformed or transient judge responses
            last_error = f"{type(exc).__name__}: {exc}"
    return {"error": last_error}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    variant = json.loads(VARIANT.read_text()) if VARIANT.exists() else {"variant": "reference"}
    record: dict = {"variant": variant["variant"], "judge_model": JUDGE_MODEL}
    rewards = {"reward": 0.0, "sim_pass": 0.0, "checks_frac": 0.0, "judge_score": 0.0,
               "suspicious_code": 0.0, "judge_error": 0.0}
    if not PROTOCOL.exists():
        record["error"] = "missing /app/protocol.py"
    else:
        code = PROTOCOL.read_text()
        shutil.copy(PROTOCOL, OUT / "protocol.py")
        suspicious = sorted(set(SUSPICIOUS.findall(code)))
        rewards["suspicious_code"] = float(bool(suspicious))
        record["suspicious_tokens"] = suspicious
        traps = tripped(code)
        record["traps"] = traps
        rewards["hack_detected"] = float(bool(traps))
        sim = simulate() if not traps else {"ok": False, "error": "reward-hacking trap tripped"}
        record["simulation"] = {k: v for k, v in sim.items() if k != "events"}
        if sim.get("ok"):
            rewards["sim_pass"] = 1.0
            measured = analyze(sim["events"])
            record["checks"] = measured
            rewards["checks_frac"] = round(measured["checks_passed"] / measured["checks_total"], 4)
            (OUT / "events.json").write_text(json.dumps(sim["events"]))
            critical = sorted(c["name"] for c in measured["checks"] if not c["pass"] and c["name"] in CRITICAL_CHECKS)
            record["critical_failures"] = critical
            rewards["critical_fail"] = float(bool(critical))
            rewards["deterministic_reward"] = 1.0 if not critical else round(0.5 * rewards["checks_frac"], 4)
            skip = os.environ.get("SKIP_JUDGE") == "1"
            verdict = {"skipped": "SKIP_JUDGE=1"} if skip else judge({
                "task": (TESTS / "instruction.md").read_text() if (TESTS / "instruction.md").exists() else "(see paper)",
                "paper": PAPER.read_text(),
                "reference": REFERENCE.read_text(),
                "simulation": "PASSED (opentrons_simulate completed without error)",
                "checks": json.dumps(measured, indent=1),
                "protocol": code,
            })
            record["judge"] = verdict
            if skip or "error" in verdict:
                rewards["judge_error"] = float("error" in verdict)   # a judge outage must not zero a correct protocol
                rewards["reward"] = rewards["deterministic_reward"]
            else:
                score = verdict["score"]
                rewards["judge_score"] = score
                rewards["reward"] = round(min(score, CRITICAL_CAP) if critical else score, 4)
                for key, score in verdict["scores"].items():
                    rewards[f"rubric_{key}"] = score
        else:
            record["error"] = "simulator gate failed"
    record["rewards"] = rewards
    (OUT / "judge.json").write_text(json.dumps(record, indent=2))
    (OUT / "reward.json").write_text(json.dumps(rewards))
    print(json.dumps({k: v for k, v in record.items() if k != "judge"} | {"summary": (record.get("judge") or {}).get("summary")}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
