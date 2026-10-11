"""Can a task's ground-truth IR run on a robot other than the OT-2? A static feasibility check per embodiment.

    fit(protocol, deck, embodiment) -> Fit
    python eval/embodiment_fit.py [--markdown]

Text2WetLab grades OT-2 code, but the IR it grades against says nothing OT-2 specific: containers, wells, volumes. This
asks, step by step, whether the low-cost rigs in qte77's open self-driving-lab stack could execute that IR as written:
the i3 Mega gantry with an 8-channel DLAB dPette+ (qte77/i3mega-pipettebot) and the SO-101 arm with a single-channel
syringe pipette (qte77/so101-biolab-automation). The embodiment numbers are copied from those repos' docs and code
(cited per field below) and are a snapshot, not a contract; when they change, change them here.

It is a reading of the IR, not a simulation. It does not check reach, collisions, liquid classes or timing, and a step
that passes here is "not obviously impossible", nothing more.
"""
import argparse
import json
import pathlib
from collections import defaultdict
from dataclasses import dataclass, field

from paper2protocol.check import expand_wells
from paper2protocol.models import Protocol
from paper2protocol.timeline import pairs

ROOT = pathlib.Path(__file__).parent.parent
ROWS = "ABCDEFGH"


@dataclass(frozen=True)
class Embodiment:
    name: str
    channels: int                                 # 1, or 8 for a fixed-pitch multichannel on one piston
    volume_ranges: tuple[tuple[float, float], ...]  # each a pipette that can be mounted; a run may need several
    swap_is_manual: bool                          # True if changing pipette range means a human remounts it
    container_kinds: frozenset[str]               # what the deck can hold today
    max_labware: int                              # non-tip labware positions on the deck
    fresh_tips: bool                              # can it change tips between steps without a human
    notes: str = ""


ALL_KINDS = frozenset({"plate_96", "plate_96_deep", "tube_1.5ml", "tube_15ml", "tube_50ml", "reservoir", "waste"})

EMBODIMENTS = {
    # Baseline: the deck every task is written for. p20 + p300 single-channel GEN2, 11 slots, two of them tip racks.
    "ot2": Embodiment("OT-2 (p20 + p300)", 1, ((1, 20), (20, 300)), False, ALL_KINDS, 9, True),
    # i3mega-pipettebot docs/hardware.md "dPette+ 8-channel specs": four programmable ranges, one physical pipette
    # mounted at a time (payload cap 300 g, pipette ~250 g). bot.py: the 8 channels share one piston, no per-channel
    # addressing. docs/deck-layout.md: one reservoir, one 96-well plate, a tip box and a tip-release bar on a
    # 220 x 220 mm deck. Tips: pickup and release are scripted in the rows showcase.
    "i3-dpette8": Embodiment(
        "i3 Mega + dPette+ 8-channel", 8, ((0.5, 10), (5, 50), (15, 300), (30, 300)), True,
        frozenset({"plate_96", "plate_96_deep", "reservoir", "waste"}), 2, True,
        "8 channels on one piston: whole columns only"),
    # Same gantry with the single-channel dPette (docs/hardware.md "Product variants"; the _Pipette Protocol allows
    # it). Not built or tested in the repo; ranges assumed equal to the 8-channel's. A tube rack would need a printed
    # holder, so tubes stay out until one exists.
    "i3-dpette1": Embodiment(
        "i3 Mega + dPette single-channel (untested)", 1, ((0.5, 10), (5, 50), (15, 300), (30, 300)), True,
        frozenset({"plate_96", "plate_96_deep", "reservoir", "waste"}), 2, True,
        "hypothetical: same deck, single channel"),
    # so101-biolab-automation pipette.py PipetteConfig.max_volume_ul = 200 (digital-pipette-v2 syringe);
    # pylabrobot_backend.py pick_up_tip() is a placeholder, so a fresh tip per step needs a human. Positions are
    # taught joint poses (architecture.md "No IK"); plate_layout.yaml defines one plate, a tip rack and a trough.
    "so101-syringe": Embodiment(
        "SO-101 + digital-pipette-v2", 1, ((1, 200),), False,
        frozenset({"plate_96", "reservoir", "waste"}), 2, False,
        "taught poses only, no IK; tip pickup not implemented"),
}


@dataclass
class StepFit:
    step: int
    kind: str
    ok: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class Fit:
    embodiment: str
    steps: list[StepFit]
    blockers: list[str]          # deck-level problems that stop the whole run
    ranges_needed: list[tuple[float, float]]

    @property
    def robot_steps(self):
        return [s for s in self.steps if s.kind != "manual"]

    @property
    def runnable(self):
        return not self.blockers and all(s.ok for s in self.robot_steps)


def _covering_ranges(volumes, ranges):
    """Fewest pipette ranges that cover every volume (greedy on the widest range that fits; there are at most four)."""
    left, chosen = sorted(set(volumes)), []
    while left:
        best = max(ranges, key=lambda r: sum(r[0] <= v <= r[1] for v in left))
        hit = [v for v in left if best[0] <= v <= best[1]]
        if not hit:
            break
        chosen.append(best)
        left = [v for v in left if v not in hit]
    return chosen, left


def _whole_columns(wells):
    """True if `wells` is a union of complete A-H columns."""
    by_col = defaultdict(set)
    for w in wells:
        by_col[int(w[1:])].add(w[0])
    return all(rows == set(ROWS) for rows in by_col.values())


