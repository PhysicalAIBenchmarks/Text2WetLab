from opentrons import protocol_api

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck setup
    plasmid_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tiprack_20 = protocol.load_labware(
        'opentrons_96_tiprack_20ul', 10, label='tiprack_20ul')
    tiprack_300 = protocol.load_labware(
        'opentrons_96_tiprack_300ul', 11, label='tiprack_300ul')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    cells_tube = tubes_1_5ml_1['A1']

    # Step 1: add 2 uL plasmid DNA to competent cells
    p20.transfer(
        2,
        plasmid_plate['A1'],
        cells_tube,
        new_tip='always',
    )

    # Step 2: heat shock (not simulated)
    protocol.comment(
        'Heat shock cells_rack 42°C 45 s, then transfer immediately to '
        'ice 2 min')

    # Step 3: add 250 uL SOC medium
    p300.transfer(
        250,
        soc_reservoir['A1'],
        cells_tube,
        new_tip='always',
    )

    # Step 4: outgrowth (not simulated)
    protocol.comment(
        'Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery')
