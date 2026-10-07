from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR screening with Q5 Hot Start master mix",
    "author": "OpenAI",
    "description": "Prepare 96 colony PCR reactions, each with a final volume of 20 uL.",
    "apiLevel": "2.15",
}


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 1, label="colony_plate"
    )
    pcr_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2, label="pcr_plate"
    )
    master_mix_reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 3, label="master_mix_reservoir"
    )
    primer_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 4, label="primer_plate"
    )
    p20_tips = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 10, label="p20_tips"
    )
    p300_tips = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 11, label="p300_tips"
    )
    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[p20_tips]
    )
    protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[p300_tips]
    )

    # Use matching well names in row order: A1, A2, ..., H12.
    well_names = [f"{row}{column}" for row in "ABCDEFGH" for column in range(1, 13)]
    tips_used = 0

    def pick_up_fresh_tip():
        nonlocal tips_used
        if tips_used == 96:
            protocol.comment("Replenish the P20 tip rack in slot 10 with fresh tips.")
            protocol.pause("Replace the P20 tip rack in slot 10, then resume.")
            p20.reset_tipracks()
            tips_used = 0
        p20.pick_up_tip()
        tips_used += 1

    protocol.comment("Step 1: Add 18 uL Q5 master mix 2x to all 96 PCR wells.")
    for name in well_names:
        pick_up_fresh_tip()
        p20.aspirate(18, master_mix_reservoir["A1"])
        p20.dispense(18, pcr_plate[name])
        p20.drop_tip()

    protocol.comment("Step 2: Add 1 uL matching colony template; mix 3 times.")
    for name in well_names:
        pick_up_fresh_tip()
        p20.aspirate(1, colony_plate[name])
        p20.dispense(1, pcr_plate[name])
        # Each well now contains 19 uL; a 10 uL mix stays within P20 limits.
        p20.mix(3, 10, pcr_plate[name])
        p20.drop_tip()

    protocol.comment("Step 3: Add 1 uL matching primer pairs to all 96 PCR wells.")
    for name in well_names:
        pick_up_fresh_tip()
        p20.aspirate(1, primer_plate[name])
        p20.dispense(1, pcr_plate[name])
        p20.drop_tip()

    protocol.comment("Step 4: Seal pcr_plate; each well contains 20 uL.")
    protocol.comment(
        "Thermocycle externally: 98 degrees C for 30 s; "
        "[98 degrees C for 10 s, 60 degrees C for 30 s, "
        "72 degrees C for 30 s] x 30 cycles; "
        "72 degrees C for 2 min; hold at 4 degrees C."
    )
