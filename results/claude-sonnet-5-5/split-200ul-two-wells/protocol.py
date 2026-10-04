from opentrons import protocol_api

metadata = {'apiName': 'split', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    p300.pick_up_tip()
    for dest in ('A1', 'B1'):
        p300.aspirate(100, reservoir['A1'])
        p300.dispense(100, plate[dest])
    p300.drop_tip()
