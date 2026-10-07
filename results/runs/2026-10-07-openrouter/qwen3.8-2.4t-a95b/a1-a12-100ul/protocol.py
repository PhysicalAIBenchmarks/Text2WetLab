metadata = {
    'protocolName': 'Reservoir to 96-well plate A1:A12 - 100 uL',
    'description': 'Transfer 100 uL from a 1-well reservoir (A1) to plate wells A1 through A12.',
    'apiLevel': '2.15',
}


def run(protocol):
    # Labware
    reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 1, label='reservoir')
    plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='plate')

    # Pipettes and tips
    tips_20 = protocol.load_labware(
        'opentrons_96_tiprack_20ul', 10, label='20 uL tips')
    tips_300 = protocol.load_labware(
        'opentrons_96_tiprack_300ul', 11, label='300 uL tips')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # 100 uL is within the p300 range (20-300 uL); the p20 cannot handle it.
    source = reservoir.wells_by_name()['A1']
    destinations = [plate.wells_by_name()[f'A{i}'] for i in range(1, 13)]

    protocol.comment('Transferring 100 uL from reservoir A1 to plate A1:A12')

    for well in destinations:
        p300.transfer(100, source, well, new_tip='always')

    # Ensure no tip is left on the pipette at the end (transfer drops it,
    # but be explicit for safety).
    if p300.has_tip:
        p300.drop_tip()
    if p20.has_tip:
        p20.drop_tip()
