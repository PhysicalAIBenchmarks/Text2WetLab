from paper2protocol.check import check, expand_wells
from paper2protocol.models import Container, Content, Protocol, Step


def step(kind="transfer", source=None, sw=(), dest=None, dw=(), vol=None, action=""):
    return Step(kind=kind, source=source, source_wells=list(sw), dest=dest, dest_wells=list(dw),
                volume_ul=vol, reagent="", mix_cycles=None, action=action, source_quote="",
                assumed=False, note="")


def proto(steps, contents=()):
    return Protocol(
        title="t",
        containers=[Container(name="tube", kind="tube_1.5ml", description="", assumed=False),
                    Container(name="plate", kind="plate_96", description="", assumed=False)],
        initial_contents=list(contents), steps=steps, assumptions=[])


def tube(vol):
    return Content(container="tube", wells=[], reagent="x", volume_ul=vol, assumed=False)


def test_expand_wells():
    assert expand_wells(["A1:B2"], "plate_96") == ["A1", "A2", "B1", "B2"]
    assert expand_wells([], "tube_1.5ml") == [""]


def test_clean_protocol_has_no_issues():
    p = proto([step(source="tube", dest="plate", dw=["A1:A2"], vol=100)], [tube(200)])
    assert check(p) == []


def test_overdraw_is_flagged():
    # 100 µL into 3 wells = 300 µL from a 200 µL tube
    p = proto([step(source="tube", dest="plate", dw=["A1:A3"], vol=100)], [tube(200)])
    assert [i.message for i in check(p)] == ["withdraws more than tube holds (short by 100 µL)"]


def test_over_capacity_is_flagged():
    p = proto([step(source="tube", dest="plate", dw=["A1"], vol=400)], [tube(None)])
    assert "capacity" in check(p)[0].message


def test_unfilled_source_is_flagged():
    p = proto([step(source="tube", dest="plate", dw=["A1"], vol=10)])
    assert "before anything was put there" in check(p)[0].message


def test_stock_is_unlimited_and_bad_well_flagged():
    p = proto([step(source="tube", dest="plate", dw=["Z9"], vol=10)], [tube(None)])
    assert "bad 96-well position" in check(p)[0].message
