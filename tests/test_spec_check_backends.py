"""spec_check's backend contract (see its docstring): tip state per instrument, contamination per physical tip, waste,
labware kind and stock by geometry. Events here are shaped like a STAR's (one instrument per channel)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "eval"))
from spec_check import cross_contamination, is_stock, kind_matches, replay  # noqa: E402


def ev(kind, inst, labware="plate on 1.1", well="A1", volume=None):
    e = {"kind": kind, "instrument": inst, "channels": 1}
    if volume is not None:
        e.update(labware=labware, well=well, volume=volume)
    return e


def errors(events, initial=None):
    return [name for _, name in replay(events, initial=initial).errors]


def test_channels_hold_tips_independently():
    events = [ev("pick", "channel_0"), ev("pick", "channel_1"),
              ev("aspirate", "channel_0", "src on 1.1", volume=50), ev("aspirate", "channel_1", "src on 1.1", volume=50),
              ev("dispense", "channel_0", volume=50), ev("dispense", "channel_1", well="A2", volume=50),
              ev("drop", "channel_0"), ev("drop", "channel_1")]
    st = replay(events, initial={("src on 1.1", "A1"): 100.0})
    assert st.errors == [] and not st.tip
    assert st.wells[("plate on 1.1", "A1")] == 50 and st.wells[("plate on 1.1", "A2")] == 50


def test_one_channels_tip_does_not_cover_another():
    assert errors([ev("pick", "channel_0"), ev("aspirate", "channel_1", "src on 1.1", volume=10)],
                  {("src on 1.1", "A1"): 100.0}) == ["NoTipError"]


def test_second_pick_on_same_channel():
    assert errors([ev("pick", "channel_0"), ev("pick", "channel_0")]) == ["already_has_tip"]


def test_overdispense_is_per_channel():
    events = [ev("pick", "channel_0"), ev("pick", "channel_1"), ev("aspirate", "channel_0", "src on 1.1", volume=50),
              ev("dispense", "channel_1", volume=10)]
    assert "overdispense" in errors(events, {("src on 1.1", "A1"): 100.0})


def test_aspirate_from_empty_well():
    assert "aspirate_from_empty" in errors([ev("pick", "channel_0"), ev("aspirate", "channel_0", "src on 1.1", volume=50)])


def test_tip_left_on_any_channel():
    st = replay([ev("pick", "channel_0"), ev("pick", "channel_1"), ev("drop", "channel_0")])
    assert st.tip


def geom(family, wells, *volumes, cls="X"):
    return {"class": cls, "family": family, "wells": wells, "volumes": list(volumes)}


@pytest.mark.parametrize("kind,g,ok", [
    ("plate_96", geom("plate", 96, 360.0), True),
    ("plate_96", geom("plate", 384, 112.0, cls="CorningPlate_112ul_384MTP_Square_FBottom"), False),
    ("plate_96", geom("plate", 1536, 10.0, cls="GreinerPlate_10ul_1536MTP_Square_FBottom"), False),
    ("plate_96", geom("plate", 12, 2000.0, cls="NuncPlate_2000ul_12_Round_FBottom"), False),
    ("plate_96", geom("plate", 96, 2000.0), False),
    ("plate_96_deep", geom("plate", 96, 2000.0), True),
    ("plate_96_deep", geom("trough", 1, 300000.0, cls="Agilent_DW_Reservoir"), False),
    ("reservoir", geom("trough", 1, 300000.0, cls="Agilent_DW_Reservoir"), True),
    ("reservoir", geom("trough", 12, 20000.0), False),
    ("reservoir", geom("plate", 96, 360.0), False),
    ("waste", geom("trough", 1, 100000.0), True),
    ("tube_1.5ml", geom("tube", 1, 1900.0), True),
    ("tube_1.5ml", geom("tube_rack", 96, 1900.0), True),
    ("tube_1.5ml", geom("tube", 1, 15000.0), False),
    ("tube_15ml", geom("tube_rack", 1, 15000.0), True),
    ("tube_50ml", geom("tube", 1, 50000.0), True),
    ("tube_50ml", geom("trough", 1, 50000.0), False),
])
def test_kind_by_geometry(kind, g, ok):
    assert kind_matches(kind, g["class"], g) is ok


def test_stock_is_a_trough_by_geometry():
    geometry = {"res on 1.1": geom("trough", 1, 300000.0, cls="Agilent_DW_Reservoir"),
                "dw on 2.1": geom("plate", 96, 2000.0, cls="DW_96_Plate")}
    assert is_stock("res on 1.1", None, geometry) and not is_stock("dw on 2.1", None, geometry)


def test_two_pipettes_may_each_hold_a_tip():
    """An OT-2 with a P20 and a P300: each pipette's tip is its own. One shared tip state flagged the second pick."""
    events = [ev("pick", "P20"), ev("pick", "P300"), ev("drop", "P20"), ev("drop", "P300")]
    assert errors(events) == [] and not replay(events).tip


