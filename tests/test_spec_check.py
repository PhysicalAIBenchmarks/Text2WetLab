import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from paper2protocol.models import Protocol  # noqa: E402
from spec_check import check, error_kind, free_wells, replay  # noqa: E402

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures/events").glob("*.json"))


def task(name):
    d = ROOT / "tasks" / name
    return Protocol.model_validate_json((d / "public/ir.json").read_text()), free_wells(d)


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
    assert (ROOT / "eval/runlog.py").read_bytes() == (ROOT / "tasks/split-200ul-two-wells/tests/runlog.py").read_bytes()


def test_simulator_errors_are_recorded_by_type_never_by_their_random_message():
    """The raw message holds a new UUID and timestamp each run; storing it broke byte-identical reports."""
    a = ("ProtocolEngineExecuteError: [ErrorOccurrence(id='f190f402-8e71', createdAt=datetime(2026, 10, 4), errorType='ExceptionInProtocolError', "
         "detail='...', errorType='TipNotAttachedError')]")
    b = a.replace("f190f402-8e71", "0a1b2c3d-4e5f").replace("10, 4", "11, 9")
    assert error_kind(a) == error_kind(b) == "TipNotAttachedError"
    assert error_kind("RuntimeError: /x is not a directory") == "RuntimeError"


def test_module_labware_named_the_api_2_14_way_still_maps_to_the_deck():
    """From API 2.14 the simulator keys labware on a module as '<label> on ThermocyclerContext at <slot> lw <label>' while
    its pipetting events say '<label> on <slot>'. A correct deck must not fail on that (Opus 5.5 hit it on ecoli-hard)."""
    from spec_check import labware_names
    run = {"labware": {"tp on ThermocyclerContext at Thermocycler Module GEN1 on 7 lw tp": "biorad_96_wellplate_200ul_pcr",
                       "plasmids on 1": "biorad_96_wellplate_200ul_pcr"}}
    assert labware_names(run) == {"tp on Thermocycler Module GEN1 on 7": "biorad_96_wellplate_200ul_pcr",
                                  "plasmids on 1": "biorad_96_wellplate_200ul_pcr"}


def test_a_tip_that_mixed_in_one_sample_cannot_go_on_to_the_next():
    """new_tip='once' + mix_after across wells carries sample A into stock and sample B (the old ampure reference did)."""
    from spec_check import cross_contamination
    pick, drop = {"kind": "pick"}, {"kind": "drop"}
    asp = lambda w, lw="plate": {"kind": "aspirate", "labware": lw, "well": w}
    disp = lambda w, lw="plate": {"kind": "dispense", "labware": lw, "well": w}
    multi_dispense = [pick, asp("A1", "res"), disp("A1"), disp("A2"), asp("A1", "res"), disp("A3"), drop]
    mix_then_next = [pick, asp("A1", "res"), disp("A1"), asp("A1"), disp("A1"), asp("A1", "res"), disp("A2"), drop]
    assert cross_contamination(multi_dispense) == []
    assert cross_contamination(mix_then_next) != []


def test_mixing_a_source_before_drawing_from_it_is_not_contamination():
    """DeepSeek V4 Pro on colony-PCR-hard: fresh tip per colony, mix the colony well, take 1 uL, dispense into its PCR
    well. The mix-tracking rule had flagged every colony; only mixing in a destination carries anything."""
    from spec_check import cross_contamination
    pick, drop = {"kind": "pick"}, {"kind": "drop"}
    asp = lambda w, lw: {"kind": "aspirate", "labware": lw, "well": w}
    disp = lambda w, lw: {"kind": "dispense", "labware": lw, "well": w}
    colony = [pick, asp("A1", "colonies"), disp("A1", "colonies"), asp("A1", "colonies"), disp("A1", "colonies"),
              asp("A1", "colonies"), disp("A1", "pcr"), drop]
    assert cross_contamination(colony) == []
    # still caught: mixing in the destination, then back to the stock and on to the next sample
    dest_mix_then_stock = [pick, asp("A1", "beads"), disp("A1", "samples"), asp("A1", "samples"), disp("A1", "samples"),
                           asp("A1", "beads"), disp("B1", "samples"), drop]
    assert cross_contamination(dest_mix_then_stock) != []


def test_a_container_the_paper_does_not_fix_is_still_checked_for_what_it_does_fix():
    # colony-PCR-hard: any equal reaction of 10-25 uL passes; a missing input, unequal wells or 40 uL do not
    from spec_check import _composition
    proto = Protocol.model_validate_json((ROOT / "tasks/colony-pcr-screening-hard/tests/ir.json").read_text())
    mapping = {"master_mix_reservoir": "mm", "colony_plate": "col", "primer_plate": "pri", "pcr_plate": "pcr"}
    wells = [r + str(c) for r in "ABCDEFGH" for c in range(1, 13)]
    want = {w: 20.0 for w in wells}
    fed_all = {("pcr", w): {"mm", "col", "pri"} for w in wells}
    ok = lambda got, fed=fed_all: _composition("pcr_plate", "pcr", want, got, fed, proto, mapping, (10, 25), False)
    assert ok({w: 11.0 for w in wells})[0]                                  # 9 mix + 1 primer + 1 colony
    assert not ok({w: 40.0 for w in wells})[0]
    assert not ok({**{w: 11.0 for w in wells}, "H12": 41.0})[0]
    assert not ok({w: 11.0 for w in wells[:-1]})[0]
    assert not ok({w: 10.0 for w in wells}, {**fed_all, ("pcr", "A1"): {"mm", "col"}})[0]


def test_non_claude_cost_comes_from_tokens_at_openrouter_prices():
    sys.path.insert(0, str(ROOT / "scripts"))
    from export_run import openrouter_cost
    agent = {"n_input_tokens": 1_000_000, "n_cache_tokens": 800_000, "n_output_tokens": 10_000}
    pricing = {"prompt": "0.000002", "completion": "0.000006", "input_cache_read": "0.00000025"}
    assert openrouter_cost(agent, pricing) == pytest.approx(0.4 + 0.2 + 0.06)
