# T2WL-CANARY-7f3c9e1a4b
from unitelabs.labware.agilent.tips import AgilentTip_250, AgilentTipRack_250
from unitelabs.labware.agilent.troughs import Agilent_DW_Reservoir
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.liquids import PredefinedLiquids


async def run(bravo, comment):
    # Nine deck locations: six labware and three tip racks; used tips go back into their own rack, so no location is
    # needed for tip waste. The 96-channel head maps tip X to well X, so each rack is a per-well tip set that is put
    # back and re-used for the same wells only, and never goes back into a shared stock after touching a sample:
    #   sample_tips:  bead add + mix, then every supernatant / ethanol removal (dispensed into waste from above)
    #   ethanol_tips: ethanol adds (dispensed from above, never touching the beads); they only ever draw ethanol
    #   water_tips:   water add + mix, then the eluate transfer
    sample_tips = AgilentTipRack_250("sample_tips")
    sample_tips.fill(AgilentTip_250)
    ethanol_tips = AgilentTipRack_250("ethanol_tips")
    ethanol_tips.fill(AgilentTip_250)
    water_tips = AgilentTipRack_250("water_tips")
    water_tips.fill(AgilentTip_250)
    beads = Agilent_DW_Reservoir("beads_reservoir")
    ethanol = Agilent_DW_Reservoir("ethanol_reservoir")
    water = Agilent_DW_Reservoir("water_reservoir")
    for trough in (beads, ethanol, water):
        trough.containers[0].add_liquid(PredefinedLiquids.WATER, 90000)
    waste = Agilent_DW_Reservoir("waste")
    sample_plate = Cos_96_FB("sample_plate")
    for well in sample_plate:
        well.container.add_liquid(PredefinedLiquids.WATER, 50)
    elution_plate = Cos_96_FB("elution_plate")

    bravo.deck.add(sample_tips, location=1)
    bravo.deck.add(ethanol_tips, location=2)
    bravo.deck.add(water_tips, location=3)
    bravo.deck.add(beads, location=4)
    bravo.deck.add(ethanol, location=5)
    bravo.deck.add(water, location=6)
    bravo.deck.add(sample_plate, location=7)
    bravo.deck.add(waste, location=8)
    bravo.deck.add(elution_plate, location=9)
    head = bravo.pipette_head

    async def remove(volume):
        await head.pick_up_tips_from(rack=sample_tips, press_depth=5.8)
        await head.aspirate(sample_plate, volume=volume)
        await head.dispense(waste, volume=volume, liquid_offset=25)        # from above the waste level
        await head.put_down_tips_to(rack=sample_tips)

    async def add_ethanol():
        await head.pick_up_tips_from(rack=ethanol_tips, press_depth=5.8)
        await head.aspirate(ethanol, volume=200)
        await head.dispense(sample_plate, volume=200, liquid_offset=9)     # from above, off the bead pellet
        await head.put_down_tips_to(rack=ethanol_tips)

    # 1. Beads, mixed in
    await head.pick_up_tips_from(rack=sample_tips, press_depth=5.8)
    await head.aspirate(beads, volume=40)
    await head.dispense(sample_plate, volume=40, mix_cycles=10, mix_volume=40)
    await head.put_down_tips_to(rack=sample_tips)
    comment("Incubate sample_plate 5 min at room temperature (beads bind DNA)")
    comment("Engage magnetic module; wait 5 min until solution clears")
    await remove(90)
    # Two ethanol washes
    await add_ethanol()
    await remove(200)
    await add_ethanol()
    await remove(200)
    comment("Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny")
    comment("Disengage magnetic module")
    # Elution
    await head.pick_up_tips_from(rack=water_tips, press_depth=5.8)
    await head.aspirate(water, volume=50)
    await head.dispense(sample_plate, volume=50, mix_cycles=10, mix_volume=50)
    await head.put_down_tips_to(rack=water_tips)
    comment("Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min")
    # Same tips again: tip X has only been in well X (and the water stock, before it touched a sample)
    await head.pick_up_tips_from(rack=water_tips, press_depth=5.8)
    await head.aspirate(sample_plate, volume=45)
    await head.dispense(elution_plate, volume=45)
    await head.put_down_tips_to(rack=water_tips)
