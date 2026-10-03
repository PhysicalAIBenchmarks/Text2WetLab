"""Protocol → numbered plain-English instructions for the downstream parser LLM. No LLM."""

from .models import Protocol, Step

KIND_LABEL = {
    "plate_96": "96-well plate", "plate_96_deep": "96-deep-well plate (2 mL)", "tube_1.5ml": "1.5 mL tube", "tube_15ml": "15 mL tube",
    "tube_50ml": "50 mL tube", "reservoir": "reservoir", "waste": "waste container",
}


def _v(x: float | None) -> str:
    return "stock" if x is None else f"{x:g} µL"


def _loc(container: str | None, wells: list[str]) -> str:
    return f"{container} well{'s' if len(wells) > 1 or ':' in ''.join(wells) else ''} {', '.join(wells)}" if wells else f"{container}"


def step_line(s: Step) -> str:
    if s.kind == "manual":
        line = f"MANUAL: {s.action.rstrip('.')}."
    elif s.kind == "mix":
        line = f"Mix {_loc(s.dest, s.dest_wells)} by pipetting {_v(s.volume_ul)} up and down {s.mix_cycles or 10} times."
    else:
        what = f" of {s.reagent}" if s.reagent else ""
        line = f"Transfer {_v(s.volume_ul)}{what} from {_loc(s.source, s.source_wells)} to {_loc(s.dest, s.dest_wells)}"
        if s.dest_wells and (len(s.dest_wells) > 1 or ":" in "".join(s.dest_wells)):
            line += " (each well)"
        if s.mix_cycles:
            line += f", then mix {s.mix_cycles} times"
        line += "."
    if s.note:
        line += f" Note: {s.note}"
    if s.assumed:
        line += " [assumed]"
    return line


def render(p: Protocol) -> str:
    out = [p.title, "", "Containers:"]
    for c in p.containers:
        out.append(f"- {c.name}: {KIND_LABEL[c.kind]} — {c.description}{' [assumed]' if c.assumed else ''}")
    out += ["", "Starting contents:"]
    for c in p.initial_contents:
        loc = _loc(c.container, c.wells)
        out.append(f"- {loc}: {_v(c.volume_ul)} {c.reagent}{' [assumed]' if c.assumed else ''}")
    out += ["", "Steps:"]
    out += [f"{i}. {step_line(s)}" for i, s in enumerate(p.steps, 1)]
    if p.assumptions:
        out += ["", "Assumptions:"] + [f"- {a}" for a in p.assumptions]
    return "\n".join(out) + "\n"
