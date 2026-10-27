# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.liquids import PredefinedLiquids
from unitelabs.labware.plates import Standard96Plate
from unitelabs.labware.tecan import EvoTip_MCA_DiTi_50, EvoTipBox_MCA_DiTi_50, MP_3Pos_flat, MP_4Pos_flat
from unitelabs.labware.troughs import StandardTrough


async def run(evo, comment):
    # MCA96: every step moves the same volume in all 96 wells, so each step is one head operation.
    tip_carrier = MP_3Pos_flat()
    tip_boxes = []
    for site in range(3):
        box = EvoTipBox_MCA_DiTi_50(identifier=f"tips50_{site + 1}")
        box.fill(EvoTip_MCA_DiTi_50)
        tip_carrier[site] = box
        tip_boxes.append(box)
    evo.deck.add(tip_carrier, track=1)

    plate_carrier = MP_4Pos_flat()
    colony_plate = Standard96Plate(identifier="colony_plate")
    primer_plate = Standard96Plate(identifier="primer_plate")
    pcr_plate = Standard96Plate(identifier="pcr_plate")
    master_mix = StandardTrough(identifier="master_mix_reservoir")
    master_mix.containers[0].add_liquid(PredefinedLiquids.WATER, 90_000)
    for plate in (colony_plate, primer_plate):
        for well in plate:
            well.container.add_liquid(PredefinedLiquids.WATER, 100)
    plate_carrier[0], plate_carrier[1], plate_carrier[2], plate_carrier[3] = (
        master_mix, colony_plate, primer_plate, pcr_plate)
    evo.deck.add(plate_carrier, track=8)

    # 1. 18 µL master mix into every well (one tip set, into empty wells).
    await evo.mca.pick_up_tips_from(rack=tip_boxes[0])
    await evo.mca.aspirate(source=master_mix, volume=18)
    await evo.mca.dispense(target=pcr_plate, volume=18)
    await evo.mca.discard_tips()

    # 2. 1 µL colony template, plate-to-plate, mix 3x; fresh tips.
    await evo.mca.pick_up_tips_from(rack=tip_boxes[1])
    await evo.mca.aspirate(source=colony_plate, volume=1)
    await evo.mca.dispense(target=pcr_plate, volume=1, mix_cycles=3, mix_volume=10)
    await evo.mca.discard_tips()

    # 3. 1 µL primer mix, plate-to-plate; fresh tips.
    await evo.mca.pick_up_tips_from(rack=tip_boxes[2])
    await evo.mca.aspirate(source=primer_plate, volume=1)
    await evo.mca.dispense(target=pcr_plate, volume=1)
    await evo.mca.discard_tips()

    comment("Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C")
