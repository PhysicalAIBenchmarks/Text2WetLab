from opentrons import protocol_api

metadata = {
    "protocolName": "AMPure XP cleanup of 96 PCR products (0.8x)",
    "author": "OpenAI",
    "description": "Clean up 50 uL PCR products and collect 45 uL eluate per well.",
    "apiLevel": "2.15",
}


def run(protocol: protocol_api.ProtocolContext):
    sample_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 1, label="sample_plate"
    )
    beads_reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 2, label="beads_reservoir"
    )
    ethanol_reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 3, label="ethanol_reservoir"
    )
    water_reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 4, label="water_reservoir"
    )
    waste = protocol.load_labware(
        "nest_1_reservoir_195ml", 5, label="waste"
    )
    elution_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 6, label="elution_plate"
    )
    p20_tips = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 10, label="p20_tips"
    )
    p300_tips = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 11, label="p300_tips"
    )
    protocol.load_instrument("p20_single_gen2", "left", tip_racks=[p20_tips])
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[p300_tips]
    )

    # Use the same explicit well order for both plates.
    well_names = [f"{row}{column}" for row in "ABCDEFGH" for column in range(1, 13)]
    samples = [sample_plate[name] for name in well_names]
    eluates = [elution_plate[name] for name in well_names]
    beads = beads_reservoir["A1"]
    ethanol = ethanol_reservoir["A1"]
    water = water_reservoir["A1"]
    liquid_waste = waste["A1"]
    tips_used = 0

    def transfer(volume, source, destination, mix_after=None):
        nonlocal tips_used
        if tips_used == len(p300_tips.wells()):
            protocol.pause("Replace the 300 uL tip rack in slot 11 with a full rack.")
            p300.reset_tipracks()
            tips_used = 0
        p300.pick_up_tip()
        tips_used += 1
        p300.aspirate(volume, source.bottom(1))
        # Keep waste tips above the accumulated liquid.
        dispense_location = (
            destination.top(-5)
            if destination is liquid_waste
            else destination.bottom(1)
        )
        p300.dispense(volume, dispense_location)
        if mix_after is not None:
            repetitions, mix_volume = mix_after
            p300.mix(repetitions, mix_volume, destination.bottom(1))
        p300.drop_tip()

    # 1. Add beads and mix each 90 uL sample/bead suspension.
    for sample in samples:
        transfer(40, beads, sample, mix_after=(10, 50))

    # 2-3. Magnetic actions are comments only; no module occupies this fixed deck.
    protocol.comment("Incubate sample_plate 5 min at room temperature (beads bind DNA).")
    protocol.comment("Engage magnetic module; wait 5 min until solution clears.")

    # 4. Remove the full 90 uL supernatant from every sample.
    for sample in samples:
        transfer(90, sample, liquid_waste)

    # 5-6. First ethanol wash, with the magnet remaining engaged.
    for sample in samples:
        transfer(200, ethanol, sample)
    for sample in samples:
        transfer(200, sample, liquid_waste)

    # 7-8. Second ethanol wash.
    for sample in samples:
        transfer(200, ethanol, sample)
    for sample in samples:
        transfer(200, sample, liquid_waste)

    # 9-10. Dry beads before releasing them from the magnet.
    protocol.comment(
        "Air dry beads 5 min at room temperature (magnet engaged); "
        "beads should appear matte not shiny."
    )
    protocol.comment("Disengage magnetic module.")

    # 11. Resuspend beads in 50 uL nuclease-free water.
    for sample in samples:
        transfer(50, water, sample, mix_after=(10, 40))

    # 12. Elute, then clear the beads again.
    protocol.comment("Incubate sample_plate 2 min at room temperature.")
    protocol.comment("Re-engage magnetic module; wait 5 min until solution clears.")

    # 13. Match each sample well to its corresponding elution well, leaving 5 uL.
    for sample, eluate in zip(samples, eluates):
        transfer(45, sample, eluate)
