# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.biomek import Biomek_MC96_Water, BiomekTip_50, BiomekTipRack_50
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.plates import Standard96Plate
from unitelabs.labware.troughs import StandardTrough


async def run(biomek, comment):
    head = biomek.pipette_head
    racks = []
    for index, position in enumerate(["TL1", "TL2", "TL3"]):
        rack = BiomekTipRack_50(f"tips50_{index + 1}", filled_with=BiomekTip_50)
        biomek.deck.add(rack, location=position)
        racks.append(rack)

    colony_plate, primer_plate, pcr_plate = (
        Standard96Plate("colony_plate"), Standard96Plate("primer_plate"), Standard96Plate("pcr_plate"),
    )
    for plate in (colony_plate, primer_plate):
        for well in plate:
            well.container.add_liquid(PredefinedLiquids.WATER, 100)
    biomek.deck.add(colony_plate, location="P1")
    biomek.deck.add(primer_plate, location="P2")
    biomek.deck.add(pcr_plate, location="P3")
    master_mix = StandardTrough("master_mix_reservoir")
    master_mix.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    biomek.deck.add(master_mix, location="P4")

    # 96-channel head: each step is one stroke over the whole plate with a fresh rack of 50 µL tips.
    await head.pick_up_tips_from(rack=racks[0])
    await head.aspirate(master_mix, volumes=18)
    await head.dispense(pcr_plate, volumes=18)
    await head.discard_tips("TR1")

    await head.pick_up_tips_from(rack=racks[1])
    await head.aspirate(colony_plate, volumes=1)
    await head.dispense(pcr_plate, volumes=1, mix_cycles=3, mix_volume=10,
                        liquid_class=Biomek_MC96_Water())   # mixing needs an explicit liquid class
    await head.discard_tips("TR1")

    await head.pick_up_tips_from(rack=racks[2])
    await head.aspirate(primer_plate, volumes=1)
    await head.dispense(pcr_plate, volumes=1)
    await head.discard_tips("TR1")

    comment("Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C")
