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


HARBOR = {"task.toml", "instruction.md", "environment", "solution", "tests"}
SPEC = {"public", "private"}       # public/ is the source spec (published); private/ is never published


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_every_task_is_a_harbor_task_with_an_optional_public_spec(task):
    """tasks/<task>/ is the Harbor task itself; public/ and private/ hold the spec it was made from. Nothing else."""
    assert {p.name for p in task.iterdir()} - {"__pycache__"} <= HARBOR | SPEC
    for need in ("task.toml", "instruction.md", "environment/Dockerfile", "tests/test.sh", "solution/solve.sh"):
        assert (task / need).exists(), f"{task.name}/{need}"
    meta = tomllib.loads((task / "task.toml").read_text())
    assert meta["task"]["name"] == f"text2wetlab/{task.name}"           # Harbor's org/name rule
    if (task / "public/ir.json").exists():
        assert (task / "public/assumptions.md").exists()
        assert (task / "public/instruction.md").read_text().strip() in (task / "instruction.md").read_text()
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
    links = meta["metadata"].get("papers", [])   # not [[source]]: Harbor reserves a top-level "source" string
    if meta["metadata"]["source"] != "handwritten":
        assert links, f"{task.name} is not handwritten and has no [[metadata.papers]]"
    for s in links:
        assert s["slug"] in SLUGS and s["relation"], f"{task.name}: {s}"


def test_the_grader_reads_the_brief_the_agent_got():
    """The LLM judge reads a copy of the brief from tests/; that copy was dropped once between two commits."""
    for task in ALL:
        copy = task / "tests/instruction.md"
        if copy.exists():
            assert copy.read_text() == (task / "instruction.md").read_text(), task.name


VENDORED = {"spec_check.py": "eval/spec_check.py", "protocol_lint.py": "eval/protocol_lint.py",
            "paper2protocol/models.py": "paper2protocol/models.py", "paper2protocol/check.py": "paper2protocol/check.py",
            "paper2protocol/timeline.py": "paper2protocol/timeline.py", "paper2protocol/__init__.py": "paper2protocol/__init__.py"}


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_vendored_checker_copies_match_the_repo(task):
    """Graders run in the sandbox with copies of the checker. A copy that drifts silently changes how the task is graded."""
    for rel, src in VENDORED.items():
        copy = task / "tests" / rel
        if copy.exists():
            assert copy.read_text() == (ROOT / src).read_text(), f"{task.name}/tests/{rel} differs from {src}"


def test_no_layer_scheme_is_left():
    assert not [p.name for p in TASKS.iterdir() if p.name in ("L1", "L2")]
    assert not list(TASKS.glob("*/input.nl.txt"))
    assert not list(TASKS.glob("*/harbor")), "the task folder is the Harbor task; harbor/ subfolders were retired"


def test_every_path_a_task_readme_tells_you_to_run_exists():
    for readme in TASKS.glob("*/README.md"):
        for path in re.findall(r"(?:-p|--path)\s+(tasks/[\w./-]+)", readme.read_text()):
            assert (ROOT / path).exists(), f"{readme.relative_to(ROOT)} runs {path}, which does not exist"


def test_nothing_is_left_in_the_old_collection_folders():
    assert not [d for d in ("ingestion", "references", "data") if (ROOT / d).exists()]
    assert all((ROOT / "sources" / s / "record.json").exists() for s in SLUGS)


def test_the_task_sources_table_is_current():
    import subprocess
    import sys

    r = subprocess.run([sys.executable, str(ROOT / "scripts/task_sources.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("task", ALL, ids=lambda p: p.name)
def test_harbor_accepts_the_task(task):
    """Harbor validates task.toml strictly; a top-level [[source]] once made 9 of 11 tasks unloadable."""
    harbor_task = pytest.importorskip("harbor.models.task.task", reason="CI runs this with harbor installed")
    assert harbor_task.Task(task).name == f"text2wetlab/{task.name}"
