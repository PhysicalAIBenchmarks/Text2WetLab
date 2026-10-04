from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR with Q5 Hot Start master mix', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    wells = [w for col in pcr.columns() for w in col]
    idx = [w.well_name for w in wells]

    # 1. master mix (single tip, dispensed without touching liquid)
    p20.pick_up_tip()
    for name in idx:
        p20.aspirate(18, res['A1'])
        p20.dispense(18, pcr[name])
    p20.drop_tip()
    p20.reset_tipracks()

    # 2. colony template, fresh tip each, mix 3x after dispensing
    for name in idx:
        p20.transfer(1, colony[name], pcr[name], new_tip='always', mix_after=(3, 10))
    p20.reset_tipracks()

    # 3. primers, fresh tip each
    for name in idx:
        p20.transfer(1, primers[name], pcr[name], new_tip='always')
    p20.reset_tipracks()

    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
