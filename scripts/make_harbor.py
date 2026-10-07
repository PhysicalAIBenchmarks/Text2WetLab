"""Keep the IR-derived files of every IR task in step with its public/ir.json, the same way every time.

    python scripts/make_harbor.py [--check]       # --check fails if a committed derived file is stale

tasks/<task>/ is itself the Harbor task (task.toml, instruction.md, environment/, solution/, tests/). For each
tasks/<task>/public/ir.json this writes the files that follow from the IR:

    instruction.md            the agent brief: the task text, the FIXED DECK (eval/deck.py) and the exact steps
    solution/                 the reference solution, compiled from the IR (eval/ir_compile.py)
    tests/                    deck.json, ir.json, checks.json, and copies of the checker (spec_check, runlog,
                              protocol_lint, paper2protocol/*), kept byte-identical to eval/ and paper2protocol/

The rest of a task is written by hand and left alone: task.toml, environment/, tests/grade.py, judge_layer.py,
rubric.json and the reward-hacking traps. A <task>-hard variant with no public/ of its own gets the same tests/ and
solution/ as its base task (its brief is the paper, not the steps). The RNA task has no IR and is not touched.
"""
import argparse
import json
import re
import pathlib
import shutil
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))
from deck import plan_deck  # noqa: E402
from ir_compile import compile_ir  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402

CHECKER_COPIES = {  # destination under tests/ -> source in the repo
    "spec_check.py": "eval/spec_check.py", "runlog.py": "eval/runlog.py",
    "paper2protocol/__init__.py": "paper2protocol/__init__.py", "paper2protocol/models.py": "paper2protocol/models.py",
    "paper2protocol/timeline.py": "paper2protocol/timeline.py", "paper2protocol/check.py": "paper2protocol/check.py",
    "protocol_lint.py": "eval/protocol_lint.py",
}
RNA = "opentrons-rna-extraction"



BRIEF = '''# {title}

{nl}

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.{paper}

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed:

```python
protocol.load_labware('<load name>', <slot>, label='<label>')
```

| Slot | Labware (load name) | Label |
|---|---|---|
{slots}
{tubes}
Pipettes: `p20_single_gen2` on the **left** (tips `opentrons_96_tiprack_20ul`, slot 10) and `p300_single_gen2` on the
**right** (tips `opentrons_96_tiprack_300ul`, slot 11). Use the one that suits each volume (20 µL pipette: 1–20 µL;
300 µL pipette: 20–300 µL). Tips are unlimited: call `pipette.reset_tipracks()` when you have used a rack.

## What is in the labware at the start

{contents}

## The protocol to implement

The task text above says what to do; these are the exact quantities, in order. Do them with the pipettes, in this order.

{steps}

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Tools and constraints

- Use OT-2 Python API `apiLevel` between `'2.2'` and `'2.15'`; Opentrons 7.5.0 is installed.
- Simulate with: `opentrons_simulate /app/protocol.py`. Your protocol must simulate without errors.
- No internet access besides the model API.
- Every well and tube must end holding exactly the volume the task implies, and the robot must never pipette
  without a tip, dispense more than it holds, aspirate from an empty well or finish holding a tip. `transfer()`, `distribute()` or your own loops are all fine.
- Steps that are not pipetting (incubating, heat shock, thermocycling, sealing, magnet) cannot be simulated; record
  each one with `protocol.comment('...')` at the point it happens.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.
'''


SOLVE_SH = '''#!/bin/bash
set -euo pipefail
mkdir -p /app
cp "$(dirname "$0")/protocol.py" /app/protocol.py
'''



def contents_text(ir: Protocol, deck: dict) -> str:
    lines = []
    for c in ir.initial_contents:
        spec = deck["containers"][c.container]
        where = f"`{spec['label']}`" + (f" well {spec['well']}" if spec.get("well") and not spec["label"] == c.container else "")
        wells = f" wells {', '.join(c.wells)}" if c.wells else ""
        vol = f"{c.volume_ul:g} µL each" if c.volume_ul is not None else "plenty (more than the protocol needs)"
        lines.append(f"- {where}{wells}: {c.reagent.replace('_', ' ')}, {vol}.")
    unloaded = [n for n in deck["containers"] if n not in {c.container for c in ir.initial_contents}]
    for n in unloaded:
        spec = deck["containers"][n]
        what = next(c.description for c in ir.containers if c.name == n)
        lines.append(f"- `{spec['label']}`" + (f" well {spec['well']}" if spec.get("well") else "") + f": empty at the start ({what}).")
    return "\n".join(lines)


