# APEX Protocol 1: low-volume heat shock transformation (Kasprzyk et al., bioRxiv 2024, doi:10.1101/2024.08.13.607171)
from unitelabs.labware.agilent.tips import AgilentTip_200, AgilentTip_250, AgilentTipRack_200, AgilentTipRack_250
from unitelabs.labware.agilent.troughs import Agilent_DW_Reservoir
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.liquids import PredefinedLiquids

# The 96-channel LT head takes only LT200/LT250 tips (the 10-70 µL racks are 384-format, for the ST head), so 1 µL
# goes with LT200 tips, as in the colony PCR. One column of tips: at offset (0, 11) only nozzle column 1 overlaps a
# rack column (12), so eight nozzles take tips; at no offset they are over plate column 1 and the other 88 are empty.
COLUMN = (0, 11)


async def run(bravo, comment):
    head = bravo.pipette_head
    tips200 = AgilentTipRack_200("tips200")
    tips200.fill(AgilentTip_200)
    tips250 = AgilentTipRack_250("tips250")
    tips250.fill(AgilentTip_250)
    plasmids = Cos_96_FB("plasmid_plate")
    cells = Cos_96_FB("transformation_plate")
    for row in "ABCDEFGH":
        plasmids[f"{row}1"].container.add_liquid(PredefinedLiquids.WATER, 10)
        cells[f"{row}1"].container.add_liquid(PredefinedLiquids.WATER, 10)
    soc = Agilent_DW_Reservoir("soc_reservoir")
    soc.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    bravo.deck.add(tips200, location=1)
    bravo.deck.add(tips250, location=4)
    bravo.deck.add(plasmids, location=2)
    bravo.deck.add(cells, location=3)
    bravo.deck.add(soc, location=5)

    comment("Keep transformation_plate at 4 °C (cold block or thermocycler, lid open) while pipetting.")
    # Low-volume configuration: 1 uL DNA into 10 uL cells, a fresh tip per plasmid; used tips go back to their rack.
    await head.pick_up_tips_from(rack=tips200, well_offset=COLUMN, press_depth=5.8)
    await head.aspirate(plasmids, volume=1)
    await head.dispense(cells, volume=1)
    await head.put_down_tips_to(rack=tips200, well_offset=COLUMN)
    comment("Thermocycler, lid closed: 4 °C 30 min with the DNA, heat shock at 42 °C for 30 s, back to 4 °C for 2 min.")
    # Recovery: 50 uL SOC per transformation, fresh tips.
    await head.pick_up_tips_from(rack=tips250, well_offset=COLUMN, press_depth=5.8)
    await head.aspirate(soc, volume=50)
    await head.dispense(cells, volume=50)
    await head.put_down_tips_to(rack=tips250, well_offset=COLUMN)
    comment("Thermocycler: recover at 37 °C for 1 h, then hold at 4 °C. Spot the transformations on selective agar.")
