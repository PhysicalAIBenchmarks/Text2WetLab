from opentrons import protocol_api

metadata = {
    'protocolName': '100 uL from 1-well reservoir to A1-A12',
    'author': 'Claude',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # Step 1: 100 uL from reservoir A1 to plate A1:A12 (fresh tip per well)
    dests = plate.wells_by_name()
    for name in ['A' + str(i) for i in range(1, 13)]:
        p300.transfer(100, reservoir['A1'], dests[name], new_tip='always')
