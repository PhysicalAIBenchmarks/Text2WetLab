from opentrons import protocol_api

metadata = {'protocolName': 'Split 200 uL into two 100 uL wells', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # Step 1: 100 uL reagent from reservoir A1 to plate A1, B1
    p300.transfer(100, reservoir['A1'], [plate['A1'], plate['B1']], new_tip='always')
