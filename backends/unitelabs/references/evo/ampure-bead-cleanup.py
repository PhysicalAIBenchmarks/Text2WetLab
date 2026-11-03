# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.plates import Standard96Plate
from unitelabs.labware.tecan import EvoTip_MCA_DiTi_200, EvoTipBox_MCA_DiTi_200, MP_3Pos_flat, MP_4Pos_flat
from unitelabs.labware.troughs import StandardTrough


async def run(evo, comment):
    # MCA96: every step moves the same volume in all 96 wells; a fresh 96-tip set per transfer.
    tip_boxes = []
    for carrier_index, track in enumerate((1, 8)):
        tip_carrier = MP_4Pos_flat()
        for site in range(4):
            box = EvoTipBox_MCA_DiTi_200(identifier=f"tips200_{carrier_index * 4 + site + 1}")
            box.fill(EvoTip_MCA_DiTi_200)
            tip_carrier[site] = box
            tip_boxes.append(box)
        evo.deck.add(tip_carrier, track=track)

    trough_carrier = MP_4Pos_flat()
    beads = StandardTrough(identifier="beads_reservoir")
    ethanol = StandardTrough(identifier="ethanol_reservoir")
    water = StandardTrough(identifier="water_reservoir")
    waste = StandardTrough(identifier="waste")
    beads.containers[0].add_liquid(PredefinedLiquids.WATER, 90_000)
    ethanol.containers[0].add_liquid(PredefinedLiquids.ETHANOL, 90_000)
    water.containers[0].add_liquid(PredefinedLiquids.WATER, 90_000)
    trough_carrier[0], trough_carrier[1], trough_carrier[2], trough_carrier[3] = beads, ethanol, water, waste
    evo.deck.add(trough_carrier, track=15)

    plate_carrier = MP_3Pos_flat()
    sample_plate = Standard96Plate(identifier="sample_plate")
    elution_plate = Standard96Plate(identifier="elution_plate")
    for well in sample_plate:
        well.container.add_liquid(PredefinedLiquids.WATER, 50)
    plate_carrier[0], plate_carrier[1] = sample_plate, elution_plate
    evo.deck.add(plate_carrier, track=22)

    tips = iter(tip_boxes)

    async def transfer(source, target, volume, mix_cycles=None, mix_volume=None):
        await evo.mca.pick_up_tips_from(rack=next(tips))
        await evo.mca.aspirate(source=source, volume=volume)
        await evo.mca.dispense(target=target, volume=volume, mix_cycles=mix_cycles, mix_volume=mix_volume)
        await evo.mca.discard_tips()

    await transfer(beads, sample_plate, 40, mix_cycles=10, mix_volume=60)          # 50 + 40 = 90 µL
    comment("Incubate sample_plate 5 min at room temperature (beads bind DNA)")
    comment("Engage magnetic module; wait 5 min until solution clears")
    await transfer(sample_plate, waste, 90)                                        # all supernatant
    for wash in (1, 2):
        await transfer(ethanol, sample_plate, 200)
        await transfer(sample_plate, waste, 200)
    comment("Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny")
    comment("Disengage magnetic module")
    await transfer(water, sample_plate, 50, mix_cycles=10, mix_volume=30)
    comment("Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min")
    await transfer(sample_plate, elution_plate, 45)
