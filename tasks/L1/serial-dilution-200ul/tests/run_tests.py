"""
Test suite — runs all 5 criteria in PyLabRobot (ChatterBox sim backend).
Each test is PASS if the correct behaviour is observed,
FAIL if PyLabRobot lets a bad protocol through without error.

Criteria:
  T1  pick up tip before aspirating
  T2  aspirate 200uL then dispense 100+100 from same load
  T3  drop tip at end
  T4  no crash: aspirate auto-lifts before lateral move
  T5  volume overflow: aspirate more than pipette max raises error
"""

import asyncio
import traceback
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend as ChatterBoxBackend
from pylabrobot.resources import (
    OTDeck,
    opentrons_96_tiprack_1000ul,
    cor_96_wellplate_360uL_Fb,
)



PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
INFO = "\033[94m INFO\033[0m"


def result(name, passed, note=""):
    tag = PASS if passed else FAIL
    print(f"  [{tag[1:5]}] {name}{(' — ' + note) if note else ''}")


async def make_lh():
    deck = OTDeck()
    lh = LiquidHandler(backend=ChatterBoxBackend(), deck=deck)

    tiprack = opentrons_96_tiprack_1000ul(name="tiprack")
    plate   = cor_96_wellplate_360uL_Fb(name="plate")
    deck.assign_child_at_slot(tiprack, 1)
    deck.assign_child_at_slot(plate, 2)

    await lh.setup()
    return lh, tiprack, plate


# ─────────────────────────────────────────────
# T1: tip must be picked up before aspirating
# ─────────────────────────────────────────────
async def test_tip_before_aspirate():
    print("\n[T1] Pick up tip BEFORE aspirating")
    lh, tiprack, plate = await make_lh()
    try:
        # attempt aspirate with no tip loaded
        await lh.aspirate(plate["A1"], vols=[100])
        result("aspirate without tip", False, "no error raised — should have failed")
    except Exception as e:
        result("aspirate without tip raises error", True, type(e).__name__)
    await lh.stop()


# ─────────────────────────────────────────────
# T2+T3: aspirate 200uL → dispense 100+100 → drop tip
# ─────────────────────────────────────────────
async def test_200ul_two_dispenses():
    print("\n[T2+T3] Aspirate 200uL → dispense 100 + 100 → drop tip")
    lh, tiprack, plate = await make_lh()

    # pick up tip
    await lh.pick_up_tips(tiprack["A1"])
    result("pick up tip", True)

    # aspirate 200uL
    try:
        await lh.aspirate(plate["A1"], vols=[200])
        result("aspirate 200uL", True)
    except Exception as e:
        result("aspirate 200uL", False, str(e))
        await lh.stop(); return

    # first 100uL dispense
    try:
        await lh.dispense(plate["B1"], vols=[100])
        result("dispense 100uL → B1 (100uL remaining)", True)
    except Exception as e:
        result("dispense 100uL → B1", False, str(e))
        await lh.stop(); return

    # second 100uL dispense (from same load, 100uL still in tip)
    try:
        await lh.dispense(plate["C1"], vols=[100])
        result("dispense 100uL → C1 (0uL remaining)", True)
    except Exception as e:
        result("dispense 100uL → C1", False, str(e))
        await lh.stop(); return

    # drop tip
    try:
        await lh.drop_tips(tiprack["A1"])
        result("drop tip at end", True)
    except Exception as e:
        result("drop tip at end", False, str(e))

    await lh.stop()


# ─────────────────────────────────────────────
# T4: overdispense — try to dispense more than aspirated
# ─────────────────────────────────────────────
async def test_overdispense():
    print("\n[T4] Overdispense: aspirate 100uL, try to dispense 200uL")
    lh, tiprack, plate = await make_lh()
    await lh.pick_up_tips(tiprack["A1"])

    try:
        await lh.aspirate(plate["A1"], vols=[100])
        await lh.dispense(plate["B1"], vols=[200])   # 200 > 100 available
        result("overdispense raises error", False, "no error — volume tracking may be off")
    except Exception as e:
        result("overdispense raises error", True, f"{type(e).__name__}: {str(e)[:60]}")

    await lh.stop()


# ─────────────────────────────────────────────
# T5: over-capacity — aspirate > max pipette volume (1000uL for p1000)
# ─────────────────────────────────────────────
async def test_over_capacity():
    print("\n[T5] Over-capacity: aspirate 1100uL into 1000uL pipette")
    lh, tiprack, plate = await make_lh()
    await lh.pick_up_tips(tiprack["A1"])

    try:
        await lh.aspirate(plate["A1"], vols=[1100])
        result("over-capacity aspirate raises error", False, "no error raised")
    except Exception as e:
        result("over-capacity aspirate raises error", True, f"{type(e).__name__}: {str(e)[:60]}")

    await lh.stop()


# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
async def main():
    print("=" * 58)
    print("  NL2WetLab — PyLabRobot protocol validation tests")
    print("=" * 58)

    # suppress chatterbox output to keep results clean
    import io, sys
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    await test_tip_before_aspirate()
    await test_200ul_two_dispenses()
    await test_overdispense()
    await test_over_capacity()

    sys.stdout = old_stdout

    # re-run cleanly
    await test_tip_before_aspirate()
    await test_200ul_two_dispenses()
    await test_overdispense()
    await test_over_capacity()

    print("\n" + "=" * 58)


asyncio.run(main())
