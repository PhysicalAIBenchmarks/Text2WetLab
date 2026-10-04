from opentrons import protocol_api

metadata = {'protocolName': 'Heat shock transformation with SOC recovery'}
requirements = {'robotType': 'OT-2', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    plasmid_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    soc = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # 1. plasmid DNA into cells
    p20.pick_up_tip()
    p20.aspirate(2, plasmid_plate['A1'])
    p20.dispense(2, tubes['A1'])
    p20.drop_tip()

    # 2. heat shock
    protocol.comment('Heat shock cells_rack 42C 45 s, then transfer immediately to ice 2 min')

    # 3. SOC
    p300.pick_up_tip()
    p300.aspirate(250, soc['A1'])
    p300.dispense(250, tubes['A1'])
    p300.drop_tip()

    # 4. recovery
    protocol.comment('Incubate cells_rack 37C 60 min at 250 rpm for outgrowth recovery')
