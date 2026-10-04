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
    dests = [plate.wells_by_name()['A{}'.format(i)] for i in range(1, 13)]

    # 100 uL per well -> P300; one tip reused since every destination receives the same liquid
    p300.pick_up_tip()
    for well in dests:
        p300.aspirate(100, source)
        p300.dispense(100, well)
        p300.blow_out(well.top())
    p300.drop_tip()
