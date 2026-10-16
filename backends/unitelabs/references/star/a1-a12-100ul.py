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

    # All eight channels draw from the trough at once; they share one X arm, so row A is then filled one channel per
    # column. Two rounds (8 + 4 columns), each tip only ever in the trough and its own well.
    channels = list(range(8))
    await star.pipettes.pick_up_tips(channels=channels, spots=tips["A1":"H1"])
    for first in (1, 9):
        used = channels[:min(8, 13 - first)]
        await star.pipettes.aspirate(reservoir, channels=used, volume=100)
        for channel in used:
            await star.pipettes.dispense(plate[f"A{first + channel}"], channels=[channel], volume=100)
    await star.pipettes.discard_tips(channels=channels)
