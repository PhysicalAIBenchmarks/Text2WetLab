from opentrons import protocol_api

metadata = {
    'protocolName': 'Distribute 100 uL from reservoir to plate A1:A12',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='plate')

    # Load pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left',
        tip_racks=[protocol.load_labware(
            'opentrons_96_tiprack_20ul', 10)])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right',
        tip_racks=[protocol.load_labware(
            'opentrons_96_tiprack_300ul', 11)])

    # 100 uL needs the 300 uL pipette
    pipette = p300

    # Step 1: Transfer 100 uL from reservoir A1 to plate wells A1:A12.
    # One source well feeds every destination well; distribute() chunks
    # the aspirates so the tip never holds more than the pipette can.
    pipette.distribute(100, reservoir['A1'], plate.rows()[0])
