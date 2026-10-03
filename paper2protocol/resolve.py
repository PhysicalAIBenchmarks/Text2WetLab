"""(Paper, Experiment) → Sufficiency: is there enough detail to run this experiment?

Finds the details needed to execute the experiment, fills gaps from cited papers, kit
manuals and other web sources, and returns proceed / proceed_with_assumptions / reject.
"""

from . import guard, llm
from .ingest import experiment_section_ids, paper_text
from .models import Experiment, Paper, Sufficiency

TASK = """\
Decide whether the paper gives enough detail to actually perform this experiment at the bench:

EXPERIMENT: {title}
GOAL: {goal}
SECTIONS IN BENCH ORDER: {sections}
FIGURES: {figures}
DEFERRED METHODS FLAGGED EARLIER: {unresolved}

1. List the details a technician needs to run it: reagent identities and concentrations, \
cell numbers/seeding densities, volumes, incubation times and temperatures, kit procedures, \
instrument settings, and any method the paper defers to another source ("as previously \
described [n]", "according to the manufacturer's instructions").
2. Check each against the paper text above.
3. For each one the paper does not give, {research}
4. Classify every gap:
   - resolved: you found the value or procedure in the paper's own tables, a cited paper, \
kit manual or other reliable source. Give the URL you actually fetched (or the section id).
   - assumable: no source found, but a standard-practice default is defensible and would \
not change what the experiment measures (e.g. PBS wash volume, a mixing step).
   - missing: not found, and guessing would risk invalidating the result (e.g. unknown \
reagent identity or concentration, an unretrievable custom method, an undefined critical \
timing).
5. Verdict:
   - proceed: no gaps, or only trivial ones
   - proceed_with_assumptions: every gap is resolved or assumable
   - reject: any gap is "missing" and would undermine the experiment's measured outcome
Only list gaps that matter for execution; skip analysis and statistics. Put every concrete \
detail you recovered (with its source URL) in retrieved_details so the protocol writer can use it.
"""

RESEARCH_WEB = (
    "you MUST research it with the web_search and web_fetch tools before classifying it: "
    "fetch the cited reference for any deferred method (use the DOI links in REFERENCES; try "
    "open-access copies via PubMed Central or Europe PMC if the publisher page is paywalled), "
    "and fetch the manufacturer's manual/technical bulletin for every commercial kit or "
    "transfection reagent used. Do not answer from memory when a source can be fetched; "
    "only fall back to 'assumable' after a search fails to find the detail. "
    + guard.PROMPT_RULE
)
RESEARCH_OFFLINE = (
    "use your own knowledge of the cited methods and kit manuals, and say so in the source "
    "field (web research is disabled for this run)."
)


def resolve(paper: Paper, exp: Experiment, web: bool = True) -> Sufficiency:
    refs = experiment_section_ids(paper, exp)
    context = paper_text(paper, section_ids=refs, legends=True, references=True)
    heading = lambda r: paper.section(r).heading if paper.section(r) else "unknown section"  # noqa: E731
    task = TASK.format(
        title=exp.title, goal=exp.goal,
        sections=", ".join(f"{r} ({heading(r)})" for r in exp.section_refs),
        figures=", ".join(exp.figure_refs) or "none",
        unresolved="; ".join(exp.unresolved_refs) or "none",
        research=RESEARCH_WEB if web else RESEARCH_OFFLINE,
    )
    return llm.structured("resolve", context, task, Sufficiency, tools=llm.WEB_TOOLS if web else None)


def details_block(s: Sufficiency) -> str:
    """Text appended to extract/critic prompts so they use what resolve found."""
    lines = ["DETAILS RECOVERED FROM CITED SOURCES / KIT MANUALS (use these; cite the source in assumptions):",
             s.retrieved_details or "(none)", "", "GAP ASSESSMENT:"]
    lines += [f"- [{g.status}] {g.detail}: {g.resolution or '—'} ({g.source or 'no source'})" for g in s.gaps]
    return "\n".join(lines)
