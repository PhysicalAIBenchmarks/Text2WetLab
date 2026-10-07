from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR screening with Q5 Hot Start master mix', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = [w for col in pcr.columns() for w in col]
    idx = [w.well_name for w in wells]

    # 1. master mix (single tip: reagent only, dispensed into empty wells)
    p20.pick_up_tip()
    for name in idx:
        p20.aspirate(18, res['A1'])
        p20.dispense(18, pcr[name].top(-2))
        p20.blow_out(pcr[name].top(-2))
    p20.drop_tip()

    # 2. colony template, fresh tip each, mix 3x after dispensing
    for name in idx:
        if p20.tip_racks[0].next_tip() is None:
            p20.reset_tipracks()
        p20.pick_up_tip()
        p20.aspirate(1, colony[name])
        p20.dispense(1, pcr[name])
        p20.mix(3, 10, pcr[name])
        p20.drop_tip()

    # 3. primers, fresh tip each
    for name in idx:
        if p20.tip_racks[0].next_tip() is None:
            p20.reset_tipracks()
        p20.transfer(1, primers[name], pcr[name], new_tip='always')

    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
