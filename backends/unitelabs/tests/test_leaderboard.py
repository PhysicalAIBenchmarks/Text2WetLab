"""leaderboard.py on a synthetic Harbor job: what is averaged, what is left out, what is never mixed."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
JUDGE = {"skipped": False, "model": "claude-sonnet-5-5", "provider": "anthropic", "votes": 3}


def trial(job: pathlib.Path, name: str, task: str, record: dict | None, model="m") -> None:
    d = job / name
    (d / "verifier").mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({"task_name": f"text2wetlab-ul/{task}",
                                               "agent_info": {"model_info": {"name": model}}}))
    if record is not None:
        (d / "verifier/result.json").write_text(json.dumps(record))


def board(tmp: pathlib.Path) -> dict:
    out = tmp / "board.json"
    subprocess.run([sys.executable, str(ROOT / "ul/leaderboard.py"), str(tmp / "job"), "--out", str(out)],
                   check=True, capture_output=True)
    return json.loads(out.read_text())


def test_aggregation(tmp_path):
    job = tmp_path / "job"
    graded = {"feasible": True, "judge_config": JUDGE}
    trial(job, "t1", "evo.ampure", graded | {"rewards": {"reward": 0.8}})
    trial(job, "t2", "evo.ampure", graded | {"rewards": {"reward": 1.0, "judge_error": 1.0}})   # left out
    trial(job, "t3", "evo.ampure", None)                                                         # verifier missing: 0
    trial(job, "t4", "evo.a1", {"feasible": False, "judge_config": JUDGE, "verdict": "correctly declared infeasible",
                                "rewards": {"reward": 1.0}})
    trial(job, "t5", "evo.ampure", {"feasible": True, "judge_config": {"skipped": True}, "rewards": {"reward": 1.0}},
          model="n")
    b = board(tmp_path)
    judged = b["models"]["m @ evo (judge claude-sonnet-5-5/anthropic/x3)"]
    assert sorted(judged["tasks"]["ampure"]["rewards"]) == [0.0, 0.8]
    assert judged["mean"] == 0.4 and judged["infeasible_recognized"] == 1.0
    assert b["rejudge"] == [str(job / "t2")]
    assert b["models"]["n @ evo (no judge)"]["mean"] == 1.0
    assert "m @ evo (?)" not in b["models"]


def test_deterministic_and_efficiency_columns(tmp_path):
    job, ref = tmp_path / "job", tmp_path / "ref"
    graded = {"feasible": True, "judge_config": JUDGE}
    trial(job, "t1", "star.a1", graded | {"rewards": {"reward": 0.7, "deterministic_reward": 1.0, "checks_frac": 1.0},
                                          "efficiency": {"est_seconds": 300}})
    trial(job, "t2", "star.a1", graded | {"rewards": {"reward": 0.2, "deterministic_reward": 0.4, "checks_frac": 0.5},
                                          "efficiency": {"est_seconds": 50}})      # failed checks: no efficiency
    trial(ref, "o1", "star.a1", {"feasible": True, "judge_config": {"skipped": True},
                                 "rewards": {"reward": 1.0, "checks_frac": 1.0}, "efficiency": {"est_seconds": 200}},
          model="oracle")
    out = tmp_path / "board.json"
    subprocess.run([sys.executable, str(ROOT / "ul/leaderboard.py"), str(job), "--reference", str(ref),
                    "--out", str(out)], check=True, capture_output=True)
    m = json.loads(out.read_text())["models"]["m @ star (judge claude-sonnet-5-5/anthropic/x3)"]
    assert m["mean"] == 0.45 and m["deterministic"] == 0.7
    assert m["time_vs_reference"] == 1.5
