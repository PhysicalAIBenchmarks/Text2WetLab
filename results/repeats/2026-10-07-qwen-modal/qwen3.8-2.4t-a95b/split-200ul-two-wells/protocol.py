from opentrons import protocol_api

metadata = {'protocolName': 'Split 200 uL into two 100 uL wells',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware exactly as the deck is set up.
    reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='plate')

    # Load tip racks.
    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Load pipettes.
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # 100 uL transfers are within the p300 range (20-300 uL).
    source = reservoir.wells_by_name()['A1']
    destinations = [plate.wells_by_name()['A1'],
                    plate.wells_by_name()['B1']]

    # Transfer 100 uL of reagent from reservoir A1 to plate A1, then B1.
    p300.pick_up_tip()
    for dest in destinations:
        p300.aspirate(100, source)
        p300.dispense(100, dest)
    p300.drop_tip()
