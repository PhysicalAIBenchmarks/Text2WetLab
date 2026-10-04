import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from protocol_lint import violations  # noqa: E402
from spec_check import cross_contamination  # noqa: E402

TASKS = ROOT / "tasks"
IR_TASKS = sorted(p for p in TASKS.iterdir() if (p / "public/ir.json").exists())
OT = pathlib.Path(os.environ.get("OT_VENV", pathlib.Path.home() / "Desktop/ot-sim-venv")) / "bin/python"


def test_generated_harbor_folders_are_current():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/make_harbor.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("task", IR_TASKS, ids=lambda p: p.name)
def test_every_ir_task_has_the_same_harbor_files(task):
    h = task / "harbor"
    for rel in ("instruction.md", "task.toml", "environment/Dockerfile", "solution/protocol.py", "solution/solve.sh", "tests/test.sh",
                "tests/grade.py", "tests/deck.json", "tests/ir.json", "tests/spec_check.py", "tests/runlog.py", "tests/protocol_lint.py"):
        assert (h / rel).exists(), f"{task.name}/harbor/{rel}"
    deck = json.loads((h / "tests/deck.json").read_text())
    brief = (h / "instruction.md").read_text()
    for spec in deck["slots"].values():
        assert f"`{spec['label']}`" in brief, f"{task.name}: {spec['label']} missing from the brief"
    assert (h / "solution/protocol.py").read_text().count("load_labware(") == len(deck["slots"]) + len(deck["tips"])


def test_the_protocol_lint_accepts_plain_protocols_and_refuses_the_rest():
    ok = "from opentrons import protocol_api\nimport math\nmetadata = {'apiLevel': '2.13'}\n\ndef run(protocol):\n    protocol.comment('hi')\n"
    assert violations(ok) == []
    for bad in ("import os\n", "open('/tests/x')\n", "x = protocol.__class__\n", "protocol_api.ProtocolContext.comment = None\n",
                "raise SystemExit(0)\n", "import subprocess\n", "print(protocol.environ)\n", "x = '/tests/ir.json'\n", "def run(:\n"):
        assert violations(bad), bad


def event(kind, well="A1", labware="p on 1"):
    return {"kind": kind, "well": well, "labware": labware, "volume": 10.0, "channels": 1, "instrument": "x"}


def test_cross_contamination_rules():
    same_source = [event("pick"), event("aspirate", "A1"), event("dispense", "B1"), event("aspirate", "A1"), event("dispense", "B2"), event("drop")]
    assert cross_contamination(same_source) == []                        # multi-dispense from one well
    mixing = [event("pick"), event("aspirate", "A1"), event("dispense", "B1"), event("aspirate", "B1"), event("dispense", "B1"), event("drop")]
    assert cross_contamination(mixing) == []                              # mixing in its own destination
    two_sources = [event("pick"), event("aspirate", "A1"), event("dispense", "B1"), event("aspirate", "A2"), event("dispense", "B2"), event("drop")]
    assert cross_contamination(two_sources) == [(3, "A2")]                # same tip, second source well
    assert cross_contamination([event("pick"), event("aspirate", "A1"), event("drop"), event("pick"), event("aspirate", "A2"), event("drop")]) == []


@pytest.mark.skipif(not OT.exists(), reason="needs the Opentrons 7.5.0 venv (OT_VENV)")
def test_no_attack_beats_the_split_task_grader(tmp_path):
    out = tmp_path / "adv.json"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/harbor_adversarial.py"), "--tasks", "split-200ul-two-wells", "--out", str(out)],
                       capture_output=True, text=True, timeout=900)
    res = json.loads(out.read_text())["split-200ul-two-wells"]
    assert res["control_reference_solution"]["reward"] == 1.0
    assert [n for n, x in res.items() if n != "control_reference_solution" and x.get("reward") == 1.0] == [], r.stdout
