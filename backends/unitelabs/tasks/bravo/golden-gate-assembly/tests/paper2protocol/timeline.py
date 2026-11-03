"""Volume timeline over a Protocol: what every well/tube holds after each step. No LLM, no deck/tip model.

Shared by the checker (eval/spec_check.py) and the viewers (eval/ir_viz.py, eval/ir_mujoco.py).
Pairing rules match check.py: one source feeds every destination, equal-length lists pair in order,
many sources into one destination pool.
"""

from .check import expand_wells
from .models import Protocol


def pairs(step, kinds):
    """(source_well, dest_well) pairs for a transfer, same rules as check.py."""
    srcs = expand_wells(step.source_wells, kinds[step.source])
    dests = expand_wells(step.dest_wells, kinds[step.dest])
    if len(srcs) == 1:
        return [(srcs[0], d) for d in dests]
    if len(srcs) == len(dests):
        return list(zip(srcs, dests))
    if len(dests) == 1:
        return [(s, dests[0]) for s in srcs]
    return []


def timeline(p: Protocol):
    """Volume snapshots: state[i] is the state after step i (state[0] = initial).
    Each state maps (container, well) -> µL, or None for a stock with ample volume."""
    kinds = {c.name: c.kind for c in p.containers}
    vol: dict[tuple[str, str], float | None] = {}
    for c in p.initial_contents:
        if c.container not in kinds:
            continue
        for w in expand_wells(c.wells, kinds[c.container]):
            prev = vol.get((c.container, w), 0.0)
            vol[(c.container, w)] = None if c.volume_ul is None or prev is None else prev + c.volume_ul
    states, touched = [dict(vol)], [([], [])]
    for s in p.steps:
        src_t, dst_t = [], []
        try:
            if s.kind == "transfer" and s.source in kinds and s.dest in kinds and s.volume_ul:
                for sw, dw in pairs(s, kinds):
                    cur = vol.get((s.source, sw))
                    if cur is not None:
                        vol[(s.source, sw)] = cur - s.volume_ul
                    if kinds[s.dest] != "waste":
                        cur = vol.get((s.dest, dw), 0.0)
                        vol[(s.dest, dw)] = None if cur is None else cur + s.volume_ul
                    src_t.append((s.source, sw))
                    dst_t.append((s.dest, dw))
            elif s.kind == "mix" and s.dest in kinds:
                dst_t = [(s.dest, w) for w in expand_wells(s.dest_wells, kinds[s.dest])]
        except ValueError:
            pass  # bad well name; check() reports it
        states.append(dict(vol))
        touched.append((src_t, dst_t))
    return states, touched
