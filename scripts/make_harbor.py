"""Generate tasks/<task>/harbor/ for every IR task, the same way every time.

    python scripts/make_harbor.py [--check]       # --check fails if a committed harbor/ folder is stale

For each tasks/<task>/public/ir.json this writes a complete Harbor task:

    harbor/instruction.md     the agent brief: the task text, the FIXED DECK (eval/deck.py), how to simulate, how it is graded
    harbor/task.toml          Harbor settings (same resources and network allowlist as the RNA task)
    harbor/environment/       Dockerfile: Python 3.10 + Opentrons 7.5.0 (/opt/ot) + Claude Code + a pydantic-2 venv for the checker
    harbor/solution/          the reference solution, compiled from the IR (eval/ir_compile.py)
    harbor/tests/             test.sh, grade.py, deck.json, ir.json, and copies of the checker (spec_check, runlog, paper2protocol/*)

Everything is derived from the IR, so the IR stays the one source. The checker files are copies made here; a test
keeps them byte-identical to eval/ and paper2protocol/. The RNA task (opentrons-rna-extraction) is Mohammed's and is
not generated: it has no IR and is graded by an LLM judge.
"""
import argparse
import json
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

CHECKER_COPIES = {  # destination under harbor/tests -> source in the repo
    "spec_check.py": "eval/spec_check.py", "runlog.py": "eval/runlog.py",
    "paper2protocol/__init__.py": "paper2protocol/__init__.py", "paper2protocol/models.py": "paper2protocol/models.py",
    "paper2protocol/timeline.py": "paper2protocol/timeline.py", "paper2protocol/check.py": "paper2protocol/check.py",
    "protocol_lint.py": "eval/protocol_lint.py",
}
RNA = "opentrons-rna-extraction"

DOCKERFILE = (ROOT / f"tasks/{RNA}/harbor/environment/Dockerfile").read_text().replace(
    "COPY data/ /data/\nRUN chmod -R a-w /data\n\n",
    "RUN python -m venv /opt/grader \\\n    && /opt/grader/bin/pip install --no-cache-dir \"pydantic>=2.13\"\n\n")

TASK_TOML = '''schema_version = "1.4"

[task]
name = "text2wetlab/{slug}"
version = "0.1.0"
description = "{description}"
authors = [{{ name = "Text2WetLab" }}]
keywords = ["opentrons", "ot-2", "lab-automation", "protocol-generation"]

[metadata]
source = "{source}"
deck = "specified"
grading = "simulator + deterministic end-state checker (no LLM judge)"

[agent]
timeout_sec = 1800.0

[verifier]
timeout_sec = 900.0

[environment]
network_mode = "allowlist"
allowed_hosts = ["api.anthropic.com", "registry.npmjs.org"]
build_timeout_sec = 1200.0
cpus = 4
memory_mb = 8192
storage_mb = 10240
gpus = 0
'''

BRIEF = '''# {title}

{nl}

Write an Opentrons OT-2 Python protocol that does this, and save it as **`/app/protocol.py`**.

## The robot is set up like this (fixed)

The operator has loaded the deck as below. Load **each labware with its label**, exactly as listed, because the
grader finds your labware by label and checks that it is the labware named here:

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
- Grading is by simulation, not by reading your code. Every well and tube must end holding exactly the volume the
  task implies, and the robot must never pipette without a tip, dispense more than it holds, aspirate from an empty
  well or finish holding a tip. `transfer()`, `distribute()` or your own loops are all fine.
- Steps that are not pipetting (incubating, heat shock, thermocycling, sealing, magnet) cannot be simulated and are
  not graded; record them with `protocol.comment('...')` if you want them in the log.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.
'''

TEST_SH = '''#!/bin/bash
set -uo pipefail
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
/opt/grader/bin/python /tests/grade.py
exit_code=$?
test -f /logs/verifier/reward.json || printf '0\\n' > /logs/verifier/reward.txt
exit "$exit_code"
'''

SOLVE_SH = '''#!/bin/bash
set -euo pipefail
mkdir -p /app
cp "$(dirname "$0")/protocol.py" /app/protocol.py
'''

GRADE_PY = '''#!/usr/bin/env python3
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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protocol.py").write_text(protocol.read_text())     # keep what was graded next to the verdict
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
        "instruction.md": BRIEF.format(title=ir.title, nl=nl, slots=slots, tubes=tubes, contents=contents_text(ir, deck), steps=steps_text(ir, deck)),
        "task.toml": TASK_TOML.format(slug=task.name, description=ir.title.replace('"', "'"), source=meta["metadata"]["source"]),
        "environment/Dockerfile": DOCKERFILE,
        "solution/protocol.py": compile_ir(ir, deck),
        "solution/solve.sh": SOLVE_SH,
        "tests/test.sh": TEST_SH,
        "tests/grade.py": GRADE_PY,
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
        for rel, text in render_files(task).items():
            f = task / "harbor" / rel
            if a.check:
                if not f.exists() or f.read_text() != text:
                    stale.append(f"{task.name}/harbor/{rel}")
            else:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(text)
                if rel.endswith(".sh"):
                    f.chmod(0o755)
        print(("checked " if a.check else "wrote ") + task.name)
    if stale:
        sys.exit("stale generated files (run scripts/make_harbor.py):\n  " + "\n  ".join(stale))


if __name__ == "__main__":
    main()
