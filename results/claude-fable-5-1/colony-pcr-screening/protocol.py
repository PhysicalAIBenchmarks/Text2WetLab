"""Colony PCR screening with Q5 Hot Start master mix."""

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'OT-2 protocol',
    'description': 'Dispense Q5 master mix, colony template and primer mix into a 96-well PCR plate.',
    'apiLevel': '2.13',
}


def run(protocol):
    # Labware
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # Tip bookkeeping: tips are unlimited, reset a rack once it has been exhausted.
    tip_count = {'p20': 0}

    def pick_up_p20():
        if tip_count['p20'] >= 96:
            p20.reset_tipracks()
            tip_count['p20'] = 0
        p20.pick_up_tip()
        tip_count['p20'] += 1

    dest_wells = pcr_plate.wells()[:96]
    colony_wells = colony_plate.wells()[:96]
    primer_wells = primer_plate.wells()[:96]
    master_mix = master_mix_reservoir.wells_by_name()['A1']

    # Step 1: 18 uL Q5 master mix 2x to every PCR plate well (single tip, reservoir source).
    protocol.comment('Step 1: Adding 18 uL Q5 Hot Start master mix (2x) to pcr_plate A1:H12.')
    pick_up_p20()
    for dest in dest_wells:
        p20.aspirate(18, master_mix)
        p20.dispense(18, dest)
        p20.blow_out(dest.top())
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per well, mix 3x after dispensing.
    protocol.comment('Step 2: Adding 1 uL colony template from colony_plate to pcr_plate, mixing 3x.')
    for src, dest in zip(colony_wells, dest_wells):
        pick_up_p20()
        p20.aspirate(1, src)
        p20.dispense(1, dest)
        p20.mix(3, 10, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well.
    protocol.comment('Step 3: Adding 1 uL primer mix from primer_plate to pcr_plate.')
    for src, dest in zip(primer_wells, dest_wells):
        pick_up_p20()
        p20.aspirate(1, src)
        p20.dispense(1, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 4: off-robot steps.
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30 cycles; 72C 2 min; hold 4C.')
