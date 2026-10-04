from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'description': 'Add 2 uL plasmid DNA to competent cells, heat shock 42C 45 s, add 250 uL SOC.',
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

    # 1. Plasmid DNA into competent cells (fresh tip, gentle mix)
    p20.transfer(2, plasmid_plate['A1'], cells, new_tip='always', mix_after=(3, 10))

    # 2. Heat shock (manual)
    protocol.comment('Heat shock cells_rack (tubes_1_5ml_1 A1) at 42°C for 45 s, '
                     'then transfer immediately to ice for 2 min.')

    # 3. SOC recovery medium
    p300.transfer(250, soc_reservoir['A1'], cells, new_tip='always')

    # 4. Outgrowth (manual)
    protocol.comment('Incubate cells_rack at 37°C for 60 min at 250 rpm for outgrowth recovery.')
