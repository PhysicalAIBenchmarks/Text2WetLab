"""LLM review of a rendered protocol against the source sections. Advisory only."""

from . import llm
from .ingest import paper_text
from .models import CheckIssue, CriticReport, Experiment, Paper

TASK = """\
You are reviewing a liquid-handling protocol that another model produced from the paper \
sections above, for the experiment "{title}" ({figures}).

PROTOCOL:
{protocol}

AUTOMATED CHECK FINDINGS:
{checks}

Review it against the paper. Look for:
- steps from the paper that are missing, or steps that are out of bench order
- numbers (volumes, concentrations, times, temperatures, cell numbers) that contradict the paper
- assumptions that are unreasonable or contradict standard practice
- well layouts that don't cover the conditions/controls in the paper
- causes of the automated check findings
Only flag real problems; minor wording does not matter. Refer to steps by number.
"""


def critique(paper: Paper, exp: Experiment, protocol_text: str, issues: list[CheckIssue]) -> CriticReport:
    refs = exp.section_refs + [r for r in exp.shared_refs if r not in exp.section_refs]
    context = paper_text(paper, section_ids=refs, legends=True)
    checks = "\n".join(f"- step {i.step}: [{i.severity}] {i.message}" for i in issues) or "none"
    task = TASK.format(title=exp.title, figures=", ".join(exp.figure_refs) or "no figures",
                       protocol=protocol_text, checks=checks)
    return llm.structured("critic", context, task, CriticReport)
