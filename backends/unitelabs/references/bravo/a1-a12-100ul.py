# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.agilent.tips import AgilentTip_250, AgilentTipRack_250
from unitelabs.labware.agilent.troughs import Agilent_DW_Reservoir
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.liquids import PredefinedLiquids


async def run(bravo, comment):
    tips = AgilentTipRack_250("tips250")
    tips.fill(AgilentTip_250)
    reservoir = Agilent_DW_Reservoir("reservoir")
    reservoir.containers[0].add_liquid(PredefinedLiquids.WATER, 10000)
    plate = Cos_96_FB("plate")
    bravo.deck.add(tips, location=7)
    bravo.deck.add(reservoir, location=8)
    bravo.deck.add(plate, location=4)

    # Row A of tips: head row H (A12..H12 nozzles overlap rack row A) -> 12 tips on head row H.
    await bravo.pipette_head.pick_up_tips_from(rack=tips, well_offset=(-7, 0), press_depth=5.8)
    await bravo.pipette_head.aspirate(reservoir, volume=100)
    # The 12 tips sit on head row H; shift by -7 rows so they land in plate row A.
    await bravo.pipette_head.dispense(plate, volume=100, well_offset=(-7, 0))
    await bravo.pipette_head.discard_tips(bravo.deck[5])
