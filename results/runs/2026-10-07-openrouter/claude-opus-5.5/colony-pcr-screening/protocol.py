from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-style colony PCR (OT-2)',
    'description': '18 uL Q5 master mix + 1 uL colony template + 1 uL primer mix per well',
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 18
TEMPLATE_VOL = 1
PRIMER_VOL = 1
MIX_REPS = 3
MIX_VOL = 10


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tips_used = {'p20': 0}

    def pick_up(pip):
        # Tips are unlimited: refill the rack once all 96 have been used
        if tips_used['p20'] >= 96:
            pip.reset_tipracks()
            tips_used['p20'] = 0
        pip.pick_up_tip()
        tips_used['p20'] += 1

    sources_colony = colony_plate.wells()  # A1..H12, column-wise
    sources_primer = primer_plate.wells()
    dests = pcr_plate.wells()
    master_mix = mm_res.wells_by_name()['A1']

    # Step 1: 18 uL Q5 master mix into every PCR well (one tip, empty destinations)
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start master mix (2x) to pcr_plate A1:H12')
    pick_up(p20)
    for dest in dests:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest.bottom(2))
        p20.blow_out(dest.top())
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per colony, mix 3x after dispensing
    protocol.comment('Step 2: adding 1 uL colony template to each PCR well and mixing')
    for src, dest in zip(sources_colony, dests):
        pick_up(p20)
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(MIX_REPS, MIX_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well
    protocol.comment('Step 3: adding 1 uL primer pair to each PCR well')
    for src, dest in zip(sources_primer, dests):
        pick_up(p20)
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 4: off-deck
    protocol.comment('Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
