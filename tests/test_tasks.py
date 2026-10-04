import json
import pathlib
import re
import tomllib

import pytest

from paper2protocol.models import Protocol

ROOT = pathlib.Path(__file__).parent.parent
TASKS = ROOT / "tasks"
ALL = sorted(p for p in TASKS.iterdir() if p.is_dir())
SLUGS = {s["slug"] for s in json.loads((ROOT / "sources/sources.json").read_text())}


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_every_task_is_split_into_public_private_harbor(task):
    """public/ is published, private/ and harbor/ are not. Nothing else lives loose in the folder except the manifest."""
    assert {p.name for p in task.iterdir()} - {"__pycache__"} <= {"task.toml", "public", "private", "harbor"}
    assert (task / "public/instruction.md").read_text().strip()
    meta = tomllib.loads((task / "task.toml").read_text())
    assert meta["task"]["name"] == task.name
    if (task / "public/ir.json").exists():       # the Harbor task is specified by its instruction and grader instead
        assert (task / "public/assumptions.md").exists()
        proto = Protocol.model_validate_json((task / "public/ir.json").read_text())
        names = {c.name for c in proto.containers}
        assert set(meta.get("checks", {}).get("free_wells", [])) <= names
    for forbidden in ("tests", "solution", "environment"):
        assert not (task / "public" / forbidden).exists(), f"{task.name}: {forbidden} must not be in public/"


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_a_task_says_where_it_came_from(task):
    """A handwritten task may still cite a paper it was inspired by or is claimed to come from, with the relation
    spelled out; every other task must name its paper. Every cited slug must exist in sources/sources.json."""
    meta = tomllib.loads((task / "task.toml").read_text())
    links = meta.get("source", [])
    if meta["metadata"]["source"] != "handwritten":
        assert links, f"{task.name} is not handwritten and has no [[source]]"
    for s in links:
        assert s["slug"] in SLUGS and s["relation"], f"{task.name}: {s}"


def test_a_harbor_folder_is_a_complete_harbor_task():
    for task in ALL:
        h = task / "harbor"
        if h.exists():
            for need in ("task.toml", "instruction.md", "environment/Dockerfile", "tests/test.sh", "solution/solve.sh"):
                assert (h / need).exists(), f"{task.name}/harbor/{need}"
            meta = tomllib.loads((h / "task.toml").read_text())
            assert re.fullmatch(r"[\w-]+/[\w-]+", meta["task"]["name"])      # Harbor's org/name rule


def test_the_task_text_is_the_same_everywhere_it_is_copied():
    """public/, harbor/ and the grader's tests/ each need the text. One was dropped once between two commits."""
    for task in ALL:
        h = task / "harbor"
        if h.exists():
            want = (task / "public/instruction.md").read_bytes()
            assert (h / "instruction.md").read_bytes() == want, task.name
            grade = h / "tests/grade.py"
            if "/tests/instruction.md" in grade.read_text():
                assert (h / "tests/instruction.md").read_bytes() == want, task.name


def test_no_layer_scheme_is_left():
    assert not [p.name for p in TASKS.iterdir() if p.name in ("L1", "L2")]
    assert not list(TASKS.glob("*/input.nl.txt"))
    assert not [p for p in TASKS.glob("*/*") if p.name in ("ir.json", "instruction.md", "assumptions.md", "solution", "tests")]


def test_every_path_a_task_readme_tells_you_to_run_exists():
    for readme in TASKS.glob("*/harbor/README.md"):
        for path in re.findall(r"(?:-p|--path)\s+(tasks/[\w./-]+)", readme.read_text()):
            assert (ROOT / path).exists(), f"{readme.relative_to(ROOT)} runs {path}, which does not exist"


def test_nothing_is_left_in_the_old_collection_folders():
    assert not [d for d in ("ingestion", "references", "data") if (ROOT / d).exists()]
    assert all((ROOT / "sources" / s / "record.json").exists() for s in SLUGS)
