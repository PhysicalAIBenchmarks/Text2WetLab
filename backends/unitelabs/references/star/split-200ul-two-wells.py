# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, RGT_CAR_3R_A00, RGT_CONT_100ml, TIP_CAR_480_A00, HamiltonTip_300, HamiltonTipRack_300,
)
from unitelabs.labware.liquids import PredefinedLiquids


async def run(star, comment):
    tip_carrier = TIP_CAR_480_A00()
    tips = HamiltonTipRack_300("tips300", filled_with=HamiltonTip_300)
    tip_carrier[0] = tips
    star.deck.add(tip_carrier, track=1)
    plate_carrier = PLT_CAR_L5MD_A00()
    plate = Cos_96_FB("plate")
    plate_carrier[0] = plate
    star.deck.add(plate_carrier, track=7)
    trough_carrier = RGT_CAR_3R_A00()
    reservoir = RGT_CONT_100ml("reservoir")
    reservoir.containers[0].add_liquid(PredefinedLiquids.WATER, 10000)
    trough_carrier[0] = reservoir
    star.deck.add(trough_carrier, track=13)

    await star.pipettes.pick_up_tips(channels=[0, 1], spots=tips["A1":"B1"])
    await star.pipettes.aspirate(reservoir, channels=[0, 1], volume=100)
    await star.pipettes.dispense([plate["A1"], plate["B1"]], channels=[0, 1], volume=100)
    await star.pipettes.discard_tips(channels=[0, 1])
