from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'author': 'OT-2 protocol',
    'description': 'Transform competent E. coli with 2 uL plasmid DNA, heat shock '
                   'at 42C for 45 s, then add 250 uL SOC medium for recovery.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware ----
    plasmid_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ---- Pipettes ----
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # ---- Wells ----
    plasmid = plasmid_plate.wells_by_name()['A1']
    cells = tubes_1_5ml_1.wells_by_name()['A1']   # 50 uL competent cells
    soc = soc_reservoir.wells_by_name()['A1']

    # Step 1: 2 uL plasmid DNA into competent cells
    protocol.comment('Step 1: Transfer 2 uL plasmid DNA to competent cells.')
    p20.pick_up_tip()
    p20.aspirate(2, plasmid)
    p20.dispense(2, cells)
    p20.mix(3, 10, cells)
    p20.blow_out(cells.top())
    p20.drop_tip()

    # Step 2: heat shock (manual, not simulated)
    protocol.comment(
        'Step 2 (manual): Heat shock '
        'cells_rack at 42 C for 45 s, then transfer immediately to ice for 2 min.')
    protocol.pause('Perform heat shock (42 C, 45 s) and ice (2 min) on '
                   'cells_rack, then return it to slot 2 and resume.')

    # Step 3: 250 uL SOC medium into transformed cells
    protocol.comment('Step 3: Add 250 uL SOC medium to transformed cells.')
    p300.pick_up_tip()
    p300.aspirate(250, soc)
    p300.dispense(250, cells)
    p300.blow_out(cells.top())
    p300.drop_tip()

    # Step 4: outgrowth (manual, not simulated)
    protocol.comment(
        'Step 4 (manual): Incubate cells_rack at 37 C for 60 min at 250 rpm '
        'for outgrowth recovery.')