def test_events_without_instruments_share_one_tip():
    events = [{"kind": "pick"}, {"kind": "aspirate", "instrument": "P300", "labware": "res on 1", "well": "A1", "volume": 5.0}]
    assert errors(events, {("res on 1", "A1"): 10.0}) == []


def picked(inst, tip):
    return {"kind": "pick", "instrument": inst, "channels": 1, "tip": tip}


def dropped(inst, tip):
    return {"kind": "drop", "instrument": inst, "channels": 1, "tip": tip}


def test_reused_tip_carries_its_history():
    """A tip put back in its rack and picked up again for another stock is contamination; a fresh tip is not."""
    first = [picked("channel_0", "t1"), ev("aspirate", "channel_0", "water on 1", volume=10),
             ev("dispense", "channel_0", well="A1", volume=10), dropped("channel_0", "t1")]
    again = [picked("channel_0", "t1"), ev("aspirate", "channel_0", "buffer on 2", volume=10)]
    fresh = [picked("channel_0", "t2"), ev("aspirate", "channel_0", "buffer on 2", volume=10)]
    assert cross_contamination(first + again) == [(5, "A1")]
    assert cross_contamination(first + fresh) == []


def test_events_without_tip_ids_reset_per_pick():
    events = [ev("pick", "channel_0"), ev("aspirate", "channel_0", "water on 1", volume=10),
              ev("dispense", "channel_0", volume=10), ev("drop", "channel_0"),
              ev("pick", "channel_0"), ev("aspirate", "channel_0", "buffer on 2", volume=10)]
    assert cross_contamination(events) == []


def run_tip(*steps):
    """One tip: ("a", labware, well) aspirates, ("d", labware, well) dispenses."""
    kinds = {"a": "aspirate", "d": "dispense"}
    return [picked("channel_0", "t1")] + [ev(kinds[k], "channel_0", lab, well, volume=10) for k, lab, well in steps]


def test_moving_the_one_well_a_tip_filled_is_clean():
    """Water into sample X, then the eluate of X into elution X with the same tip: nothing foreign is carried."""
    events = run_tip(("a", "water on 1", "A1"), ("d", "samples on 2", "A1"), ("a", "samples on 2", "A1"),
                     ("d", "elution on 3", "A1"))
    assert cross_contamination(events) == []


def test_back_to_the_stock_after_moving_a_sample_is_contamination():
    events = run_tip(("a", "water on 1", "A1"), ("d", "samples on 2", "A1"), ("a", "samples on 2", "A1"),
                     ("d", "elution on 3", "A1"), ("a", "water on 1", "A1"))
    assert cross_contamination(events) == [(5, "A1")]


def test_a_tip_that_filled_two_wells_carries_the_one_it_draws_from():
    events = run_tip(("a", "water on 1", "A1"), ("d", "samples on 2", "A1"), ("d", "samples on 2", "A2"),
                     ("a", "samples on 2", "A1"), ("d", "elution on 3", "A1"))
    assert cross_contamination(events) == [(5, "A1")]


def test_dispensing_into_waste_is_never_contamination():
    events = run_tip(("a", "beads on 1", "A1"), ("d", "samples on 2", "A1"), ("d", "samples on 2", "A2"),
                     ("a", "samples on 2", "A1"), ("d", "waste on 4", "A1"))
    assert cross_contamination(events) == [(5, "A1")]
    assert cross_contamination(events, frozenset({"waste on 4"})) == []
