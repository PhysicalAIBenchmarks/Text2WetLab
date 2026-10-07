"""Every task's reference solution must pass its own grader. Runs each tasks/<task>/tests/grade.py on solution/protocol.py
outside Docker with SKIP_JUDGE=1, so it needs no API key: lint, reward-hacking traps, simulator and end-state checks.
The full Harbor run with the LLM judge is the harbor-oracle CI job."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
TASKS = sorted(p for p in (ROOT / "tasks").iterdir() if (p / "tests/grade.py").exists())
OT = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path.home() / "Desktop/ot-sim-venv")) / "bin/python"


@pytest.mark.skipif(not OT.exists(), reason="needs the Opentrons 7.5 simulator venv (set OT_VENV)")
@pytest.mark.parametrize("task", TASKS, ids=lambda p: p.name)
def test_the_reference_solution_passes_its_own_grader(task, tmp_path):
    data = task / "environment/data"
    shipped = json.loads((task / "tests/data_hashes.json").read_text()) if (task / "tests/data_hashes.json").exists() else {}
    missing = [f for f in shipped if not (data / f).exists()]
    if missing:
        pytest.skip(f"{missing} is fetched at image build time (not redistributable); covered by the Docker oracle job")
    env = dict(os.environ, TESTS_DIR=str(task / "tests"), PROTOCOL_PATH=str(task / "solution/protocol.py"),
               VERIFIER_OUT=str(tmp_path), OT_PYTHON=str(OT), RUNLOG=str(task / "tests/runlog.py"),
               DATA_DIR=str(data), SKIP_JUDGE="1")
    if (data / "labware").is_dir():
        env["LABWARE_DIR"] = str(data / "labware")
    r = subprocess.run([sys.executable, str(task / "tests/grade.py")], capture_output=True, text=True, env=env, timeout=900)
    assert (tmp_path / "reward.json").exists(), r.stderr[-2000:]
    rewards = json.loads((tmp_path / "reward.json").read_text())
    assert rewards.get("deterministic_reward") == 1.0, r.stdout[-3000:]
