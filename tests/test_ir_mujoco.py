import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from ir_mujoco import build_frames  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402


def test_a1_a12_renders_and_liquid_appears():
    p = Protocol.model_validate_json((ROOT / "tasks/L1/a1-a12-100ul/ir.json").read_text())
    deck, states, touched, issues, frames = build_frames(p)
    first, last = frames[0][0], frames[-1][0]
    assert first.shape == last.shape == (540, 720, 3)
    assert len(frames) > len(p.steps)
    assert not np.array_equal(first, last)  # wells filled, head moved
    assert not issues
