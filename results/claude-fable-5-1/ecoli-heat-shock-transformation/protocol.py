from opentrons import protocol_api

metadata = {
    'protocolName': 'E. coli heat shock transformation with SOC recovery',
    'author': 'OT-2',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    plasmid_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    soc_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    cells_tube = tubes_1_5ml_1['A1']

    # Step 1: 2 uL plasmid DNA into competent cells
    p20.pick_up_tip()
    p20.aspirate(2, plasmid_plate['A1'])
    p20.dispense(2, cells_tube)
    p20.mix(3, 10, cells_tube)
    p20.blow_out(cells_tube.top())
    p20.drop_tip()

    # Step 2: heat shock (not simulated)
    protocol.comment('Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min')

    # Step 3: 250 uL SOC medium into cells
    p300.pick_up_tip()
    p300.aspirate(250, soc_reservoir['A1'])
    p300.dispense(250, cells_tube)
    p300.blow_out(cells_tube.top())
    p300.drop_tip()

    # Step 4: outgrowth recovery (not simulated)
    protocol.comment('Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery')
