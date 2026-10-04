from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'description': 'Add plasmid DNA to competent cells, heat shock, then add SOC for recovery.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    plasmid_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    cells = tubes['A1']

    # Step 1: 2 uL plasmid DNA into competent cells (fresh tip, gentle mix)
    p20.transfer(2, plasmid_plate['A1'], cells, new_tip='always', mix_after=(3, 10))

    # Step 2: heat shock (manual)
    protocol.comment('Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min')

    # Step 3: 250 uL SOC medium
    p300.transfer(250, soc_reservoir['A1'], cells, new_tip='always')

    # Step 4: outgrowth (manual)
    protocol.comment('Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery')
