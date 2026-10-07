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
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = [w for col in pcr.columns() for w in col]
    idx = [w.well_name for w in wells]

    # 1. Master mix: one tip, dispensed into empty wells without touching (no cross-contamination)
    p20.pick_up_tip()
    for name in idx:
        p20.aspirate(18, res['A1'])
        p20.dispense(18, pcr[name].bottom(2))
        p20.blow_out(pcr[name].top())
    p20.drop_tip()
    p20.reset_tipracks()

    # 2. Colony template, fresh tip each, mix 3x after dispensing
    for name in idx:
        p20.pick_up_tip()
        p20.aspirate(1, colony[name])
        p20.dispense(1, pcr[name])
        p20.mix(3, 10, pcr[name])
        p20.drop_tip()
    p20.reset_tipracks()

    # 3. Primer pairs, fresh tip each
    for name in idx:
        p20.pick_up_tip()
        p20.aspirate(1, primers[name])
        p20.dispense(1, pcr[name])
        p20.drop_tip()
    p20.reset_tipracks()

    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
