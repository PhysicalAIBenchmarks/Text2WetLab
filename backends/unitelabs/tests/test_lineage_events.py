"""lineage_events.py: the SDK's lineage stream as run-log events, replayed from pinned runs without the SDK
(tests/fixtures/lineage, written by ul/lineage_fixtures.py), and the cases the references don't reach."""
import json
import pathlib

import check
import lineage_events
import pytest
import spec_check

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures/lineage").glob("*__*.json"))
ENTITIES = {"plate:A1": ["plate on 7.0", "A1"], "src:A1": ["src on 15.0", "A1"], "water": ["water on 13.2", "A1"]}


def ch(n, module="pipettes"):
    return f"channel:star:{module}:{n}"


def lineage(operation, source, target, type_="lineage", **extras):
    return {"type": type_, "operation": operation, "inputs": {"entity_id": source} if source else {},
            "outputs": {"entity_id": target} if target else {}, "extras": extras}


def test_fixtures_exist():
    assert len(FIXTURES) >= 15


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_pinned_runs_replay(path):
    f = json.loads(path.read_text())
    events, errors = lineage_events.to_events(f["lineage"], f["entities"], [tuple(c) for c in f["comments"]])
    assert events == f["events"] and errors == []


def test_a_transfer():
    stream = [lineage("pick_up_tip", "tips:A1", ch(2), channel=2, tip="t1"),
              lineage("aspirate", "src:A1", ch(2), channel=2, volume_ul=50.0, volume_requested_ul=50.0, tip="t1"),
              lineage("dispense", ch(2), "plate:A1", channel=2, volume_ul=50.0, volume_requested_ul=50.0, tip="t1"),
              lineage("discard_tip", ch(2), "waste", channel=2, tip="t1", origin_slot="tips:A1")]
    events, errors = lineage_events.to_events(stream, ENTITIES)
    assert errors == []
    assert events == [
        {"kind": "pick", "instrument": "channel_2", "channels": 1, "tip": "t1"},
        {"kind": "aspirate", "instrument": "channel_2", "channels": 1, "volume": 50.0, "moved": 50.0, "well": "A1",
         "labware": "src on 15.0"},
        {"kind": "dispense", "instrument": "channel_2", "channels": 1, "volume": 50.0, "moved": 50.0, "well": "A1",
         "labware": "plate on 7.0"},
        {"kind": "drop", "instrument": "channel_2", "channels": 1, "tip": "t1"}]


def test_volume_is_the_request_and_moved_what_moved():
    over = lineage("aspirate", "src:A1", ch(0), channel=0, volume_ul=80.0, volume_requested_ul=100.0)
    [e], _ = lineage_events.to_events([over], ENTITIES)
    assert (e["volume"], e["moved"]) == (100.0, 80.0)          # an over-aspiration stays visible to the checks


def test_no_request_means_what_moved():
    default = lineage("dispense", ch(0), "plate:A1", channel=0, volume_ul=30.0)
    [e], _ = lineage_events.to_events([default], ENTITIES)
    assert (e["volume"], e["moved"]) == (30.0, 30.0)


def test_put_down_is_a_drop_and_tubes_are_their_own_entity():
    stream = [lineage("put_down_tip", ch(0, "pipette_head"), "tips:A1", channel=0, tip="t1"),
              lineage("aspirate", "water", ch(0, "pipette_head"), channel=0, volume_ul=5.0)]
    events, _ = lineage_events.to_events(stream, ENTITIES)
    assert events[0] == {"kind": "drop", "instrument": "nozzle_0", "channels": 1, "tip": "t1"}
    assert (events[1]["labware"], events[1]["well"]) == ("water on 13.2", "A1")


def test_mix():
    stream = [lineage("pick_up_tip", "tips:A1", ch(3), channel=3, tip="t1"),
              lineage("mix_in_place", "plate:A1", "plate:A1", channel=3, volume_ul=40.0, cycles=10, tip="t1")]
    [_, e], _ = lineage_events.to_events(stream, ENTITIES)
    assert e == {"kind": "mix", "instrument": "channel_3", "channels": 1, "cycles": 10, "volume": 40.0, "well": "A1",
                 "labware": "plate on 7.0"}


