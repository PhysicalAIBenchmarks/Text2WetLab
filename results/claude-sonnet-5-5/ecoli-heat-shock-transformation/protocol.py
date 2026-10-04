from opentrons import protocol_api

metadata = {'protocolName': 'Heat shock transformation with SOC recovery', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    tubes = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    soc = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    p20.transfer(2, plate['A1'], tubes['A1'], new_tip='always')
    protocol.comment('Heat shock cells_rack 42C 45 s, then transfer immediately to ice 2 min')
    p300.transfer(250, soc['A1'], tubes['A1'], new_tip='always')
    protocol.comment('Incubate cells_rack 37C 60 min at 250 rpm for outgrowth recovery')
