metadata = {'apiLevel': '2.13'}


def run(protocol):
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])
    lw_plasmid_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='plasmid_plate')
    lw_tubes_1_5ml_1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    lw_soc_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='soc_reservoir')
    # step 1: transfer
    p20.reset_tipracks(); p300.reset_tipracks()
    p20.transfer(2.0, lw_plasmid_plate['A1'], [lw_tubes_1_5ml_1['A1']], new_tip='once')
    # step 2: manual
    p20.reset_tipracks(); p300.reset_tipracks()
    protocol.comment('Heat shock cells_rack 42°C 45 s, then transfer immediately to ice 2 min')
    # step 3: transfer
    p20.reset_tipracks(); p300.reset_tipracks()
    p300.transfer(250.0, lw_soc_reservoir['A1'], [lw_tubes_1_5ml_1['A1']], new_tip='once')
    # step 4: manual
    p20.reset_tipracks(); p300.reset_tipracks()
    protocol.comment('Incubate cells_rack 37°C 60 min at 250 rpm for outgrowth recovery')
