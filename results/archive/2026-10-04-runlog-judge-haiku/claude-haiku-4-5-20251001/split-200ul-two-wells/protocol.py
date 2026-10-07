from opentrons import protocol_api

metadata = {
    'apiLevel': '2.15'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    # Load pipettes
    p300 = protocol.load_instrument(
        'p300_single_gen2',
        'right',
        tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', 11)]
    )

    # Transfer 100 µL from reservoir A1 to plate wells A1 and B1
    p300.distribute(100, reservoir['A1'], [plate['A1'], plate['B1']])
