import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from ir_viz import find_irs, timeline  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402


def load(path):
    return Protocol.model_validate_json(path.read_text())


def test_every_ir_in_the_repo_validates_and_has_a_timeline():
    irs = find_irs()
    assert len(irs) >= 6
    for path in irs:
        p = load(path)
        states, touched = timeline(p)
        assert len(states) == len(p.steps) + 1 == len(touched)


def test_a1_a12_fills_row_a_with_100ul():
    states, _ = timeline(load(ROOT / "tasks/a1-a12-100ul/public/ir.json"))
    final = states[-1]
    assert [final[("plate", f"A{c}")] for c in range(1, 13)] == [100.0] * 12
    assert final[("reservoir", "")] == 10000 - 1200
