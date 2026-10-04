import pathlib
import sys

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

ROOT = pathlib.Path(__file__).parent.parent


def _gl_available():
    try:
        mujoco.Renderer(mujoco.MjModel.from_xml_string("<mujoco/>"), 8, 8).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _gl_available(), reason="no OpenGL context for MuJoCo offscreen rendering")
sys.path.insert(0, str(ROOT / "eval"))
from ir_mujoco import build_frames  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402


def test_a1_a12_renders_and_liquid_appears():
    p = Protocol.model_validate_json((ROOT / "tasks/a1-a12-100ul/ir.json").read_text())
    deck, states, touched, issues, frames, track = build_frames(p)
    first, last = frames[0][0], frames[-1][0]
    assert first.shape == last.shape == (540, 720, 3)
    assert len(frames) > len(p.steps)
    assert not np.array_equal(first, last)  # wells filled, head moved
    assert not issues


def load(name):
    return Protocol.model_validate_json((ROOT / name).read_text())


def test_lifted_travel_has_no_collisions_and_no_lift_does():
    p = load("tasks/split-200ul-two-wells/ir.json")
    *_, lifted = build_frames(p)
    *_, dragged = build_frames(p, lift=False)
    assert lifted["collision"].sum() == 0
    assert dragged["collision"].sum() > 0
    assert dragged["issues"].max() >= dragged["collision"].sum()


def test_tracker_flags_transfer_larger_than_one_pipette_load():
    *_, track = build_frames(load("tasks/a1-a12-100ul/ir.json"), pipette_max=300)
    assert track["trips"].max() == 4          # 12 x 100 uL = 1200 uL = 4 loads of 300
    assert track["held"].max() <= 300         # the tip never holds more than one load


def test_fill_colours():
    from ir_viz import fill_rgb
    assert fill_rgb(0.3) != fill_rgb(0.9)
    assert fill_rgb(1.2) == (1.0, 0.15, 0.15)   # above capacity
    assert fill_rgb(-0.1) == (1.0, 0.0, 0.8)    # overdrawn
    assert fill_rgb(0, stock=True) == (0.0, 0.9, 0.5)
