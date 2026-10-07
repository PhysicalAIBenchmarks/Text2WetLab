from opentrons import protocol_api

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'Split 200 uL into two 100 uL wells',
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware with labels exactly as specified
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    # Pipettes: p300 on the right (for 100 uL), tips are unlimited
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right',
        tip_racks=[protocol.load_labware('opentrons_96_tiprack_300ul', 11)],
    )

    # Reset tip racks to indicate tips are unlimited
    p300.reset_tipracks()

    # Transfer 100 uL from reservoir A1 to plate A1 and B1
    p300.transfer(
        100,
        reservoir['A1'],
        [plate['A1'], plate['B1']],
        new_tip='once',
    )