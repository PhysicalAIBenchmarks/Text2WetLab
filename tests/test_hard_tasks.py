"""A paper-only (hard) task may grade only what the agent can know: every quantity a deterministic check holds it to
must be in the paper or the brief, or follow from facts that are, by arithmetic shown here. Two hard tasks failed
this before it existed: RNA-hard graded an 80 uL recovery that only the authors' code contains, and colony-PCR-hard
graded a 20 uL reaction where the paper's is 10 uL."""
import importlib.util
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).parent.parent
IR_HARD = ["colony-pcr-screening-hard", "golden-gate-assembly-hard", "ecoli-heat-shock-transformation-hard"]
AMOUNT = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:µ|μ|u)\s?[lL]\b")


def text(task: str, name: str) -> str:
    path = ROOT / "tasks" / task / name
    return path.read_text() if path.exists() else ""


def paper(task: str) -> str:
    p = ROOT / "tasks" / task / "environment/data/paper.txt"
    if not p.exists():
        pytest.skip(f"{task}: the paper is fetched at image build time (not redistributable)")
    return p.read_text()


def amounts(s: str) -> set[float]:
    return {float(m) for m in AMOUNT.findall(s)}


def quoted(task: str, *facts: str) -> None:
    """Each fact the arithmetic below starts from must be in the paper or the brief, word for word."""
    source = paper(task) + text(task, "instruction.md")
    missing = [f for f in facts if f not in source]
    assert not missing, f"{task}: {missing}"


def golden_gate_derived() -> dict[float, str]:
    task = "golden-gate-assembly-hard"
    quoted(task, "PCRs were performed in 25 µL volumes", "0.1 µM primers", "0.5 ng linearized plasmid template",
           "(1 µM)", "0.5 ng/µL", "5X Q5 reaction buffer", "10 mM dNTPs", "for 8 reactions",
           "Each Golden Gate reaction is 20 µL", "10X T4 DNA Ligase Buffer")
    reaction, n = 25.0, 8
    primer = 0.1 / 1 * reaction                  # 0.1 uM final from a 1 uM stock: 2.5 uL each
    template = 0.5 / 0.5                         # 0.5 ng from 0.5 ng/uL: 1 uL
    buffer, dntp, pol = reaction / 5, reaction * 0.2 / 10, 0.25   # 1x from 5X; 200 uM from 10 mM; NEB Q5 0.02 U/uL
    mix = reaction - 2 * primer - template       # master mix per reaction: 19 uL
    water = mix - buffer - dntp - pol            # 13.25 uL per reaction
    gg_water = 20 - (3 + 2 + 3 + 2) - 2 - 1      # 20 uL reaction - fragments - 10X buffer (2 uL) - enzyme mix (1 uL)
    return {primer: "primers, 0.1 µM in 25 µL from 1 µM", template: "template, 0.5 ng from 0.5 ng/µL",
            mix: "master mix per 25 µL reaction", n * buffer: "Q5 buffer for 8 reactions", n * dntp: "dNTPs for 8",
            n * pol: "polymerase for 8", n * water: "water for 8", gg_water: "water to a 20 µL Golden Gate reaction",
            2.0: "10X T4 buffer in 20 µL", 1.0: "enzyme mix (NEB standard)"}


DERIVED = {"golden-gate-assembly-hard": golden_gate_derived}


@pytest.mark.parametrize("task", IR_HARD)
def test_every_graded_volume_is_in_the_paper_or_brief_or_derived_from_them(task):
    tests = ROOT / "tasks" / task / "tests"
    ir = json.loads((tests / "ir.json").read_text())
    not_from_paper = set(json.loads((tests / "checks.json").read_text()).get("not_from_paper", []))
    graded = {float(s["volume_ul"]): f'{s.get("source")} -> {s["dest"]}' for s in ir["steps"]
              if s.get("kind") == "transfer" and s.get("volume_ul") and s.get("dest") not in not_from_paper}
    known = amounts(paper(task)) | amounts(text(task, "instruction.md"))
    derived = DERIVED[task]() if task in DERIVED else {}
    unexplained = {v: where for v, where in graded.items() if v not in known and not any(abs(v - d) < 1e-9 for d in derived)}
    assert not unexplained, f"{task} grades volumes the agent cannot know: {unexplained}"


def test_colony_hard_does_not_grade_the_reaction_volume_the_paper_does_not_fix():
    # ground truth 18 uL master mix + 1 + 1 = 20 uL; the paper's OT-2 reaction is 9 uL mix + 1 uL colony
    nfp = json.loads((ROOT / "tasks/colony-pcr-screening-hard/tests/checks.json").read_text())["not_from_paper"]
    quoted("colony-pcr-screening-hard", "9 μL of this master mix")
    assert nfp["pcr_plate"] == [9 + 1, 25]   # from the paper's OT-2 reaction up to a standard 25 uL Q5 reaction
    assert "not_from_paper" not in json.loads((ROOT / "tasks/colony-pcr-screening/tests/checks.json").read_text())


def rna_checks(task: str):
    spec = importlib.util.spec_from_file_location(f"rna_{task.replace('-', '_')}", ROOT / "tasks" / task / "tests/checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rna_hard_grades_only_what_the_paper_says():
    task = "opentrons-rna-extraction-hard"
    mod = rna_checks(task)
    for name, volume in mod.EXPECTED.items():           # beads, isopropanol, sample, ethanol, elution
        assert volume in amounts(paper(task)), f"{name}: {volume} uL is not in the paper"
    quoted(task, "Air dry for 4 min", "After 30 sec turn on the GEN1 magnetic module",
           "After 90 sec collect the supernatant", "Ethanol 70%", "must be kept at 4 °C")
    assert 80.0 not in amounts(paper(task)) and "80 µL" not in text(task, "instruction.md")
    names = {c["name"] for c in mod.analyze([], "hard")["checks"]}
    assert "recover_about_80ul" not in names                       # the 80 uL is in the authors' code only
    assert "recover_about_80ul" in {c["name"] for c in mod.analyze([], "easy")["checks"]}
    rubric = json.loads(text(task, "tests/rubric.json"))
    recovery = next(i["text"] for i in rubric["task"] if i["id"] == "elution_recovery")
    assert "must not be required" in recovery and "about 80 uL recovered" not in recovery


def test_rna_easy_states_the_80ul_it_grades():
    assert "Transfer 80 µL of eluate" in text("opentrons-rna-extraction", "instruction.md")