def _column_aligned(step_pairs):
    """Each 8-channel load takes 8 sources from one column, row for row, into one destination column."""
    if any(s[:1] != d[:1] for s, d in step_pairs):
        return False
    src_of = defaultdict(set)
    for s, d in step_pairs:
        src_of[int(d[1:])].add(int(s[1:]))
    return all(len(c) == 1 for c in src_of.values())


def _eight_channel_problems(s, kinds):
    """Why an 8-channel head on one piston cannot do step `s` as written ([] if it can)."""
    plate = lambda name: kinds.get(name, "").startswith("plate_96")  # noqa: E731
    if s.kind == "mix":
        ok = not s.dest or not plate(s.dest) or _whole_columns(expand_wells(s.dest_wells, kinds[s.dest]))
        return [] if ok else ["mixes wells that are not whole columns"]
    if any(kinds.get(c, "").startswith("tube") for c in (s.source, s.dest)):
        return ["tubes cannot take an 8-channel head"]
    ps = pairs(s, kinds)
    if not ps:
        return ["source and destination wells do not pair up"]
    # a trough (reservoir, waste) takes all eight tips at once; a plate side must be whole columns
    if plate(s.dest) and not _whole_columns([d for _, d in ps]):
        return ["destination is not whole columns"]
    if plate(s.source) and not _whole_columns([w for w, _ in ps]):
        return ["source is not whole columns"]
    if plate(s.source) and plate(s.dest) and not _column_aligned(ps):
        return ["source wells are not column-aligned with destinations"]
    return []


def fit(proto: Protocol, deck: dict, emb: Embodiment) -> Fit:
    kinds = {c.name: c.kind for c in proto.containers}
    blockers = []
    used = sorted({k for k in kinds.values()})
    bad_kinds = [k for k in used if k not in emb.container_kinds]
    if bad_kinds:
        blockers.append(f"deck cannot hold {', '.join(bad_kinds)}")
    n_labware = len(deck.get("slots", {}))
    if n_labware > emb.max_labware:
        blockers.append(f"needs {n_labware} labware positions, deck has {emb.max_labware}")

    lo = min(r[0] for r in emb.volume_ranges)
    hi = max(r[1] for r in emb.volume_ranges)
    steps, volumes = [], []
    for i, s in enumerate(proto.steps, 1):
        sf = StepFit(i, s.kind, True)
        if s.kind == "manual":
            steps.append(sf)
            continue
        vol = s.volume_ul or 0
        if vol and vol < lo:
            sf.reasons.append(f"{vol:g} µL is below the smallest range ({lo:g} µL)")
        elif vol:
            volumes.append(min(vol, hi))   # above the top range is split into several loads, as on the OT-2
        if emb.channels == 8:
            try:
                sf.reasons += _eight_channel_problems(s, kinds)
            except (ValueError, KeyError) as e:
                sf.reasons.append(f"cannot read wells: {e}")
        if not emb.fresh_tips and s.kind == "transfer" and any(p.kind != "manual" for p in steps):
            sf.reasons.append("no automatic tip change: reuses the previous step's tip")
        sf.ok = not sf.reasons
        steps.append(sf)

    ranges, uncovered = _covering_ranges(volumes, emb.volume_ranges)
    if len(ranges) > 1 and emb.swap_is_manual:
        blockers.append(f"needs {len(ranges)} pipette ranges ({', '.join(f'{a:g}-{b:g}' for a, b in ranges)} µL), "
                        "each a manual remount")
    return Fit(emb.name, steps, blockers, ranges)


def task_irs():
    """(task, Protocol, deck) for every task whose grader ships an IR and a deck."""
    for d in sorted((ROOT / "tasks").iterdir()):
        ir, deck = d / "tests" / "ir.json", d / "tests" / "deck.json"
        if ir.exists() and deck.exists():
            yield d.name, Protocol.model_validate_json(ir.read_text()), json.loads(deck.read_text())


def matrix():
    return {task: {key: fit(p, deck, emb) for key, emb in EMBODIMENTS.items()} for task, p, deck in task_irs()}


def _cell(f: Fit):
    rs = f.robot_steps
    ok = sum(s.ok for s in rs)
    mark = "runs" if f.runnable else ("blocked" if f.blockers else "partial")
    return f"{mark} · {ok}/{len(rs)}"


def to_markdown(m):
    keys = list(EMBODIMENTS)
    out = ["| Task | " + " | ".join(EMBODIMENTS[k].name for k in keys) + " |",
           "|---|" + "---|" * len(keys)]
    for task, row in m.items():
        out.append(f"| `{task}` | " + " | ".join(_cell(row[k]) for k in keys) + " |")
    out += ["", "Each cell: verdict · robot steps that pass / robot steps (manual steps excluded).", ""]
    for task, row in m.items():
        lines = []
        for k in keys:
            f = row[k]
            if k == "ot2" and f.runnable:
                continue
            why = list(f.blockers)
            counts = defaultdict(int)
            for s in f.steps:
                for r in s.reasons:
                    counts[r.split(" µL")[0] if "below the smallest" in r else r] += 1
            why += [f"{r} ({n} step{'s' * (n > 1)})" for r, n in counts.items()]
            if why:
                lines.append(f"- **{f.embodiment}**: " + "; ".join(why))
        if lines:
            out += [f"**`{task}`**", "", *lines, ""]
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", action="store_true", help="print the matrix as a markdown table with reasons")
    args = ap.parse_args()
    m = matrix()
    if args.markdown:
        print(to_markdown(m))
    else:
        for task, row in m.items():
            print(f"{task:40s} " + "  ".join(f"{k}={_cell(f)}" for k, f in row.items()))
