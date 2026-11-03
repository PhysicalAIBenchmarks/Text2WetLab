# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.biomek import Biomek_MC96_Water, BiomekTip_230, BiomekTipRack_230
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.plates import Standard96Plate
from unitelabs.labware.troughs import StandardTrough

# Six tip-loader positions plus two static plate positions: one full rack of 230 µL tips per step.
TIP_POSITIONS = ["TL1", "TL2", "TL3", "TL4", "TL5", "TL6", "P7", "P8"]


async def run(biomek, comment):
    head = biomek.pipette_head
    racks = []
    for index, position in enumerate(TIP_POSITIONS):
        rack = BiomekTipRack_230(f"tips230_{index + 1}", filled_with=BiomekTip_230)
        biomek.deck.add(rack, location=position)
        racks.append(rack)

    sample_plate = Standard96Plate("sample_plate")
    for well in sample_plate:
        well.container.add_liquid(PredefinedLiquids.WATER, 50)
    biomek.deck.add(sample_plate, location="P1")
    elution_plate = Standard96Plate("elution_plate")
    biomek.deck.add(elution_plate, location="P2")
    troughs = {}
    for position, name in (("P3", "beads_reservoir"), ("P4", "ethanol_reservoir"), ("P5", "water_reservoir")):
        trough = StandardTrough(name)
        trough.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
        biomek.deck.add(trough, location=position)
        troughs[name] = trough
    waste = StandardTrough("waste")
    biomek.deck.add(waste, location="P6")

    async def transfer(source, dest, volume, mix_cycles=None):
        """Whole plate in one stroke with a fresh full rack of 96 tips."""
        await head.pick_up_tips_from(rack=racks.pop(0))
        await head.aspirate(source, volumes=volume)
        if mix_cycles:
            await head.dispense(dest, volumes=volume, mix_cycles=mix_cycles, mix_volume=volume,
                               liquid_class=Biomek_MC96_Water())   # mixing needs an explicit liquid class
        else:
            await head.dispense(dest, volumes=volume)
        await head.discard_tips("TR1")

    await transfer(troughs["beads_reservoir"], sample_plate, 40, mix_cycles=10)
    comment("Incubate sample_plate 5 min at room temperature (beads bind DNA)")
    comment("Engage magnetic module; wait 5 min until solution clears")
    await transfer(sample_plate, waste, 90)
    for _ in range(2):
        await transfer(troughs["ethanol_reservoir"], sample_plate, 200)
        await transfer(sample_plate, waste, 200)
    comment("Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny")
    comment("Disengage magnetic module")
    await transfer(troughs["water_reservoir"], sample_plate, 50, mix_cycles=10)
    comment("Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min")
    await transfer(sample_plate, elution_plate, 45)
