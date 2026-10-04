import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from paper2protocol.models import Protocol  # noqa: E402
from spec_check import check, free_wells, replay  # noqa: E402

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures/events").glob("*.json"))


def task(name):
    d = ROOT / "tasks" / name
    return Protocol.model_validate_json((d / "ir.json").read_text()), free_wells(d)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_real_simulator_traces_are_judged_correctly(path):
    """Seven-plus real traces, valid and faulty. The verdict must match ground truth, whichever API produced it."""
    fx = json.loads(path.read_text())
    proto, free = task(fx["task"])
    res = check(proto, {"ok": True, "events": fx["events"]}, free)
    assert res["passed"] == fx["expected_pass"], [c for c in res["checks"] if not c["pass"]]


def failed(res):
    return {c["name"] for c in res["checks"] if not c["pass"]}


def test_each_fault_is_caught_by_the_check_meant_for_it():
    cases = {"split-200ul-two-wells__same_well_twice": "end_state:plate", "split-200ul-two-wells__no_drop_tip": "tip_dropped_at_end",
             "a1-a12-100ul__wrong_row_B": "end_state:plate", "a1-a12-100ul__single_aspirate": "no_overdispense"}
    for stem, name in cases.items():
        fx = json.loads((pathlib.Path(__file__).parent / f"fixtures/events/{stem}.json").read_text())
        proto, free = task(fx["task"])
        assert name in failed(check(proto, {"ok": True, "events": fx["events"]}, free)), stem


def test_simulator_crash_fails_the_run():
    proto, free = task("a1-a12-100ul")
    res = check(proto, {"ok": False, "error": "TipNotAttachedError"}, free)
    assert not res["passed"] and failed(res) == {"simulator_ran"}


def test_free_wells_judge_volumes_not_positions_but_named_wells_are_enforced():
    fx = json.loads((pathlib.Path(__file__).parent / "fixtures/events/split-200ul-two-wells__other_two_wells.json").read_text())
    proto, free = task("split-200ul-two-wells")
    assert free == {"plate"} and check(proto, {"ok": True, "events": fx["events"]}, free)["passed"]
    assert not check(proto, {"ok": True, "events": fx["events"]}, frozenset())["passed"]   # strict: A1/B1 only


def test_replay_covers_long_protocols_and_flags_empty_sources():
    asp = {"kind": "aspirate", "volume": 10.0, "well": "A1", "labware": "Agilent 1 Well Reservoir 290 mL on slot 3", "instrument": "P300"}
    disp = {"kind": "dispense", "volume": 10.0, "labware": "Corning 96 Well Plate 360 µL Flat on slot 2", "instrument": "P300"}
    events = [{"kind": "pick"}]
    for c in range(1, 13):
        events += [dict(asp), dict(disp, well=f"A{c}")]
    events.append({"kind": "drop"})
    st = replay(events)                                   # 26 events: nothing may truncate the replay
    assert not st.errors and not st.tip and sum(st.wells.values()) == 120
    bad = replay([{"kind": "pick"}, dict(asp, labware="Corning 96 Well Plate 360 µL Flat on slot 2", well="H12")])
    assert (1, "aspirate_from_empty") in bad.errors


def test_eight_channel_events_touch_all_rows():
    plate = "Corning 96 Well Plate 360 µL Flat on slot 2"
    st = replay([{"kind": "pick"}, {"kind": "aspirate", "volume": 5.0, "well": "A1", "channels": 8, "labware": "Agilent 1 Well Reservoir 290 mL on slot 3", "instrument": "P300"},
                 {"kind": "dispense", "volume": 5.0, "well": "A1", "channels": 8, "labware": plate, "instrument": "P300"}, {"kind": "drop"}])
    assert sorted(w for (_, w) in st.wells) == [f"{r}1" for r in "ABCDEFGH"]


def test_eval_runlog_is_identical_to_the_harbor_graders_copy():
    """The Harbor task ships its own runlog.py (it runs in Docker). Both must parse the log the same way."""
    assert (ROOT / "eval/runlog.py").read_bytes() == (ROOT / "tasks/opentrons-rna-extraction/tests/runlog.py").read_bytes()
