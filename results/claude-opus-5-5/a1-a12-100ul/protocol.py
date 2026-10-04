from opentrons import protocol_api

metadata = {'apiLevel': '2.15', 'protocolName': '100 uL reservoir to A1-A12'}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    src = reservoir['A1']
    dests = [plate.wells_by_name()['A%d' % i] for i in range(1, 13)]

    p300.pick_up_tip()
    for d in dests:
        p300.aspirate(100, src)
        p300.dispense(100, d)
    p300.drop_tip()
