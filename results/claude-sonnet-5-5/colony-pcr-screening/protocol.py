from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR screening with Q5', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    wells = [w for col in pcr.columns() for w in col]
    idx = list(range(96))
    used = 0

    def pick():
        nonlocal used
        if used >= 96:
            p20.reset_tipracks()
            used = 0
        p20.pick_up_tip()
        used += 1

    # 1. master mix (single tip, destination wells are empty)
    pick()
    for w in wells:
        p20.aspirate(18, res['A1'])
        p20.dispense(18, w)
    p20.drop_tip()
    used = 1

    # 2. colony template, mix after dispensing
    for i, w in enumerate(wells):
        src = colony.columns()[i // 8][i % 8]
        pick()
        p20.aspirate(1, src)
        p20.dispense(1, w)
        p20.mix(3, 10, w)
        p20.drop_tip()

    # 3. primers
    for i, w in enumerate(wells):
        src = primers.columns()[i // 8][i % 8]
        pick()
        p20.aspirate(1, src)
        p20.dispense(1, w)
        p20.drop_tip()

    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
