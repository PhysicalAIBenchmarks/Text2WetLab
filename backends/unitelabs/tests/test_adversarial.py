"""adversarial.py builds its attacks from any reference; this checks the mutations, not the grading (no SDK here)."""
import json
import pathlib

import adversarial

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_attacks_mutate_the_star_reference():
    task = ROOT / "tasks/star/a1-a12-100ul"
    code = (task / "solution/protocol.py").read_text()
    deck = json.loads((task / "tests/deck.json").read_text())
    out = adversarial.attacks(code, "star", deck, (task / "tests/honeypot.py").read_text())
    assert out["control_reference_solution"] == code
    for name in ("halve_volumes", "double_volumes", "rename_a_labware", "swap_two_labware", "drop_last_dispense",
                 "finish_holding_a_tip", "copy_the_honeypot", "honeypot_without_token"):
        assert out[name] and out[name] != code, name
    assert "volume=50" in out["halve_volumes"] and "volume=200" in out["double_volumes"]
    assert '"plate_x"' in out["rename_a_labware"] or '"reservoir_x"' in out["rename_a_labware"]
