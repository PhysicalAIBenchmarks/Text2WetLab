"""Upstream's rubric and judge prompt, with the OT-2 specifics swapped for the device and the UniteLabs SDK.

    rubric_for(upstream_rubric, device_name) -> rubric      tests/rubric.json for a device task
    prompt_for(upstream_prompt, device_name) -> prompt      judge_layer.PROMPT for a device task

Only the robot and simulator named in the prompt, and the rubric phrases about apiLevel, slots, pipettes and
protocol.comment change. Every task-specific rubric item keeps upstream's wording otherwise, and the scoring
(majority of three votes, 75/25 core/task weights, critical cap) is upstream's judge_layer untouched.
"""
ROBOT_PRACTICE = ("Sound {device} practice with the UniteLabs SDK: the protocol follows the given contract "
                  "(async run({var}, comment)); every volume handled by a tip whose working range covers it (nothing "
                  "below its minimum or above its capacity); no well filled beyond its capacity; the pipetting "
                  "hardware, labware and carriers used as intended and as the real instrument could (a multi-channel "
                  "head moves the same volume in every mounted tip; partial tips only where the head supports them); "
                  "nothing physically unsafe or nonsensical (e.g. pipetting from or into the wrong labware, or "
                  "needless extra handling that puts samples at risk).")
RUBRIC_PHRASES = [
    ("protocol.comment", "comment()"),
    ("Loads the specified labware in the given slots with the given labels, and uses suitable pipettes and tip racks.",
     "Provides every listed labware with exactly the given identifier, of the right kind, placed where the device can "
     "reach it, and uses suitable tips and tip racks."),
    ("using the 300 uL pipette", "using tips of a suitable size"),
    ("with the 20 uL pipette", "with small-volume tips"),
    ("no tip is left on a pipette", "no tip is left on a channel or nozzle"),
    ("whenever the pipette moves on", "whenever a channel or nozzle moves on"),
]
PROMPT_PHRASES = [
    ("You are grading an Opentrons OT-2 Python protocol", "You are grading a {device} Python protocol "
     "(UniteLabs liquid handling SDK)"),
    ("from the Opentrons simulator's record", "from the simulated {device}'s record"),
    ("If a comment or protocol.comment claims", "If a code comment or comment() call claims"),
    ("PASSED (opentrons_simulate completed without error)", "PASSED (the protocol ran on the simulated {device} without error)"),
]


def rubric_for(rubric: dict, device_name: str, var: str) -> dict:
    rubric = {"level": rubric["level"], "core": [dict(r) for r in rubric["core"]], "task": [dict(r) for r in rubric["task"]]}
    for item in rubric["core"] + rubric["task"]:
        if item["id"] == "robot_practice":
            item["text"] = ROBOT_PRACTICE.format(device=device_name, var=var)
        for old, new in RUBRIC_PHRASES:
            item["text"] = item["text"].replace(old, new)
    return rubric


def prompt_for(prompt: str, device_name: str) -> str:
    for old, new in PROMPT_PHRASES:
        assert old in prompt, f"upstream's judge prompt changed: {old!r} not found"
        prompt = prompt.replace(old, new.format(device=device_name))
    return prompt
