"""Grader fixes found by reading the 2026-10-07 benchmark run (results/runs/2026-10-07-openrouter), kept fixed."""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
OT = pathlib.Path(os.environ.get("OT_VENV", ROOT / ".venv-ot")) / "bin/python"
RNA = ["opentrons-rna-extraction", "opentrons-rna-extraction-hard"]
RUN = ROOT / "results/runs/2026-10-07-openrouter"


def rna_checks(task: str):
    spec = importlib.util.spec_from_file_location(f"checks_{task.replace('-', '_')}", ROOT / "tasks" / task / "tests/checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ev(kind, well="A1", slot="5", volume=0.0, channels=8):
    return {"kind": kind, "instrument": "p300_multi", "labware": f"lw on {slot}", "well": well, "volume": volume,
            "channels": channels}


def reservoir_check(task, events):
    return next(c for c in rna_checks(task).analyze(events)["checks"] if c["name"] == "reservoir_columns_within_15ml")


@pytest.mark.parametrize("task", RNA)
def test_drawing_more_than_a_reservoir_column_holds_fails(task):
    # 8 channels x 1000 uL x 2 = 16 mL from one 15 mL column (Sonnet 5.5's ethanol layout)
    events = [ev("pick")] + [e for _ in range(2) for e in (ev("aspirate", "A9", volume=1000), ev("dispense", "A1", slot="1", volume=1000))]
    check = reservoir_check(task, events)
    assert not check["pass"] and "9: 16000" in check["detail"]


@pytest.mark.parametrize("task", RNA)
def test_mixing_in_the_reservoir_is_not_drawing(task):
    # resuspending beads in the trough: 20 x 200 uL x 8 channels moved, nothing taken out
    events = [ev("pick")] + [e for _ in range(20) for e in (ev("aspirate", "A2", volume=200), ev("dispense", "A2", volume=200))]
    assert reservoir_check(task, events)["pass"]


@pytest.mark.parametrize("task", RNA)
def test_reservoir_overdraw_is_critical(task):
    grade = (ROOT / "tasks" / task / "tests/grade.py").read_text()
    assert '"reservoir_columns_within_15ml"' in grade.split("CRITICAL_CHECKS = {", 1)[1].split("}", 1)[0]


@pytest.mark.skipif(not OT.exists(), reason="needs the Opentrons 7.5 simulator venv (set OT_VENV)")
def test_sonnet_rna_protocol_that_overdraws_ethanol_is_capped(tmp_path):
    task = ROOT / "tasks/opentrons-rna-extraction"
    env = dict(os.environ, TESTS_DIR=str(task / "tests"), PROTOCOL_PATH=str(RUN / "claude-sonnet-5.5" / task.name / "protocol.py"),
               VERIFIER_OUT=str(tmp_path), OT_PYTHON=str(OT), RUNLOG=str(task / "tests/runlog.py"),
               DATA_DIR=str(task / "environment/data"), SKIP_JUDGE="1")
    subprocess.run([sys.executable, str(task / "tests/grade.py")], capture_output=True, text=True, env=env, timeout=900)
    rewards = json.loads((tmp_path / "reward.json").read_text())
    assert rewards["critical_fail"] == 1.0 and rewards["deterministic_reward"] < 0.5


JUDGES = sorted(ROOT.glob("tasks/*/tests/judge_layer.py")) + [ROOT / "tasks" / t / "tests/grade.py" for t in RNA]


def load(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(f"judge_{path.parent.parent.name.replace('-', '_')}_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod


def vote(**scores):
    return {"scores": {k: float(v) for k, v in scores.items()},
            "items": [{"id": k, "score": v, "evidence": f"{k}={v}"} for k, v in scores.items()]}


@pytest.mark.parametrize("path", JUDGES, ids=lambda p: p.parent.parent.name)
def test_judge_takes_the_majority_of_three_votes_per_item(path):
    # the same colony-PCR recipe passed on one judge call and failed on another; one call no longer decides
    mod = load(path)
    assert mod.JUDGE_VOTES == 3
    items, scores = mod.majority([vote(a=1, b=0), vote(a=0, b=0), vote(a=1, b=1)], ["a", "b"])
    assert scores == {"a": 1.0, "b": 0.0}
    assert items[0] == {"id": "a", "score": 1, "evidence": "a=1", "votes": [1, 0, 1]}
    assert mod.majority([vote(a=1), vote(a=0)], ["a"])[1] == {"a": 0.0}   # a tie (one vote failed) fails the item


@pytest.mark.parametrize("path", JUDGES, ids=lambda p: p.parent.parent.name)
def test_a_judge_that_errors_on_every_vote_is_a_judge_error(path):
    class Broken:
        class messages:
            @staticmethod
            def create(**_):
                raise TimeoutError("judge down")
    verdict, error = load(path).one_verdict(Broken(), "m", "prompt", {"a"})
    assert verdict is None and "judge down" in error


def test_colony_hard_rubric_leaves_the_primer_volume_to_the_agent():
    rubric = json.loads((ROOT / "tasks/colony-pcr-screening-hard/tests/rubric.json").read_text())
    texts = {i["id"]: i["text"] for i in rubric["core"] + rubric["task"]}
    for item in ("reaction_setup", "fidelity_to_paper"):
        assert "primer volume is the agent's to choose" in texts[item]


def test_end_state_detail_is_not_truncated():
    assert 'f"expected {want}, got {got}")' in (ROOT / "eval/spec_check.py").read_text()


@pytest.mark.skipif(not OT.exists(), reason="needs the Opentrons 7.5 simulator venv (set OT_VENV)")
@pytest.mark.parametrize("model", ["claude-opus-5.5", "claude-fable-5.1"])
def test_paper_only_rna_accepts_any_full_recovery(model, tmp_path):
    # the paper says only "collect the supernatant" after a 100 uL elution: Opus's 100 uL and Fable's 90 uL both follow it.
    # (An earlier version of this test required the hard task to fail 100 uL; the paper-only audit showed that was wrong.)
    task = ROOT / "tasks/opentrons-rna-extraction-hard"
    env = dict(os.environ, TESTS_DIR=str(task / "tests"), PROTOCOL_PATH=str(RUN / model / task.name / "protocol.py"),
               VERIFIER_OUT=str(tmp_path), OT_PYTHON=str(OT), RUNLOG=str(task / "tests/runlog.py"),
               DATA_DIR=str(task / "environment/data"), SKIP_JUDGE="1")
    subprocess.run([sys.executable, str(task / "tests/grade.py")], capture_output=True, text=True, env=env, timeout=900)
    checks = {c["name"]: c for c in json.loads((tmp_path / "judge.json").read_text())["checks"]["checks"]}
    assert "recover_about_80ul" not in checks and checks["recover_70_100ul_one_well_each"]["pass"]


def test_easy_rna_rubric_holds_the_80ul_the_brief_states():
    rubric = json.loads((ROOT / "tasks/opentrons-rna-extraction/tests/rubric.json").read_text())
    text = next(i["text"] for i in rubric["task"] if i["id"] == "elution_recovery")
    assert "Recovering the whole 100 uL fails this item" in text and "Transfer 80 uL of eluate" in text
