from opentrons import protocol_api

metadata = {'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    colony = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    wells = [w for col in pcr.columns() for w in col]
    names = [w.well_name for w in wells]

    # Step 1: 18 uL master mix, one tip (dispensed into empty wells, no contact with contents)
    protocol.comment('Step 1: dispense 18 uL Q5 master mix 2x into each PCR well')
    p20.reset_tipracks()
    p20.pick_up_tip()
    mm = reservoir['A1']
    for n in names:
        p20.aspirate(18, mm)
        p20.dispense(18, pcr[n].top(-1))
        p20.blow_out(pcr[n].top(-1))
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per well, mix 3x after dispensing
    protocol.comment('Step 2: add 1 uL colony template, mix 3x')
    p20.reset_tipracks()
    for n in names:
        p20.pick_up_tip()
        p20.aspirate(1, colony[n])
        p20.dispense(1, pcr[n])
        p20.mix(3, 10, pcr[n])
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well
    protocol.comment('Step 3: add 1 uL primer pair')
    p20.reset_tipracks()
    for n in names:
        p20.pick_up_tip()
        p20.aspirate(1, primers[n])
        p20.dispense(1, pcr[n])
        p20.drop_tip()

    protocol.comment('Step 4 (not simulated): Seal pcr_plate, thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
