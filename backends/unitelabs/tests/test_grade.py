"""grade.py's feasibility branches, run as the verifier runs it: a rendered tests/ folder, /app with INFEASIBLE.md."""
import json
import os
import pathlib
import subprocess
import sys

import make_tasks
import pytest
from devices import DEVICES

ROOT = pathlib.Path(__file__).resolve().parent.parent


def grade(tmp: pathlib.Path, device: str, task: str, infeasible: str | None) -> dict:
    for rel, content in make_tasks.render_task(task, DEVICES[device], "unused", allow_missing=True).items():
        if rel.startswith(("tests/", "environment/data/")):
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode())
    app = tmp / "app"
    app.mkdir()
    if infeasible is not None:
        (app / "INFEASIBLE.md").write_text(infeasible)
    env = dict(os.environ, TESTS_DIR=str(tmp / "tests"), PROTOCOL_PATH=str(app / "protocol.py"),
               VERIFIER_OUT=str(tmp / "out"), DATA_DIR=str(tmp / "environment/data"), SKIP_JUDGE="1")
    subprocess.run([sys.executable, str(tmp / "tests/grade.py")], env=env, capture_output=True, check=True)
    return json.loads((tmp / "out/result.json").read_text())


@pytest.mark.parametrize("ref", sorted((ROOT / "references").glob("*/*.INFEASIBLE.md")),
                         ids=lambda p: f"{p.parent.name}/{p.name}")
def test_reference_refusals_score_1(tmp_path, ref):
    record = grade(tmp_path, ref.parent.name, ref.name.removesuffix(".INFEASIBLE.md"), ref.read_text())
    assert record["rewards"]["reward"] == 1.0, record


@pytest.mark.parametrize("text", ["", "# Infeasible\n\nThis cannot be done.\n",
                                  "The Bravo deck has only 9 locations and this needs 10.",
                                  "The SDK cannot pipette from tubes with the Bravo head."])
def test_refusal_without_the_reason_scores_0(tmp_path, text):
    record = grade(tmp_path, "bravo", "golden-gate-assembly", text)
    assert record["rewards"]["reward"] == 0.0
    assert record["error"].startswith("declared infeasible without naming")


def test_refusing_a_feasible_task_scores_0(tmp_path):
    record = grade(tmp_path, "evo", "ampure-bead-cleanup", "The MCA96 head moves all 96 tips at once.")
    assert record["rewards"]["reward"] == 0.0
    assert record["error"].startswith("declared infeasible, but")


def test_record_names_the_judge_configuration(tmp_path):
    record = grade(tmp_path, "evo", "a1-a12-100ul", "MCA96: all 96 tips")
    assert record["judge_config"] == {"skipped": True}