def _where(container: str, wells: list[str], deck: dict) -> str:
    spec = deck["containers"][container]
    if wells:
        return f"`{spec['label']}` wells {', '.join(wells)}"
    return f"`{spec['label']}`" + (f" (well {spec['well']})" if spec.get("well") else "")


def steps_text(ir: Protocol, deck: dict) -> str:
    out = []
    for i, st in enumerate(ir.steps, 1):
        if st.kind == "transfer":
            what = st.reagent.replace("_", " ") if st.reagent else "liquid"
            line = f"Transfer {st.volume_ul:g} µL of {what} from {_where(st.source, st.source_wells, deck)} to {_where(st.dest, st.dest_wells, deck)}."
            if st.mix_cycles:
                line += f" Mix {st.mix_cycles} times after dispensing."
        elif st.kind == "mix":
            line = f"Mix {_where(st.dest, st.dest_wells, deck)}, {st.mix_cycles or 3} cycles" + (f" at {st.volume_ul:g} µL." if st.volume_ul else ".")
        else:
            line = f"(Not simulated, record with `protocol.comment`) {st.action or st.note}"
        out.append(f"{i}. {line}")
    return "\n".join(out)


def source_paper_note(task: pathlib.Path) -> str:
    """A task that ships the paper as /data/paper.txt says so in a hand-written "## Source paper" paragraph after the
    "Write ... /app/protocol.py" line; keep it."""
    brief = task / "instruction.md"
    m = re.search(r"\n\n(## Source paper\n\n.+?)\n\n", brief.read_text() if brief.exists() else "", re.S)
    return "\n\n" + m[1] if m else ""


def render_files(task: pathlib.Path) -> dict[str, str]:
    ir = Protocol.model_validate_json((task / "public/ir.json").read_text())
    meta = tomllib.loads((task / "task.toml").read_text())
    deck = plan_deck(ir)
    nl = (task / "public/instruction.md").read_text().strip()
    slots = "\n".join(f"| {s} | `{v['load_name']}` | `{v['label']}` |" for s, v in sorted(deck["slots"].items(), key=lambda kv: int(kv[0])))
    tube_rows = [(n, v) for n, v in deck["containers"].items() if v["label"] != n and "tuberack" in v["load_name"]]
    tubes = ""
    if tube_rows:
        tubes = "\nTubes sit in the racks like this:\n\n| Tube | Rack label | Well |\n|---|---|---|\n" + "\n".join(
            f"| {n} | `{v['label']}` | {v['well']} |" for n, v in tube_rows) + "\n"
    files = {
        "instruction.md": BRIEF.format(title=ir.title, nl=nl, paper=source_paper_note(task), slots=slots, tubes=tubes,
                                       contents=contents_text(ir, deck), steps=steps_text(ir, deck)),
        "solution/protocol.py": compile_ir(ir, deck),
        "solution/solve.sh": SOLVE_SH,
        "tests/deck.json": json.dumps(deck, indent=1) + "\n",
        "tests/ir.json": (task / "public/ir.json").read_text(),
        "tests/checks.json": json.dumps({"free_wells": sorted(meta.get("checks", {}).get("free_wells", []))}) + "\n",
    }
    for dst, src in CHECKER_COPIES.items():
        files[f"tests/{dst}"] = (ROOT / src).read_text()
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    stale = []
    for task in sorted((ROOT / "tasks").iterdir()):
        if task.name == RNA or not (task / "public/ir.json").exists():
            continue
        files = render_files(task)
        targets = [(task, files)]
        hard = task.with_name(task.name + "-hard")
        if hard.is_dir() and not (hard / "public").exists() and (hard / "tests/ir.json").read_text() == files["tests/ir.json"]:
            targets.append((hard, {k: v for k, v in files.items() if k != "instruction.md"}))
        for folder, out in targets:
            for rel, text in out.items():
                f = folder / rel
                if a.check:
                    if not f.exists() or f.read_text() != text:
                        stale.append(f"{folder.name}/{rel}")
                else:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text(text)
                    if rel.endswith(".sh"):
                        f.chmod(0o755)
            print(("checked " if a.check else "wrote ") + folder.name)
    if stale:
        sys.exit("stale derived files (run scripts/make_harbor.py):\n  " + "\n  ".join(stale))


if __name__ == "__main__":
    main()
