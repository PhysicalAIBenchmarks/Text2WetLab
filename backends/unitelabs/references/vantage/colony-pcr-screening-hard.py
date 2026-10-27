# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, RGT_CAR_3R_A00, RGT_CONT_100ml, TIP_CAR_480_A00,
    HamiltonTip_10, HamiltonTip_50, HamiltonTipRack_10, HamiltonTipRack_50,
)
from unitelabs.labware.liquids import PredefinedLiquids

COLUMNS = range(1, 13)


async def run(vantage, comment):
    tip_carrier = TIP_CAR_480_A00()
    for site in range(3):
        tip_carrier[site] = HamiltonTipRack_10(f"tips10_{site + 1}", filled_with=HamiltonTip_10)
    tip_carrier[3] = HamiltonTipRack_50("tips50_1", filled_with=HamiltonTip_50)
    vantage.deck.add(tip_carrier, track=1)
    plate_carrier = PLT_CAR_L5MD_A00()
    colony_plate, primer_plate, pcr_plate = Cos_96_FB("colony_plate"), Cos_96_FB("primer_plate"), Cos_96_FB("pcr_plate")
    plate_carrier[0], plate_carrier[1], plate_carrier[2] = colony_plate, primer_plate, pcr_plate
    vantage.deck.add(plate_carrier, track=7)
    for plate in (colony_plate, primer_plate):
        for well in plate:
            well.container.add_liquid(PredefinedLiquids.WATER, 100)
    trough_carrier = RGT_CAR_3R_A00()
    master_mix = RGT_CONT_100ml("master_mix_reservoir")
    master_mix.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    trough_carrier[0] = master_mix
    vantage.deck.add(trough_carrier, track=13)

    channels = list(range(8))

    def column(plate, c):
        return plate[f"A{c}":f"H{c}"]

    await vantage.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_50)   # one tip set: stock into empty wells
    for c in COLUMNS:
        await vantage.pipettes.aspirate(master_mix, channels=channels, volume=18)
        await vantage.pipettes.dispense(column(pcr_plate, c), channels=channels, volume=18)
    await vantage.pipettes.discard_tips(channels=channels)

    for source, mix in ((colony_plate, 3), (primer_plate, None)):
        for c in COLUMNS:
            await vantage.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_10)
            await vantage.pipettes.aspirate(column(source, c), channels=channels, volume=1)
            await vantage.pipettes.dispense(column(pcr_plate, c), channels=channels, volume=1,
                                         mix_cycles=mix, mix_volume=5 if mix else None)
            await vantage.pipettes.discard_tips(channels=channels)

    comment("Seal pcr_plate, thermocycle: 98°C 30 s; [98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C")
