from opentrons import protocol_api

metadata = {
    "protocolName": "100 uL reservoir to plate A1-A12",
    "author": "OpenAI",
    "description": "Transfer 100 uL from reservoir A1 to each plate well A1-A12.",
    "apiLevel": "2.15",
}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 1, label="reservoir"
    )
    plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2, label="plate"
    )
    tips_20 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 10, label="20 uL tips"
    )
    tips_300 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 11, label="300 uL tips"
    )

    protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tips_300]
    )

    source = reservoir.wells_by_name()["A1"]
    for column in range(1, 13):
        destination = plate.wells_by_name()[f"A{column}"]
        p300.pick_up_tip()
        p300.aspirate(100, source)
        p300.dispense(100, destination)
        p300.drop_tip()
