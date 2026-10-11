import pathlib
import sys
from dataclasses import replace

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from embodiment_fit import EMBODIMENTS, _covering_ranges, fit, matrix, task_irs, to_markdown  # noqa: E402
from paper2protocol.models import Protocol  # noqa: E402


def proto(steps, containers=(("trough", "reservoir"), ("plate", "plate_96"))):
    return Protocol.model_validate({
        "title": "t",
        "containers": [{"name": n, "kind": k, "description": "", "assumed": False} for n, k in containers],
        "initial_contents": [],
        "steps": [{"kind": "transfer", "source": "trough", "source_wells": [], "dest": "plate", "dest_wells": [],
                   "volume_ul": 50, "reagent": "x", "mix_cycles": None, "action": "", "source_quote": "",
                   "assumed": False, "note": "", **s} for s in steps],
        "assumptions": [],
    })


DECK = {"slots": {"1": {}, "2": {}}}


def test_every_task_ir_runs_on_the_ot2_it_was_written_for():
    m = matrix()
    assert len(m) >= 9
    for task, row in m.items():
        assert row["ot2"].runnable, (task, row["ot2"].blockers, [s.reasons for s in row["ot2"].steps if s.reasons])


def test_eight_channel_needs_whole_columns():
    eight = EMBODIMENTS["i3-dpette8"]
    assert fit(proto([{"dest_wells": ["A1:H3"]}]), DECK, eight).runnable
    f = fit(proto([{"dest_wells": ["A1:A12"]}]), DECK, eight)
    assert not f.runnable and f.steps[0].reasons == ["destination is not whole columns"]


def test_eight_channel_plate_to_plate_must_keep_rows():
    eight = EMBODIMENTS["i3-dpette8"]
    two = (("src", "plate_96"), ("plate", "plate_96"))
    same = proto([{"source": "src", "source_wells": ["A1:H1"], "dest_wells": ["A2:H2"]}], two)
    assert fit(same, DECK, eight).runnable
    # pairs() zips row-major, so a column-to-row reshuffle pairs A1->A1, B1->A2, ... : rows do not line up
    shuffled = proto([{"source": "src", "source_wells": ["A1:H1"], "dest_wells": ["A1:A8"]}], two)
    assert not fit(shuffled, DECK, eight).runnable


def test_tubes_and_small_volumes_and_deck_size_block():
    eight, so101 = EMBODIMENTS["i3-dpette8"], EMBODIMENTS["so101-syringe"]
    tubes = proto([{"source": "tube", "dest_wells": ["A1:H1"]}], (("tube", "tube_1.5ml"), ("plate", "plate_96")))
    f = fit(tubes, DECK, eight)
    assert any("tube_1.5ml" in b for b in f.blockers) and "tubes cannot take an 8-channel head" in f.steps[0].reasons
    assert fit(proto([{"dest_wells": ["A1"], "volume_ul": 0.5}]), DECK, so101).steps[0].reasons
    assert any("labware positions" in b for b in fit(proto([{}]), {"slots": dict.fromkeys("123")}, so101).blockers)


def test_no_tip_changer_flags_every_transfer_after_the_first():
    f = fit(proto([{"dest_wells": ["A1"]}, {"dest_wells": ["B1"]}]), DECK, EMBODIMENTS["so101-syringe"])
    assert [s.ok for s in f.steps] == [True, False]


def test_range_cover_counts_manual_remounts():
    ranges = EMBODIMENTS["i3-dpette8"].volume_ranges
    assert _covering_ranges([100, 250], ranges) == ([(15, 300)], [])
    chosen, left = _covering_ranges([1, 18], ranges)
    assert len(chosen) == 2 and not left
    f = fit(proto([{"dest_wells": ["A1:H1"], "volume_ul": 1}, {"dest_wells": ["A2:H2"], "volume_ul": 200}]),
            DECK, EMBODIMENTS["i3-dpette8"])
    assert any("manual remount" in b for b in f.blockers)


def test_column_tasks_are_only_deck_bound_on_the_gantry():
    """The finding the docs report: colony PCR is column-wise, so a bigger deck and one range swap make it run."""
    tasks = {t: (p, d) for t, p, d in task_irs()}
    p, d = tasks["colony-pcr-screening"]
    eight = EMBODIMENTS["i3-dpette8"]
    assert all(s.ok for s in fit(p, d, eight).robot_steps)
    assert fit(p, d, replace(eight, max_labware=4, swap_is_manual=False)).runnable


def test_markdown_has_a_row_per_task():
    md = to_markdown(matrix())
    assert md.count("\n| `") == len(list(task_irs()))
