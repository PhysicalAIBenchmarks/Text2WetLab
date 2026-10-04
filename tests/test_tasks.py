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
