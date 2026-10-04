import pathlib
import tomllib

import pytest

from paper2protocol.models import Protocol

TASKS = pathlib.Path(__file__).parent.parent / "tasks"
ALL = sorted(p for p in TASKS.iterdir() if p.is_dir())


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_every_task_has_the_same_public_files(task):
    for f in ("instruction.md", "task.toml"):
        assert (task / f).read_text().strip(), f"{task.name}/{f}"
    meta = tomllib.loads((task / "task.toml").read_text())
    assert meta["task"]["name"].replace("/", "-") == task.name   # Harbor namespaces: opentrons/rna-extraction
    if (task / "ir.json").exists():            # the Harbor task is specified by its instruction and grader instead
        assert (task / "assumptions.md").exists()
        proto = Protocol.model_validate_json((task / "ir.json").read_text())
        names = {c.name for c in proto.containers}
        assert set(meta.get("checks", {}).get("free_wells", [])) <= names


def test_no_layer_scheme_is_left():
    assert not [p.name for p in TASKS.iterdir() if p.name in ("L1", "L2")]
    assert not list(TASKS.glob("*/input.nl.txt"))


def test_every_path_a_task_readme_tells_you_to_run_exists():
    import re

    for readme in TASKS.glob("*/README.md"):
        for path in re.findall(r"(?:-p|--path)\s+(tasks/[\w./-]+)", readme.read_text()):
            assert (TASKS.parent / path).exists(), f"{readme.relative_to(TASKS.parent)} runs {path}, which does not exist"


def test_a_grader_that_reads_tests_instruction_md_gets_it():
    """tests/grade.py hands the task text to the LLM judge from /tests/instruction.md and silently falls back to
    '(see paper)' when it is missing. The file was dropped once between two of the author's commits."""
    for task in ALL:
        grade = task / "tests/grade.py"
        if grade.exists() and "/tests/instruction.md" in grade.read_text():
            assert (task / "tests/instruction.md").read_bytes() == (task / "instruction.md").read_bytes(), task.name
