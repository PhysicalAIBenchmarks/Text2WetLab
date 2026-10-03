"""Pydantic models shared by every stage.

Models used as LLM output schemas (ExperimentList, Protocol, CriticReport) stay flat and
simple so they convert cleanly to structured-output JSON schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- paper (ingest output)

class Section(BaseModel):
    id: str                 # stable id, e.g. "s9.4"
    heading: str            # full heading path, e.g. "Methods > Luciferase assay"
    kind: str = ""          # JATS sec-type if present (methods, results, ...)
    text: str


class Legend(BaseModel):
    id: str                 # JATS id, e.g. "F1"
    label: str              # e.g. "Figure 1", "Figure S3"
    title: str
    text: str


class Paper(BaseModel):
    doi: str
    title: str
    abstract: str
    source: str             # where the full text came from
    sections: list[Section]
    legends: list[Legend]

    def section(self, sid: str) -> Section | None:
        return next((s for s in self.sections if s.id == sid), None)


# ---------------------------------------------------------------- identify output

class Experiment(BaseModel):
    title: str = Field(description="Short name of the experiment, e.g. 'HRE-luciferase reporter assay after KDM2B knockdown'")
    goal: str = Field(description="One sentence: what the experiment measures and why")
    section_refs: list[str] = Field(description="Ordered section ids (e.g. 's9.3') of the methods chained together to run this experiment, in bench order")
    shared_refs: list[str] = Field(description="Section ids that supply recipes, reagents or cell lines used by this experiment but are not steps themselves")
    unresolved_refs: list[str] = Field(description="Methods the paper defers elsewhere ('as described previously', 'per manufacturer'), quoted briefly")
    figure_refs: list[str] = Field(description="Figures/panels whose data this experiment produces, e.g. ['Figure 1B', 'Figure S2A']")
    liquid_handling: Literal["mostly", "partly", "little"] = Field(description="How much of this experiment is pipetting liquids between plates/tubes")


class ExperimentList(BaseModel):
    experiments: list[Experiment]


# ---------------------------------------------------------------- extract output

ContainerKind = Literal["plate_96", "tube_1.5ml", "tube_15ml", "tube_50ml", "reservoir", "waste"]

# Working capacity per well/tube in µL; enforced by check.py, not the LLM.
CAPACITY_UL: dict[str, float | None] = {
    "plate_96": 360,
    "tube_1.5ml": 1500,
    "tube_15ml": 15000,
    "tube_50ml": 50000,
    "reservoir": 290000,
    "waste": None,
}


class Container(BaseModel):
    name: str = Field(description="Unique label, e.g. 'plate1', 'siRNA_mix_tube'")
    kind: ContainerKind
    description: str = Field(description="What it holds or is for")
    assumed: bool = Field(description="True if the paper does not specify this container")


class Content(BaseModel):
    container: str
    wells: list[str] = Field(description="Wells like 'A1' or ranges like 'A1:H12'; empty list for a tube/reservoir")
    reagent: str
    volume_ul: float | None = Field(description="Volume per well/tube in µL; null means a stock with ample volume")
    assumed: bool


class Step(BaseModel):
    kind: Literal["transfer", "mix", "manual"]
    # transfer: move volume_ul from source into EACH destination well/tube.
    # One source well feeds every dest; or equal-length lists pair up in order.
    source: str | None = Field(description="Source container name (transfer only)")
    source_wells: list[str] = Field(description="Source wells/ranges (transfer); empty for tubes")
    dest: str | None = Field(description="Destination container name (transfer) or container to mix (mix)")
    dest_wells: list[str] = Field(description="Destination wells/ranges (transfer, mix); empty for tubes")
    volume_ul: float | None = Field(description="µL per destination (transfer) or mix volume (mix)")
    reagent: str = Field(description="What is being moved (transfer); empty otherwise")
    mix_cycles: int | None = Field(description="Mix repetitions (mix, or post-dispense mix for transfer)")
    action: str = Field(description="For manual steps: the non-pipetting action with parameters, e.g. 'Incubate plate1 24 h at 37 °C, 5% CO2'. Empty otherwise")
    source_quote: str = Field(description="Verbatim text from the paper this step comes from; empty if none")
    assumed: bool = Field(description="True if any value in this step is not stated in the paper")
    note: str = Field(description="Short clarification, or empty")


class Protocol(BaseModel):
    title: str
    containers: list[Container]
    initial_contents: list[Content]
    steps: list[Step]
    assumptions: list[str] = Field(description="Every value or choice not stated in the paper, one per line")


# ---------------------------------------------------------------- check / critic

class CheckIssue(BaseModel):
    step: int               # 1-based step number, 0 = global
    severity: Literal["error", "warning"]
    message: str


class CriticIssue(BaseModel):
    step: int = Field(description="1-based step number the issue refers to, 0 if global")
    severity: Literal["major", "minor"]
    issue: str
    suggestion: str


class CriticReport(BaseModel):
    verdict: Literal["ok", "minor_issues", "major_issues"]
    summary: str
    issues: list[CriticIssue]
