from opentrons import protocol_api

metadata = {
    'apiLevel': '2.15',
    'protocolName': 'Transfer from 1-well reservoir to plate A1:A12',
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    # Load pipette tips
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Load pipettes
    p20_left = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300_right = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Transfer 100 µL from reservoir A1 to plate A1:A12 using distribute
    p300_right.distribute(
        100,
        reservoir['A1'],
        [plate[f'A{i}'] for i in range(1, 13)]
    )
