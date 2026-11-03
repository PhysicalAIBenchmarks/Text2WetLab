"""The device-agnostic task brief: the same task text, starting contents and steps as upstream's OT-2 brief
(scripts/make_harbor.py renders those from the IR), with the labware given as roles the agent must provide on the
device it is writing for. Nothing in it names carriers, tracks, sites or SDK classes: choosing them is the task.

    python ul/brief.py <upstream task name> <device key>      # print it
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "ul"))
sys.path.insert(0, str(UPSTREAM))
sys.path.insert(0, str(UPSTREAM / "scripts"))
sys.path.insert(0, str(UPSTREAM / "eval"))
from devices import DEVICES  # noqa: E402
from make_harbor import contents_text, source_paper_note, steps_text  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402
from gate import ALLOWED_IMPORTS, ASYNCIO_ALLOWED  # noqa: E402

IMPORTS = ", ".join(f"`{m}`" for m in ["unitelabs", "asyncio", *sorted(ALLOWED_IMPORTS - {"unitelabs", "asyncio"})])
ASYNCIO = ", ".join(f"`{n}`" for n in sorted(ASYNCIO_ALLOWED) if n[0].islower())
# Upstream phrases that describe the OT-2 setup rather than the task: the agent arranges the deck here.
OT2_PHRASES = {
    " (on Opentrons thermocycler module)": "",
    ", on the thermocycler module": "",
    "The deck, the starting contents and": "The labware, the starting contents and",
    "The deck and the starting contents": "The labware and the starting contents",
    "The deck and quantities above are fixed": "The labware and quantities above are fixed",
}


def device_neutral(text: str) -> str:
    for old, new in OT2_PHRASES.items():
        text = text.replace(old, new)
    return text

KIND_TEXT = {   # IR container kind -> what the operator provides
    "plate_96": "a 96-well plate (up to 360 µL per well)",
    "plate_96_deep": "a 96-well deep-well plate (up to 2 mL per well)",
    "reservoir": "a single-well reservoir (trough)",
    "waste": "a waste reservoir (trough)",
    "tube_1.5ml": "a 1.5 mL tube",
    "tube_15ml": "a 15 mL tube",
    "tube_50ml": "a 50 mL tube",
}

BRIEF = '''# {title}

{nl}

Write a Python protocol for {article} **{device}** using the UniteLabs liquid handling SDK that does this.
Save it as **`/app/protocol.py`**.{paper}

## The protocol contract

- Define `async def run({var}, comment)`. `{var}` is the initialized {device} device object with an empty
  deck. Do not create, connect, configure or initialize the device yourself: skip the "connect to the device" parts
  of the documentation.{config_note}
- `comment(text)` records a step that cannot be simulated (see below).
- Import only from {imports}. From `asyncio`, use only {asyncio_names} (and its lock, event, queue and
  exception classes); nothing that starts processes or opens connections.

## The labware

The operator has prepared the labware below. Choose suitable labware classes (and carriers, where the device uses
them) from the SDK's labware library, arrange them on the deck as you see fit, and give each labware **exactly the
identifier listed**: the labware is identified by its identifier.

{labware}

Tips: choose tip racks whose tips suit the volumes in the protocol; tip racks are full.

## What is in the labware at the start

{contents}

Declare these starting contents on the labware (see the liquids documentation); {plenty_note}

## The protocol to implement

{steps}

Where a step lists several wells on both sides, they pair in order (A1 to A1, A2 to A2, and so on); one source well
feeds every listed destination well. "Each" well means every well in the range given.

## Constraints

- Every well must end holding exactly the volume the task implies, and the robot must never pipette without a tip,
  dispense more than it holds, aspirate from an empty well or finish holding a tip.
- Steps that are not pipetting (incubating, magnet, drying, thermocycling) cannot be simulated; record each one with
  `comment('...')` at the point it happens.
- Simulate with: `simulate /app/protocol.py`. It runs your protocol on the simulated {device} and prints what the
  robot did, or the error. Your protocol must run without errors. A completed run does not mean the protocol is
  correct: check yourself that it does exactly what the brief asks, and that the real instrument could do it.
- The SDK documentation is under `/docs/content/`: start with `01.get-started/`, `04.concepts/03.operate/`,
  `06.liquid-handling-and-robots/` and `07.labware/`. The installed SDK source is under
  `/opt/ul/lib/python3.13/site-packages/unitelabs/`. No internet access besides the model API.
- Do not read or write outside `/app`, and do not try to change how the simulator reports its log.

## If this protocol cannot be run on this device

Not every protocol suits every instrument: the pipetting hardware may make a step impossible to carry out as
specified (not merely inconvenient). If that is the case here, do **not** write `/app/protocol.py`. Instead write
**`/app/INFEASIBLE.md`** naming the step and the hardware limitation that rules it out. A protocol that runs in the
simulator but could not do what the task asks on the real instrument is wrong; so is declaring a feasible protocol
infeasible.
'''


def article(name: str) -> str:
    return "an" if name[0].lower() in "aeiou" else "a"


def generic_deck(task: pathlib.Path) -> dict:
    """The container roles of an upstream task: its deck.json labels and wells with the IR's kinds, no slots or
    load names. The same dict renders the brief and, as tests/deck.json, drives the deterministic checks."""
    import json
    ir = Protocol.model_validate_json((task / "tests/ir.json").read_text())
    up = json.loads((task / "tests/deck.json").read_text())
    kinds = {c.name: c.kind for c in ir.containers}
    containers = {}
    for name, spec in up["containers"].items():
        entry = {"label": spec["label"], "kind": kinds.get(name, "plate_96")}
        if spec.get("well"):
            entry["well"] = spec["well"]
        containers[name] = entry
    return {"containers": containers}


def labware_rows(ir: Protocol, deck: dict) -> str:
    rows, racks = [], {}
    for name, spec in deck["containers"].items():
        what = next((c.description for c in ir.containers if c.name == name), "")
        if spec["label"] != name and spec.get("well"):          # a tube in a rack
            racks.setdefault(spec["label"], []).append((name, spec, what))
            continue
        rows.append(f"- `{spec['label']}`: {KIND_TEXT.get(spec['kind'], spec['kind'])}" + (f"; {what}" if what else "") + ".")
    for label, tubes in racks.items():
        kinds = sorted({KIND_TEXT.get(t[1]["kind"], t[1]["kind"]) for t in tubes})
        rows.append(f"- `{label}`: a rack of tubes ({', '.join(k.removeprefix('a ') for k in kinds)}) holding:")
        for name, spec, what in tubes:
            rows.append(f"  - `{name}` at {spec['well']}" + (f": {what}" if what else ""))
    if racks:
        rows.append("\n  Tubes may also be provided as labware of their own (a tube in a carrier's tube spot): then give "
                    "each tube its own name as identifier (e.g. `water`) instead of a rack identifier and well.")
    return "\n".join(rows)


HARD_REPLACED = {"The robot is set up like this (fixed)", "What is in the labware at the start", "Tools and constraints"}
HARD_DROPPED = ("apiLevel", "/app", "internet", "transfer()")


def _sections(text: str) -> tuple[str, dict[str, str]]:
    head, *rest = re.split(r"^## ", text, flags=re.M)
    return head, {s.split("\n", 1)[0].strip(): s.split("\n", 1)[1].strip() for s in rest}


def render_hard(task: pathlib.Path, device) -> str:
    """A paper-only task: upstream's hard instruction.md with its OT-2 deck, API and tool lines replaced. The goal,
    the source-paper note and any fixed design tables stay word for word; the labware and starting contents are
    rendered generically as on easy tasks; there are no steps, as upstream's hard brief has none."""
    ir = Protocol.model_validate_json((task / "tests/ir.json").read_text())
    deck = generic_deck(task)
    head, sections = _sections((task / "instruction.md").read_text())
    title, goal = head.strip().split("\n", 1)
    goal = re.sub(r"\n*Write an Opentrons OT-2 Python protocol.*", "", goal.strip(), flags=re.S).strip()
    keep = [f"## {h}\n\n{b}" for h, b in sections.items() if h not in HARD_REPLACED]
    paper = next(k for k in keep if k.startswith("## Source paper"))
    extra = "\n\n".join(k for k in keep if not k.startswith("## Source paper"))
    constraints = [line.replace("`protocol.comment('...')`", "`comment('...')`").replace("\n  ", " ")
                   for line in re.split(r"\n(?=- )", sections["Tools and constraints"])
                   if not any(w in line for w in HARD_DROPPED)]
    on = f"on {article(device.name)} {device.name}"
    body = BRIEF.format(
        title=title.lstrip("# ").replace("on the OT-2", on), nl=goal.replace("on the OT-2", on),
        device=device.name, article=article(device.name), var=device.var, config_note=f" {device.config_note}" if device.config_note else "",
        paper="\n\n" + paper, labware=labware_rows(ir, deck), contents=contents_text(ir, deck),
        plenty_note='"plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.',
        steps="There are no listed steps: work them out from the paper and the design above.",
        imports=IMPORTS, asyncio_names=ASYNCIO)
    # the fixed design tables go before the labware; the paper's own constraints join ours
    body = body.replace("## The labware\n", (extra + "\n\n## The labware\n") if extra else "## The labware\n", 1)
    body = body.replace("## Constraints\n\n", "## Constraints\n\n" + "\n".join(constraints) + "\n", 1)
    return device_neutral(body)


def render(task_name: str, device_key: str) -> str:
    device = DEVICES[device_key]
    task = UPSTREAM / "tasks" / task_name
    if not (task / "public").exists():
        return render_hard(task, device)
    ir = Protocol.model_validate_json((task / "public/ir.json").read_text())
    deck = generic_deck(task)
    nl = (task / "public/instruction.md").read_text().strip().replace("on the OT-2", f"on {article(device.name)} {device.name}")
    steps = steps_text(ir, deck).replace("`protocol.comment`", "`comment`")
    return device_neutral(BRIEF.format(
        title=ir.title.replace("on the OT-2", f"on {article(device.name)} {device.name}"), nl=nl, device=device.name,
        article=article(device.name), var=device.var,
        config_note=f" {device.config_note}" if device.config_note else "",
        paper=source_paper_note(task), labware=labware_rows(ir, deck), contents=contents_text(ir, deck),
        plenty_note='"plenty" means more than the protocol needs: 90 mL in a reservoir or 100 µL in a well.',
        steps="The task text above says what to do; these are the exact quantities, in order. Do them in this order.\n\n" + steps,
        imports=IMPORTS, asyncio_names=ASYNCIO))


if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2]))
