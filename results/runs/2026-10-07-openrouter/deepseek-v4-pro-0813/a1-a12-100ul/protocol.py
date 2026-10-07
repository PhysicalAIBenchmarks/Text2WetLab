from opentrons import protocol_api

# Metadata
metadata = {
    'apiLevel': '2.15',
    'protocolName': '100uL reservoir to plate A1-A12',
    'description': 'Transfer 100 uL from a 1-well reservoir to wells A1:A12 of a 96-well plate.',
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='plate')

    # Pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[])

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20.tip_racks = [tiprack_20]
    p300.tip_racks = [tiprack_300]

    # 100 uL is within p300 range (20-300 uL), so use p300.
    p300.reset_tipracks()
    p300.transfer(
        100,
        reservoir['A1'],
        plate.rows()[0],  # A1:A12
        new_tip='once',
    )