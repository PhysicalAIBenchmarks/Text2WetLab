from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = [w for col in pcr.columns() for w in col]
    names = [w.well_name for w in wells]

    # 1. Master mix (single tip, dispensed without touching liquid)
    p20.pick_up_tip()
    for n in names:
        p20.aspirate(18, mm_res['A1'])
        p20.dispense(18, pcr[n].top(-2))
        p20.blow_out(pcr[n].top(-2))
    p20.drop_tip()

    p20.reset_tipracks()

    # 2. Colony template, mix 3x after dispensing
    for n in names:
        p20.pick_up_tip()
        p20.aspirate(1, colony[n])
        p20.dispense(1, pcr[n])
        p20.mix(3, 10, pcr[n])
        p20.drop_tip()

    p20.reset_tipracks()

    # 3. Primer pairs
    for n in names:
        p20.pick_up_tip()
        p20.aspirate(1, primers[n])
        p20.dispense(1, pcr[n])
        p20.drop_tip()

    # 4. Not simulated
    protocol.comment('Seal pcr_plate, thermocycle: 98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
