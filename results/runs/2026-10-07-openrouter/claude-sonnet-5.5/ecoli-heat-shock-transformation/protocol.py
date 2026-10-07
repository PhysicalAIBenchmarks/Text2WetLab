from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    plasmid_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    soc = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # Step 1: plasmid DNA into competent cells
    p20.transfer(2, plasmid_plate['A1'], tubes['A1'], new_tip='always')

    # Step 2: heat shock
    protocol.comment('Heat shock cells_rack (tubes_1_5ml_1) at 42 C for 45 s, then transfer immediately to ice for 2 min')

    # Step 3: SOC medium
    p300.transfer(250, soc['A1'], tubes['A1'], new_tip='always')

    # Step 4: outgrowth
    protocol.comment('Incubate cells_rack (tubes_1_5ml_1) at 37 C for 60 min at 250 rpm for outgrowth recovery')
