from unitelabs.labware.azenta import AzentaFluidXTube_1900uL_ExternalThread
from unitelabs.labware.biomek import BiomekTip_50, BiomekTip_1070, BiomekTipRack_50, BiomekTipRack_1070
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.troughs import StandardTrough
from unitelabs.labware.tubes import Standard96TubeRack


async def run(biomek, comment):
    head = biomek.pipette_head
    tips50 = BiomekTipRack_50("tips50", filled_with=BiomekTip_50)
    tips1070 = BiomekTipRack_1070("tips1070", filled_with=BiomekTip_1070)
    biomek.deck.add(tips50, location="TL1")
    biomek.deck.add(tips1070, location="TL2")
    plasmid_plate = Cos_96_FB("plasmid_plate")
    plasmid_plate["A1"].container.add_liquid(PredefinedLiquids.WATER, 100)
    biomek.deck.add(plasmid_plate, location="P1")
    # A tube rack on the 9 mm grid with the competent cells in A1, so nozzle A1 addresses it directly.
    rack = Standard96TubeRack("tubes_1_5ml_1", filled_with=AzentaFluidXTube_1900uL_ExternalThread, filled_at=["A1"])
    rack["A1"].get().container.add_liquid(PredefinedLiquids.WATER, 50)
    biomek.deck.add(rack, location="P2")
    soc = StandardTrough("soc_reservoir")
    soc.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    biomek.deck.add(soc, location="P3")

    # Single tips: nozzle A1 over the rack's H12 spot, the rest of the head overhanging empty space.
    await head.pick_up_tips(channels=[0], spots=[tips50["H12"]])
    await head.aspirate(plasmid_plate, volumes=2)
    await head.dispense(rack, volumes=2)
    await head.discard_tips("TR1")
    comment("Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min")
    await head.pick_up_tips(channels=[0], spots=[tips1070["H12"]])
    await head.aspirate(soc, volumes=250)
    await head.dispense(rack, volumes=250)
    await head.discard_tips("TR1")
    comment("Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery")
