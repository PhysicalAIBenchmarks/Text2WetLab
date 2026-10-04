"""Rubric LLM judge that reads the protocol and the simulator run log."""
from __future__ import annotations

import json
import re
from pathlib import Path

JUDGE_MODEL = "claude-sonnet-5-5"

PROMPT = """You are grading an Opentrons OT-2 Python protocol written by an AI agent for the task below.

Authority, in order:
1. SIMULATOR RUN LOG: every robot action recorded by the Opentrons simulator, in order. This is what the robot would physically do. Treat it as fact and check volumes, wells, tips, order and delays against it rather than against your reading of the code.
2. {spec_name}: the scientific specification.
3. REFERENCE PROTOCOL: one valid implementation. Do not reward or penalise stylistic or layout resemblance to it.

Score each rubric item 1 (pass: fully right) or 0 (fail: wrong, missing or only partly right). There is no partial credit. Do not fail an item for a choice the rubric or task allows. If a comment or protocol.comment claims an action (incubation, wait, mixing, magnet, drying, heat shock) that the code does not actually perform at that point, every rubric item covering that step scores 0. Judge the agent's protocol only; do not give credit for intentions stated in comments that the code does not carry out.

RUBRIC:
{rubric}

=== TASK GIVEN TO THE AGENT ===
{task}
{paper_block}
=== REFERENCE PROTOCOL ===
{reference}

=== SIMULATOR RESULT ===
PASSED (opentrons_simulate completed without error)

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


def judge(tests: Path, events: list[dict], protocol: str, paper: Path) -> dict:
    import anthropic

    rubric = json.loads((tests / "rubric.json").read_text())
    has_paper = paper.exists()
    prompt = PROMPT.format(
        spec_name="THE PAPER" if has_paper else "THE TASK TEXT",
        rubric="\n".join(f"- {r['id']}: {r['text']}" for r in rubric),
        task=(tests / "instruction.md").read_text(),
        paper_block=f"\n=== PAPER (text extraction) ===\n{paper.read_text()}\n" if has_paper else "",
        reference=(tests / "reference_protocol.py").read_text(),
        runlog=runlog_text(events),
        protocol=protocol,
    )
    ids = {r["id"] for r in rubric}
    client = anthropic.Anthropic()
    last_error = None
    for _ in range(3):
        try:
            message = client.messages.create(
                model=JUDGE_MODEL, max_tokens=4000,
                tools=[GRADE_TOOL], tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": prompt}],
            )
            calls = [b.input for b in message.content if b.type == "tool_use"]
            text = "".join(b.text for b in message.content if b.type == "text")
            data = calls[0] if calls else json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            scores = {item["id"]: float(item["score"]) for item in data["items"]}
            if set(scores) != ids or any(s not in (0, 1) for s in scores.values()):
                raise ValueError(f"bad rubric scores: {scores}")
            return {"items": data["items"], "scores": scores, "summary": data.get("summary")}
        except Exception as exc:  # retry malformed or transient judge responses
            last_error = f"{type(exc).__name__}: {exc}"
    return {"error": last_error}
