"""Rubric LLM judge added on top of the deterministic grader (same scheme as opentrons-rna-extraction)."""
from __future__ import annotations

import json
import re
from pathlib import Path

JUDGE_MODEL = "claude-sonnet-5-5"
CRITICAL_CAP = 0.3

PROMPT = """You are grading an Opentrons OT-2 Python protocol written by an AI agent for the task below.

Authority, in order:
1. MEASURED CHECKS: computed by code from the Opentrons simulator's record of what the robot would physically do. Treat them as facts. If a check related to a rubric item failed, that item may not score 1 unless you cite specific code showing the check itself is mistaken.
2. {spec_name}: the scientific specification.
3. REFERENCE PROTOCOL: one valid implementation. Do not reward or penalise stylistic or layout resemblance to it.

Score each rubric item 0 (wrong or missing), 0.5 (partly right) or 1 (fully right). Judge the agent's protocol only; do not give credit for intentions stated in comments that the code does not carry out.

RUBRIC:
{rubric}

=== TASK GIVEN TO THE AGENT ===
{task}
{paper_block}
=== REFERENCE PROTOCOL ===
{reference}

=== SIMULATOR RESULT ===
PASSED (opentrons_simulate completed without error)

=== MEASURED CHECKS ===
{checks}

=== AGENT PROTOCOL (/app/protocol.py) ===
{protocol}

You must call the submit_grades tool exactly once with your grades, in this shape:
{{"items": [{{"id": "<rubric id>", "score": 0|0.5|1, "evidence": "<one sentence citing code or a check>"}}, ...], "summary": "<two sentences>"}}
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
                    "score": {"type": "number", "enum": [0, 0.5, 1]},
                    "evidence": {"type": "string"},
                },
                "required": ["id", "score", "evidence"],
            }},
            "summary": {"type": "string"},
        },
        "required": ["items", "summary"],
    },
}


def is_critical(name: str) -> bool:
    return name.startswith(("deck_labware", "end_state")) or name in {
        "no_cross_contamination", "tip_before_aspirate", "no_aspirate_from_empty_well", "no_overdispense"}


def judge(tests: Path, checks: list[dict], protocol: str, paper: Path) -> dict:
    import anthropic

    rubric = json.loads((tests / "rubric.json").read_text())
    has_paper = paper.exists()
    prompt = PROMPT.format(
        spec_name="THE PAPER" if has_paper else "THE TASK TEXT",
        rubric="\n".join(f"- {r['id']}: {r['text']}" for r in rubric),
        task=(tests / "instruction.md").read_text(),
        paper_block=f"\n=== PAPER (text extraction) ===\n{paper.read_text()}\n" if has_paper else "",
        reference=(tests / "reference_protocol.py").read_text(),
        checks=json.dumps(checks, indent=1),
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
            if set(scores) != ids or any(s not in (0, 0.5, 1) for s in scores.values()):
                raise ValueError(f"bad rubric scores: {scores}")
            return {"items": data["items"], "scores": scores, "summary": data.get("summary")}
        except Exception as exc:  # retry malformed or transient judge responses
            last_error = f"{type(exc).__name__}: {exc}"
    return {"error": last_error}