def test_a_mix_is_on_the_instrument_holding_its_tip():
    stream = [lineage("pick_up_tip", "tips:A1", ch(5, "pipette_head"), channel=5, tip="t1"),
              lineage("mix_in_place", "plate:A1", "plate:A1", channel=5, volume_ul=10.0, cycles=2, tip="t1")]
    events, _ = lineage_events.to_events(stream, ENTITIES)
    assert events[1]["instrument"] == "nozzle_5"


def test_a_mix_with_a_tip_no_channel_picked_up_is_refused():
    with pytest.raises(ValueError, match="no channel picked up"):
        lineage_events.to_events([lineage("mix_in_place", "plate:A1", "plate:A1", channel=0, volume_ul=10.0,
                                          cycles=2, tip="t9")], ENTITIES)


@pytest.mark.parametrize("entity", ["channel:0", "channel:star:0", "channel:star:pipettes:x", "plate:A1"])
def test_only_scoped_channel_ids_are_channels(entity):
    with pytest.raises(ValueError, match="not a channel"):
        lineage_events.to_events([lineage("pick_up_tip", "tips:A1", entity, channel=0, tip="t1")], ENTITIES)


def test_loads_seeds_and_audits_are_not_run_log_events():
    stream = [lineage("load_labware", None, "car:0", labware="plate"),
              lineage("seed_container", None, "plate:A1", volume_ul=100.0, mixture={"water": 100.0}),
              lineage("seed_container", None, "plate:A1", "audit", reason="liquid_removed", volume_ul=60.0,
                      volume_before_ul=100.0, removed_ul=40.0),
              lineage("unload_labware", "car:0", None, labware="plate")]
    assert lineage_events.to_events(stream, ENTITIES) == ([], [])


def test_errors_are_kept_apart():
    failed = lineage("aspirate", "src:A1", ch(1), "error", channel=1, error="TipError")
    events, errors = lineage_events.to_events([failed], ENTITIES)
    assert events == [] and errors == [failed]


def test_comments_land_in_order():
    stream = [lineage("pick_up_tip", "tips:A1", ch(0), channel=0, tip="t1"),
              lineage("discard_tip", ch(0), "waste", channel=0, tip="t1", origin_slot="tips:A1")]
    events, _ = lineage_events.to_events(stream, ENTITIES, comments=[(0, "first"), (1, "between"), (2, "last")])
    assert [e["kind"] for e in events] == ["comment", "pick", "comment", "drop", "comment"]
    assert [e["text"] for e in events if e["kind"] == "comment"] == ["first", "between", "last"]


def test_other_operations_are_not_run_log_events():
    move = lineage("move_labware", "car:0", "car:1", labware="plate")
    assert lineage_events.to_events([move], ENTITIES) == ([], [])


def test_a_well_off_the_deck_is_refused():
    with pytest.raises(ValueError, match="not a well"):
        lineage_events.to_events([lineage("aspirate", "ghost:A1", ch(0), channel=0, volume_ul=1.0)], ENTITIES)


def test_mix_reaches_the_checks_as_one_pair():
    mix = {"kind": "mix", "instrument": "channel_0", "channels": 1, "cycles": 10, "volume": 40.0, "well": "A1",
           "labware": "plate on 7.0"}
    pair = check.mix_as_pair([mix])
    assert [e["kind"] for e in pair] == ["aspirate", "dispense"]
    assert all(e["volume"] == 40.0 and e["moved"] == 0.0 and e["labware"] == "plate on 7.0" for e in pair)


def test_mixing_more_than_the_well_holds_is_aspirating_from_empty():
    events = check.mix_as_pair([{"kind": "pick", "instrument": "channel_0", "channels": 1},
                                {"kind": "mix", "instrument": "channel_0", "channels": 1, "cycles": 3, "volume": 50.0,
                                 "well": "A1", "labware": "plate on 7.0"}])
    st = spec_check.replay(events, initial={("plate on 7.0", "A1"): 20.0})
    assert [name for _, name in st.errors] == ["aspirate_from_empty"]
