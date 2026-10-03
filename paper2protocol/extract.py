"""(Paper, Experiment) → structured Protocol of transfers, mixes and manual steps."""

from . import llm
from .ingest import experiment_section_ids, paper_text
from .models import CAPACITY_UL, Experiment, Paper, Protocol

TASK = """\
Convert the experiment below into a liquid-handling protocol for a lab where liquids are held \
in 96-well plates, tubes or reservoirs and moved by pipetting.

EXPERIMENT: {title}
GOAL: {goal}
SECTIONS IN BENCH ORDER: {sections}
SUPPORTING SECTIONS: {shared}
FIGURES: {figures}
DEFERRED METHODS (not described in this paper): {unresolved}

Containers — only these kinds, with working capacity per well/tube:
{capacities}
- Adapt dishes/flasks/6-well plates to a 96-well plate (scale volumes proportionally to \
surface area, 96-well ≈ 0.32 cm²) or tubes, and record each adaptation in `assumptions`.
- Use a container of kind "waste" for removed media/supernatant.

Steps:
- "transfer": move volume_ul from source into EACH destination well/tube. Either one source \
well feeds every destination, or source_wells and dest_wells have equal length and pair in \
order. Wells are "A1" or rectangular ranges "A1:H12". Tubes/reservoirs use empty well lists.
- "mix": pipette-mix dest/dest_wells, volume_ul, mix_cycles.
- "manual": anything that is not pipetting (incubate, centrifuge, seal, shake, thermocycle, \
read plate, image, harvest by scraping, wait). Put the full action with all parameters \
(time, temperature, speed, settings) in `action`; container fields may be null/empty.
- Every reagent a transfer draws from must appear in initial_contents or be filled by an \
earlier step. Stocks with ample volume use volume_ul = null.
- Lay out conditions (siRNAs, treatments, normoxia/hypoxia, replicates, controls) on \
explicit, non-overlapping wells, and state the layout in `assumptions`.
- Include master-mix preparation (e.g. transfection complexes, qPCR mixes) as transfers into tubes.
- Where the paper is silent, use the DETAILS RECOVERED FROM CITED SOURCES (if given) and \
cite their source in `assumptions`; otherwise fill gaps with standard lab practice and set assumed=true on that step/container/content; \
list every assumption. Commercial kits: follow standard manufacturer volumes and say so.
- source_quote: copy the exact sentence fragment from the paper behind each step.
- Keep the protocol to what one person would run for this experiment; do not include analysis.
"""


def extract(paper: Paper, exp: Experiment, details: str = "") -> Protocol:
    """`details` = resolve.details_block(...) output: values recovered from cited sources."""
    refs = experiment_section_ids(paper, exp)
    context = paper_text(paper, section_ids=refs, legends=True) + ("\n\n" + details if details else "")
    task = TASK.format(
        title=exp.title, goal=exp.goal,
        sections=", ".join(f"{r} ({_heading(paper, r)})" for r in exp.section_refs),
        shared=", ".join(f"{r} ({_heading(paper, r)})" for r in exp.shared_refs) or "none",
        figures=", ".join(exp.figure_refs) or "none",
        unresolved="; ".join(exp.unresolved_refs) or "none",
        capacities="\n".join(f"  {k}: {'no limit' if v is None else f'{v:g} µL'}" for k, v in CAPACITY_UL.items()),
    )
    return llm.structured("extract", context, task, Protocol)


def _heading(paper: Paper, sid: str) -> str:
    s = paper.section(sid)
    return s.heading if s else "unknown section"
