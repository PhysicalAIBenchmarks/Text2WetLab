from opentrons import protocol_api

metadata = {
    'protocolName': 'Slowpoke colony PCR setup (Q5 Hot Start)',
    'author': 'Slowpoke-style OT-2 colony PCR',
    'description': 'Dispense 18 uL Q5 Hot Start 2x master mix, then 1 uL colony '
                   'template and 1 uL primer mix into each well of a 96-well PCR plate.',
    'apiLevel': '2.15',
}

MASTER_MIX_UL = 18
TEMPLATE_UL = 1
PRIMER_UL = 1


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tips_used = {'n': 0}

    def pick_up():
        # Single 20 uL rack; refill (reset) when exhausted.
        if tips_used['n'] == 96:
            p20.reset_tipracks()
            tips_used['n'] = 0
        p20.pick_up_tip()
        tips_used['n'] += 1

    dest = pcr_plate.wells()  # A1..H12, column-wise
    master_mix = mm_res.wells_by_name()['A1']

    # Step 1: 18 uL Q5 Hot Start 2x master mix into every well (one tip; clean dispense into empty wells)
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix to pcr_plate A1:H12')
    pick_up()
    for well in dest:
        p20.aspirate(MASTER_MIX_UL, master_mix)
        p20.dispense(MASTER_MIX_UL, well.top(-2))
        p20.blow_out(well.top(-2))
        p20.touch_tip(well)
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per colony, mix 3x after dispensing
    protocol.comment('Step 2: adding 1 uL colony template, mixing 3x')
    for src, well in zip(colony_plate.wells(), dest):
        pick_up()
        p20.aspirate(TEMPLATE_UL, src)
        p20.dispense(TEMPLATE_UL, well)
        p20.mix(3, 10, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well
    protocol.comment('Step 3: adding 1 uL primer pair per well')
    for src, well in zip(primer_plate.wells(), dest):
        pick_up()
        p20.aspirate(PRIMER_UL, src)
        p20.dispense(PRIMER_UL, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 4: off-deck
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
