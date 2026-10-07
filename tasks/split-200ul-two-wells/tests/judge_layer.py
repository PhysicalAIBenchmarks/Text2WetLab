"""Rubric LLM judge added on top of the deterministic grader (same scheme as opentrons-rna-extraction).

tests/rubric.json holds {"level": "easy"|"hard", "core": [...], "task": [...]}. The three core items (robot practice,
tips and contamination, fidelity) are in every task and share CORE_WEIGHT equally; the task-specific items share the
rest. Every item is scored 1 or 0 by the judge.

Levels: "easy" tasks give the agent the exact steps, so the task text is the specification and every end-state check
is a hard fact. "hard" tasks give only the deck, the goal and the paper, so the paper is the specification; the
end-state checks then describe one reference implementation and are evidence, not requirements.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

JUDGE_MODEL = os.environ.get("JUDGE_MODEL") or "claude-sonnet-5-5"
OPENROUTER_URL = "https://openrouter.ai/api"      # OpenRouter's Anthropic-compatible Messages API
OPENROUTER_MODELS = {"claude-sonnet-5-5": "anthropic/claude-sonnet-5.5", "claude-opus-5-5": "anthropic/claude-opus-5.5",
                     "claude-fable-5-1": "anthropic/claude-fable-5.1"}


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
CRITICAL_CAP = 0.3
CORE_WEIGHT = 0.75
SAFETY_CHECKS = {"no_cross_contamination", "tip_before_aspirate", "no_aspirate_from_empty_well", "no_overdispense"}

PROMPT = """You are grading an Opentrons OT-2 Python protocol written by an AI agent for the task below.

Authority, in order:
1. MEASURED CHECKS: computed by code from the Opentrons simulator's record of what the robot would physically do. Treat them as facts. If a check related to a rubric item failed, that item may not score 1 unless you cite specific code showing the check itself is mistaken.{end_state_note}
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

=== MEASURED CHECKS ===
{checks}

=== AGENT PROTOCOL (/app/protocol.py) ===
{protocol}

You must call the submit_grades tool exactly once with your grades, in this shape:
{{"items": [{{"id": "<rubric id>", "score": 0|1, "evidence": "<one sentence citing code or a check>"}}, ...], "summary": "<two sentences>"}}
"""

HARD_END_STATE_NOTE = (
    " Exception: this is a paper-level task, so the end_state:* checks compare against the reference protocol's"
    " quantities, not against requirements. A failed end_state check is evidence to weigh, not a fact that fails an"
    " item: pass the item if the agent's quantities are what the paper specifies, or a sound adaptation to the given"
    " deck and reagents.")

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


def load_rubric(tests: Path) -> dict:
    """The rubric with a weight on every item: core items share CORE_WEIGHT, task items share the rest."""
    rubric = json.loads((tests / "rubric.json").read_text())
    core, task = rubric["core"], rubric["task"]
    items = [dict(r, group="core", weight=CORE_WEIGHT / len(core)) for r in core]
    items += [dict(r, group="task", weight=(1 - CORE_WEIGHT) / len(task)) for r in task]
    return {"level": rubric["level"], "items": items}


def weighted_score(rubric: dict, scores: dict[str, float]) -> float:
    return sum(item["weight"] * scores[item["id"]] for item in rubric["items"])


def is_critical(name: str, level: str = "easy") -> bool:
    """Checks that cap the reward when they fail. On hard tasks the end state is the agent's to work out from the
    paper, so only the deck and the safety rules are critical there."""
    if name.startswith("deck_labware") or name in SAFETY_CHECKS:
        return True
    return level == "easy" and name.startswith("end_state")


def judge(tests: Path, checks: list[dict], protocol: str, paper: Path) -> dict:
    rubric = load_rubric(tests)
    hard = rubric["level"] == "hard"
    has_paper = paper.exists()
    prompt = PROMPT.format(
        end_state_note=HARD_END_STATE_NOTE if hard else "",
        spec_name="THE PAPER" if hard else "THE TASK TEXT" + (" (the paper is background only)" if has_paper else ""),
        rubric="\n".join(f"- {r['id']} ({r['weight']:.1%} of the reward): {r['text']}" for r in rubric["items"]),
        task=(tests / "instruction.md").read_text(),
        paper_block=f"\n=== PAPER (text extraction) ===\n{paper.read_text()}\n" if has_paper else "",
        reference=(tests / "reference_protocol.py").read_text(),
        checks=json.dumps(checks, indent=1),
        protocol=protocol,
    )
    ids = {r["id"] for r in rubric["items"]}
    try:
        client, model, provider = judge_client()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    last_error = None
    for _ in range(3):
        try:
            message = client.messages.create(
                model=model, max_tokens=4000,
                tools=[GRADE_TOOL], tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": prompt}],
            )
            calls = [b.input for b in message.content if b.type == "tool_use"]
            text = "".join(b.text for b in message.content if b.type == "text")
            data = calls[0] if calls else json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            scores = {item["id"]: float(item["score"]) for item in data["items"]}
            if set(scores) != ids or any(s not in (0, 1) for s in scores.values()):
                raise ValueError(f"bad rubric scores: {scores}")
            return {"items": data["items"], "scores": scores, "summary": data.get("summary"),
                    "level": rubric["level"], "score": round(weighted_score(rubric, scores), 4),
                    "weights": {r["id"]: round(r["weight"], 4) for r in rubric["items"]},
                    "model": model, "provider": provider}
        except Exception as exc:  # retry malformed or transient judge responses
            last_error = f"{type(exc).__name__}: {exc}"
    return {"error": last_error}
