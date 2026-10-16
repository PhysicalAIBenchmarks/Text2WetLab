# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.biomek import BiomekTip_230, BiomekTipRack_230
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.plates import Standard96Plate
from unitelabs.labware.troughs import StandardTrough


async def run(biomek, comment):
    tips = BiomekTipRack_230("tips230", filled_with=BiomekTip_230)
    biomek.deck.add(tips, location="TL1")
    reservoir = StandardTrough("reservoir")
    reservoir.containers[0].add_liquid(PredefinedLiquids.WATER, 10000)
    biomek.deck.add(reservoir, location="P1")
    plate = Standard96Plate("plate")
    biomek.deck.add(plate, location="P2")

    # Head offset (6, 11): head nozzles A1 and B1 sit over rack G12 and H12; only those two get tips.
    await biomek.pipette_head.pick_up_tips_from(rack=tips, well_offset=(6, 11))
    await biomek.pipette_head.aspirate(reservoir, volumes=100)
    await biomek.pipette_head.dispense(plate, volumes=100)      # nozzles A1, B1 -> wells A1, B1
    await biomek.pipette_head.discard_tips("TR1")
