from opentrons import protocol_api

metadata = {
    'protocolName': '100 uL from 1-well reservoir to plate A1-A12',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    source = reservoir['A1']
    dests = plate.rows_by_name()['A'][:12]

    # 100 uL per well -> p300; one tip, fresh dispense each well
    p300.pick_up_tip()
    for well in dests:
        p300.aspirate(100, source)
        p300.dispense(100, well)
        p300.blow_out(well)
    p300.drop_tip()
