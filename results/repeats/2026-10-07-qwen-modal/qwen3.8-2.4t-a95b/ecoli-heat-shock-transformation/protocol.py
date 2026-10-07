from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plasmid_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='soc_reservoir')

    # Load tip racks
    tiprack_20 = protocol.load_labware(
        'opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware(
        'opentrons_96_tiprack_300ul', 11)

    # Load pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Step 1: Transfer 2 uL plasmid DNA from plasmid_plate A1 to tube A1
    p20.pick_up_tip()
    p20.aspirate(2, plasmid_plate['A1'])
    p20.dispense(2, tubes_1_5ml_1['A1'])
    p20.drop_tip()

    # Step 2: Heat shock (not simulated)
    protocol.comment(
        'Heat shock cells_rack at 42C for 45 s, then transfer immediately '
        'to ice for 2 min')

    # Step 3: Transfer 250 uL SOC medium from reservoir A1 to tube A1
    p300.pick_up_tip()
    p300.aspirate(250, soc_reservoir['A1'])
    p300.dispense(250, tubes_1_5ml_1['A1'])
    p300.drop_tip()

    # Step 4: Incubation (not simulated)
    protocol.comment(
        'Incubate cells_rack at 37C for 60 min at 250 rpm for outgrowth '
        'recovery')
