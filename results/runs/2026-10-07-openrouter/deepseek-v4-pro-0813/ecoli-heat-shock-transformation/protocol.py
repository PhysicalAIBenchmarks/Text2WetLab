from opentrons import protocol_api

metadata = {'apiLevel': '2.13'}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    plasmid_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='soc_reservoir')

    # Tip racks and pipettes
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # Step 1: transfer 2 uL plasmid DNA to competent cells.
    p20.transfer(2, plasmid_plate['A1'], tubes_1_5ml_1['A1'], new_tip='once')

    # Step 2: heat shock (manual, not simulated).
    protocol.comment('Heat shock cells_rack 42°C 45 s, '
                     'then transfer immediately to ice 2 min')

    # Step 3: transfer 250 uL SOC medium to each tube.
    p300.transfer(250, soc_reservoir['A1'], tubes_1_5ml_1['A1'], new_tip='once')

    # Step 4: outgrowth recovery (manual, not simulated).
    protocol.comment('Incubate cells_rack 37°C 60 min at 250 rpm '
                     'for outgrowth recovery')