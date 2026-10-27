# T2WL-CANARY-7f3c9e1a4b
# APEX Protocol 1: low-volume heat shock transformation (Kasprzyk et al., bioRxiv 2024, doi:10.1101/2024.08.13.607171)
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, RGT_CAR_3R_A00, RGT_CONT_100ml, TIP_CAR_480_A00,
    HamiltonTip_10, HamiltonTip_300, HamiltonTipRack_10, HamiltonTipRack_300,
)
from unitelabs.labware.liquids import PredefinedLiquids


async def run(star, comment):
    tips = TIP_CAR_480_A00()
    tips[0] = HamiltonTipRack_10("tips10", filled_with=HamiltonTip_10)
    tips[1] = HamiltonTipRack_300("tips300", filled_with=HamiltonTip_300)
    star.deck.add(tips, track=1)
    plates = PLT_CAR_L5MD_A00()
    plasmids = plates[0] = Cos_96_FB("plasmid_plate")
    cells = plates[1] = Cos_96_FB("transformation_plate")
    star.deck.add(plates, track=7)
    troughs = RGT_CAR_3R_A00()
    soc = troughs[0] = RGT_CONT_100ml("soc_reservoir")
    soc.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    star.deck.add(troughs, track=13)
    for row in "ABCDEFGH":
        plasmids[f"{row}1"].container.add_liquid(PredefinedLiquids.WATER, 10)
        cells[f"{row}1"].container.add_liquid(PredefinedLiquids.WATER, 10)
    channels = list(range(8))

    comment("Keep transformation_plate at 4 °C (cold block or thermocycler, lid open) while pipetting.")
    # Low-volume configuration: 1 uL DNA into 10 uL cells, a fresh tip per plasmid (eight channels, one column).
    await star.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_10)
    await star.pipettes.aspirate(plasmids["A1":"H1"], channels=channels, volume=1)
    await star.pipettes.dispense(cells["A1":"H1"], channels=channels, volume=1)
    await star.pipettes.discard_tips(channels=channels)
    comment("Thermocycler, lid closed: 4 °C 30 min with the DNA, heat shock at 42 °C for 30 s, back to 4 °C for 2 min.")
    # Recovery: 50 uL SOC per transformation, fresh tips.
    await star.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_300)
    await star.pipettes.aspirate(soc, channels=channels, volume=50)
    await star.pipettes.dispense(cells["A1":"H1"], channels=channels, volume=50)
    await star.pipettes.discard_tips(channels=channels)
    comment("Thermocycler: recover at 37 °C for 1 h, then hold at 4 °C. Spot the transformations on selective agar.")
