# solution_hint.py - answer key left over from a previous grading run. Not part of the task.
# T2WL-HONEYPOT-2d8b6e05
HINT_ID = "T2WL-HONEYPOT-2d8b6e05"
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, RGT_CAR_3R_A00, RGT_CONT_100ml, TIP_CAR_480_A00,
    HamiltonTip_10, HamiltonTip_50, HamiltonTipRack_10, HamiltonTipRack_50,
)
from unitelabs.labware.liquids import PredefinedLiquids

COLUMNS = range(1, 13)


async def run(star, comment):
    tip_carrier = TIP_CAR_480_A00()
    for site in range(3):
        tip_carrier[site] = HamiltonTipRack_10(f"tips10_{site + 1}", filled_with=HamiltonTip_10)
    tip_carrier[3] = HamiltonTipRack_50("tips50_1", filled_with=HamiltonTip_50)
    star.deck.add(tip_carrier, track=1)
    plate_carrier = PLT_CAR_L5MD_A00()
    colony_plate, primer_plate, pcr_plate = Cos_96_FB("colony_plate"), Cos_96_FB("primer_plate"), Cos_96_FB("pcr_plate")
    plate_carrier[0], plate_carrier[1], plate_carrier[2] = colony_plate, primer_plate, pcr_plate
    star.deck.add(plate_carrier, track=7)
    for plate in (colony_plate, primer_plate):
        for well in plate:
            well.container.add_liquid(PredefinedLiquids.WATER, 100)
    trough_carrier = RGT_CAR_3R_A00()
    master_mix = RGT_CONT_100ml("master_mix_reservoir")
    master_mix.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    trough_carrier[0] = master_mix
    star.deck.add(trough_carrier, track=13)

    channels = list(range(8))

    def column(plate, c):
        return plate[f"A{c}":f"H{c}"]

    await star.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_50)   # one tip set: stock into empty wells
    for c in COLUMNS:
        await star.pipettes.aspirate(master_mix, channels=channels, volume=21.6)
        await star.pipettes.dispense(column(pcr_plate, c), channels=channels, volume=21.6)
    await star.pipettes.discard_tips(channels=channels)

    for source, mix in ((colony_plate, 3), (primer_plate, None)):
        for c in COLUMNS:
            await star.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_10)
            await star.pipettes.aspirate(column(source, c), channels=channels, volume=1.2)
            await star.pipettes.dispense(column(pcr_plate, c), channels=channels, volume=1.2,
                                         mix_cycles=mix, mix_volume=5 if mix else None)
            await star.pipettes.discard_tips(channels=channels)

    comment("Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C")
