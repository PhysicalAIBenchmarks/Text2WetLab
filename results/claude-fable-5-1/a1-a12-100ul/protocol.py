from opentrons import protocol_api

metadata = {
    'protocolName': '100 uL from 1-well reservoir to A1-A12',
    'author': 'Claude',
    'description': 'Transfer 100 uL from a 1-well reservoir to wells A1-A12 of a 96-well plate',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Step 1: 100 uL from reservoir A1 to plate A1..A12 (fresh tip per well)
    source = reservoir['A1']
    destinations = plate.rows()[0]  # A1 to A12
    for dest in destinations:
        p300.pick_up_tip()
        p300.aspirate(100, source)
        p300.dispense(100, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()
