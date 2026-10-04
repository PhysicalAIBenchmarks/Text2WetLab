"""
Replay an `opentrons_simulate` run log through WetLabEnv.

    opentrons_simulate protocol.py > run.log
    python eval/trace_replay.py run.log [--gif out.gif]

Only atomic commands are replayed (pick up / aspirate / dispense / drop tip). Composite
lines such as "Transferring ..." are skipped; their nested atomic commands follow them in
the log. Labware is mapped to an env slot by role (tip rack, well plate, reservoir), so
slot numbers on the real deck do not matter.

NOTE: WetLabEnv's T2/T3/T5 are still specific to the L1 200 uL -> 2x100 uL task.
"""

import re
import sys
import pathlib

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wetlab_gym import WetLabEnv

WELL = r"(?P<well>[A-H]\d{1,2})"
PICK = re.compile(rf"Picking up tip from {WELL} of (?P<lw>.+?) on slot")
ASP  = re.compile(rf"Aspirating (?P<vol>[\d.]+) uL from {WELL} of (?P<lw>.+?) on slot")
DISP = re.compile(rf"Dispensing (?P<vol>[\d.]+) uL into {WELL} of (?P<lw>.+?) on slot")
DROP = re.compile(r"(Dropping tip into|Returning tip)")


def slot_for(labware: str) -> int:
    """Env slot by labware role: 0 = tip rack, 1 = well plate, 2 = reservoir."""
    name = labware.lower()
    if "tip rack" in name:
        return 0
    if "reservoir" in name or "trough" in name:
        return 2
    if "plate" in name:
        return 1
    raise ValueError(f"Unsupported labware: {labware!r}")


def well_rc(well: str) -> tuple[int, int]:
    return ord(well[0]) - ord("A"), int(well[1:]) - 1


def action(kind: int, labware: str = "", well: str = "A1", vol: float = 0.0) -> dict:
    slot = slot_for(labware) if labware else 0
    row, col = well_rc(well)
    return {"type": kind, "slot": slot, "row": row, "col": col, "volume": np.array([vol])}


def parse_log(text: str) -> list[dict]:
    actions = []
    for line in text.splitlines():
        line = line.strip()
        if m := PICK.search(line):
            actions.append(action(0, m["lw"], m["well"]))
        elif m := ASP.search(line):
            actions.append(action(1, m["lw"], m["well"], float(m["vol"])))
        elif m := DISP.search(line):
            actions.append(action(2, m["lw"], m["well"], float(m["vol"])))
        elif DROP.search(line):
            actions.append(action(3))
    return actions


def replay(text: str) -> dict:
    """Run the parsed log through the env. Returns criteria, errors per step, final state.
    Every action is replayed: the env's own episode limits (20 steps, stop when T1-T6 pass) would
    hide later faults and cut off long valid protocols."""
    env = WetLabEnv()
    env.MAX_STEPS = 10**9
    env.reset()
    errors = []
    info = {"criteria": {}}
    for i, a in enumerate(parse_log(text), 1):
        _, _, _, _, info = env.step(a)
        errors += [(i, e) for e in info["errors"]]
    return {
        "criteria": info["criteria"],
        "errors": errors,
        "tip_attached": env.pipette_has_tip,
        "pipette_ul": float(env.pipette_volume),
        "plate_ul": env.well_volumes[1].copy(),
        "steps": info.get("steps", 0),
    }


def record(text: str, out: str, fps: int = 3) -> int:
    """Replay the log and save the 2D env view of every step as a GIF/MP4. Returns frame count."""
    import imageio

    env = WetLabEnv(render_mode="rgb_array")
    env.reset()
    frames = [env.render()]
    for a in parse_log(text):
        _, _, terminated, truncated, _ = env.step(a)
        frames.append(env.render())
        if terminated or truncated:
            break
    frames += [frames[-1]] * 3
    if out.endswith(".gif"):
        imageio.mimsave(out, frames, duration=1000 / fps, loop=0)
    else:
        imageio.mimsave(out, frames, fps=fps)
    return len(frames)


if __name__ == "__main__":
    result = replay(pathlib.Path(sys.argv[1]).read_text())
    print("criteria:", result["criteria"])
    print("errors:  ", result["errors"] or "none")
    print("tip attached at end:", result["tip_attached"])
    if "--gif" in sys.argv:
        out = sys.argv[sys.argv.index("--gif") + 1]
        print(f"saved {record(pathlib.Path(sys.argv[1]).read_text(), out)} frames -> {out}")
