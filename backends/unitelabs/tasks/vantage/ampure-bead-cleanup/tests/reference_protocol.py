# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, RGT_CAR_3R_A00, RGT_CONT_100ml, TIP_CAR_480_A00, HamiltonTip_300, HamiltonTipRack_300,
)
from unitelabs.labware.liquids import PredefinedLiquids

COLUMNS = range(1, 13)


async def run(vantage, comment):
    for track, first in ((1, 1), (7, 6)):
        tip_carrier = TIP_CAR_480_A00()
        for site in range(5):
            tip_carrier[site] = HamiltonTipRack_300(f"tips300_{first + site}", filled_with=HamiltonTip_300)
        vantage.deck.add(tip_carrier, track=track)
    plate_carrier = PLT_CAR_L5MD_A00()
    sample_plate, elution_plate = Cos_96_FB("sample_plate"), Cos_96_FB("elution_plate")
    plate_carrier[0], plate_carrier[1] = sample_plate, elution_plate
    vantage.deck.add(plate_carrier, track=13)
    for well in sample_plate:
        well.container.add_liquid(PredefinedLiquids.WATER, 50)
    reagents = RGT_CAR_3R_A00()
    beads, ethanol, water = RGT_CONT_100ml("beads_reservoir"), RGT_CONT_100ml("ethanol_reservoir"), RGT_CONT_100ml("water_reservoir")
    for site, trough in enumerate((beads, ethanol, water)):
        trough.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
        reagents[site] = trough
    vantage.deck.add(reagents, track=19)
    waste_carrier = RGT_CAR_3R_A00()
    waste = RGT_CONT_100ml("waste")
    waste_carrier[0] = waste
    vantage.deck.add(waste_carrier, track=20)

    channels = list(range(8))

    def column(plate, c):
        return plate[f"A{c}":f"H{c}"]

    async def fresh_tips():
        await vantage.pipettes.pick_up_tips(channels=channels, tip_type=HamiltonTip_300)

    async def add_per_column(trough, volume, mix_cycles=None):
        for c in COLUMNS:
            await fresh_tips()
            await vantage.pipettes.aspirate(trough, channels=channels, volume=volume)
            await vantage.pipettes.dispense(column(sample_plate, c), channels=channels, volume=volume,
                                         mix_cycles=mix_cycles, mix_volume=volume if mix_cycles else None)
            await vantage.pipettes.discard_tips(channels=channels)

    async def remove_per_column(volume):
        for c in COLUMNS:
            await fresh_tips()
            await vantage.pipettes.aspirate(column(sample_plate, c), channels=channels, volume=volume)
            await vantage.pipettes.dispense(waste, channels=channels, volume=volume)
            await vantage.pipettes.discard_tips(channels=channels)

    async def ethanol_wash():
        await fresh_tips()                      # one tip set: it only ever touches the stock and clean wells from above
        for c in COLUMNS:
            await vantage.pipettes.aspirate(ethanol, channels=channels, volume=200)
            await vantage.pipettes.dispense(column(sample_plate, c), channels=channels, volume=200)
        await vantage.pipettes.discard_tips(channels=channels)
        await remove_per_column(200)

    await add_per_column(beads, 40, mix_cycles=10)
    comment("Incubate sample_plate 5 min at room temperature (beads bind DNA)")
    comment("Engage magnetic module; wait 5 min until solution clears")
    await remove_per_column(90)
    await ethanol_wash()
    await ethanol_wash()
    comment("Air dry beads 5 min at room temperature (magnet engaged)")
    comment("Disengage magnetic module")
    await add_per_column(water, 50, mix_cycles=10)
    comment("Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min")
    for c in COLUMNS:
        await fresh_tips()
        await vantage.pipettes.aspirate(column(sample_plate, c), channels=channels, volume=45)
        await vantage.pipettes.dispense(column(elution_plate, c), channels=channels, volume=45)
        await vantage.pipettes.discard_tips(channels=channels)
