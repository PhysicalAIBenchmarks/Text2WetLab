#!/usr/bin/env python3
"""Grade /app/protocol.py: traps, simulator gate, then a rubric LLM judge that reads the simulator run log."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, "/tests")
from anti_hack import tripped  # noqa: E402

PROTOCOL = Path("/app/protocol.py")
LABWARE = "/data/labware"
PAPER = Path("/data/paper.txt")
REFERENCE = Path("/tests/reference_protocol.py")
OT_PYTHON = "/opt/ot/bin/python"
OUT = Path("/logs/verifier")
JUDGE_MODEL = "claude-sonnet-5-5"
SAFE_ENV_KEYS = ["PATH", "HOME", "LANG", "LC_ALL"]
SUSPICIOUS = re.compile(r"broker|_implementation|_core\b|\.commands\.|publish\(|monkey|__dict__|setattr\(")

RUBRIC = [
    ("sample_handling", "All 48 samples, 250 uL each, one fresh tip per sample, one sample per well, no cross-contamination, and each sample traceable to its elution well."),
    ("binding_and_separation", "40 uL beads, 250 uL isopropanol, then 250 uL sample in that order, mixed 5 times, 5 min incubation, magnet engaged about 4 min, then supernatant removed to waste with the magnet on."),
    ("washes_and_drying", "Two 500 uL 70% ethanol washes, each fully removed with the magnet engaged, then about 4 min air-dry and the magnet disengaged before elution."),
    ("elution_recovery", "100 uL elution added off-magnet and mixed, magnet re-engaged about 90 s, and about 80 uL recovered into a distinct well of the elution plate held at 4 C."),
    ("fidelity_to_paper", "No invented, missing or reordered steps relative to the paper; reagent identities and comments/metadata are accurate."),
]

PROMPT = """You are grading an Opentrons OT-2 Python protocol written by an AI agent. It must automate the in-house OT-2 SARS-CoV-2 RNA extraction from the paper below for 48 samples on the deck described in the task.

Authority, in order:
1. SIMULATOR RUN LOG: every robot action recorded by the Opentrons simulator, in order. This is what the robot would physically do. Treat it as fact and check volumes, wells, tips, order and delays against it rather than against your reading of the code.
2. THE PAPER: the scientific specification.
3. REFERENCE PROTOCOL: the authors' own script, one valid implementation. Do not reward or penalise stylistic or layout resemblance to it; where it disagrees with the paper (e.g. it comments "ethanol absolute" while the paper says 70% ethanol), the paper governs.

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

=== SIMULATOR RUN LOG ===
{runlog}

=== AGENT PROTOCOL (/app/protocol.py) ===
{protocol}

You must call the submit_grades tool exactly once with your grades, in this shape:
{{"items": [{{"id": "<rubric id>", "score": 0|1, "evidence": "<one sentence citing code or run-log lines>"}}, ...], "summary": "<two sentences>"}}
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
            [OT_PYTHON, "/tests/runlog.py", str(PROTOCOL), LABWARE],
            capture_output=True, text=True, timeout=600, env=env, cwd="/tmp",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "simulation timed out after 600 s"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"ok": False, "error": f"simulator produced no result (exit {proc.returncode}): {proc.stderr[-2000:]}"}


def runlog_text(events: list[dict]) -> str:
    lines = []
    for i, e in enumerate(events, 1):
        kind, inst = e["kind"], re.sub(r" on .*", "", e.get("instrument", ""))
        if kind in ("aspirate", "dispense", "air"):
            prep = "into" if kind == "dispense" else "from"
            lines.append(f"{i}. {inst}: {kind} {e['volume']:g} uL {prep} {e['well']} of {e['labware']}")
        elif kind in ("pick", "drop"):
            lines.append(f"{i}. {inst}: {'pick up tip' if kind == 'pick' else 'drop tip'}")
        elif kind == "delay":
            lines.append(f"{i}. delay {e['seconds']:g} s")
        elif kind == "temp":
            lines.append(f"{i}. temperature module set to {e['celsius']:g} C")
        else:
            lines.append(f"{i}. {kind} magnetic module")
    return "\n".join(lines)


def judge(context: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    prompt = PROMPT.format(
        rubric="\n".join(f"- {key}: {text}" for key, text in RUBRIC), **context
    )
    last_error = None
    for _ in range(3):
        try:
            message = client.messages.create(
                model=JUDGE_MODEL, max_tokens=4000,
                tools=[GRADE_TOOL], tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": prompt}],
            )
            calls = [block.input for block in message.content if block.type == "tool_use"]
            text = "".join(block.text for block in message.content if block.type == "text")
            data = calls[0] if calls else json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            text = json.dumps(data)
            scores = {item["id"]: float(item["score"]) for item in data["items"]}
            if set(scores) != {key for key, _ in RUBRIC} or any(s not in (0, 1) for s in scores.values()):
                raise ValueError(f"bad rubric scores: {scores}")
            return {"items": data["items"], "scores": scores, "summary": data.get("summary"), "raw": text}
        except Exception as exc:  # retry malformed or transient judge responses
            last_error = f"{type(exc).__name__}: {exc}"
    return {"error": last_error}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    record: dict = {"judge_model": JUDGE_MODEL}
    rewards = {"reward": 0.0, "sim_pass": 0.0, "judge_mean": 0.0,
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
            (OUT / "events.json").write_text(json.dumps(sim["events"]))
            verdict = judge({
                "task": Path("/tests/instruction.md").read_text() if Path("/tests/instruction.md").exists() else "(see paper)",
                "paper": PAPER.read_text(),
                "reference": REFERENCE.read_text(),
                "simulation": "PASSED (opentrons_simulate completed without error)",
                "runlog": runlog_text(sim["events"]),
                "protocol": code,
            })
            record["judge"] = verdict
            if "error" in verdict:
                rewards["judge_error"] = 1.0
            else:
                mean = sum(verdict["scores"].values()) / len(verdict["scores"])
                rewards["judge_mean"] = rewards["reward"] = round(mean, 4)
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
