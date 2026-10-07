from opentrons import protocol_api

metadata = {
    'protocolName': 'Split 200 uL into two 100 uL wells',
    'author': 'Claude',
    'description': 'Transfer 100 uL reagent from reservoir A1 to plate wells A1 and B1',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    # Tip racks
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Step 1: 100 uL reagent from reservoir A1 -> plate A1, B1 (one tip per destination)
    source = reservoir['A1']
    for dest in [plate['A1'], plate['B1']]:
        p300.pick_up_tip()
        p300.aspirate(100, source)
        p300.dispense(100, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()
