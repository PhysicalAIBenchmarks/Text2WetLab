"""Paper → experiments. Experiments are bench workflows that may chain several Methods sections."""

import re

from . import llm
from .ingest import paper_text
from .models import Experiment, ExperimentList, Paper

TASK = """\
Identify the distinct wet-lab EXPERIMENTS in this paper.

An experiment is a bench workflow that produces a specific dataset shown in the figures. \
Methods subsections are NOT 1:1 with experiments: one experiment usually chains several \
subsections in bench order (e.g. cell culture -> siRNA transfection -> hypoxia treatment -> \
lysis -> luciferase assay), and one subsection (e.g. cell culture) can be shared by several \
experiments. Use the Results text and figure legends to see which methods were actually \
combined to produce each figure panel.

Rules:
- section_refs: the ordered section ids (the [sX.Y] tags) whose steps are performed, in bench order.
- shared_refs: section ids that only supply reagents/recipes/cell lines (e.g. a reagents table).
- figure_refs: the figures/panels produced, using the paper's labels (e.g. "Figure 1B").
- Only include wet-lab experiments. Skip purely computational, statistical or \
bioinformatic analyses and cloning-only steps unless they are a lab workflow in their own right.
- Group variants of the same workflow (different cell lines, siRNAs, time points) into one \
experiment unless the bench procedure differs materially.
- Order experiments by first figure appearance.
"""


def identify(paper: Paper) -> list[Experiment]:
    result = llm.structured("identify", paper_text(paper), TASK, ExperimentList)
    return result.experiments


def _fig_key(ref: str) -> str | None:
    """'Figure 2B' -> '2', 'Supplementary Figure 3' / 'Figure S3A' -> 'S3'."""
    m = re.search(r"(S?)(\d+)", ref.replace("Fig. S", "Fig S"), re.I)
    if not m:
        return None
    supp = bool(m.group(1)) or bool(re.search(r"supp|extended|appendix", ref, re.I))
    return ("S" if supp else "") + m.group(2)


def verify_figure_refs(paper: Paper, exp: Experiment) -> list[tuple[str, bool]]:
    """Pair each figure ref with whether it matches a legend label in the paper."""
    known = {_fig_key(lg.label) for lg in paper.legends}
    return [(ref, _fig_key(ref) in known) for ref in exp.figure_refs]
