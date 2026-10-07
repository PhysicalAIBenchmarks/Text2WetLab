from opentrons import protocol_api

metadata = {
    "protocolName": "Split 200 uL into two 100 uL wells",
    "description": "Transfer 100 uL from reservoir A1 to each of plate A1 and B1.",
    "apiLevel": "2.15",
}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware(
        "nest_1_reservoir_195ml", 1, label="reservoir"
    )
    plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2, label="plate"
    )
    tips20 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 10, label="20 uL tips"
    )
    tips300 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 11, label="300 uL tips"
    )
    protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tips300]
    )

    for well_name in ("A1", "B1"):
        if not p300.has_tip:
            if p300.tip_racks[0].next_tip() is None:
                p300.reset_tipracks()
            p300.pick_up_tip()
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, plate[well_name])
        p300.drop_tip()
