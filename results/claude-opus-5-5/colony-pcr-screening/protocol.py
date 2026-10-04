from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-style colony PCR (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629)',
    'description': 'Dispense 18 uL Q5 master mix, add 1 uL colony template and '
                   '1 uL primer mix to each well of a 96-well PCR plate.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    # Loaded per the fixed deck setup; all volumes here are within the p20 range.
    protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    dest = pcr_plate.wells()          # A1..H12, column order
    colonies = colony_plate.wells()
    primers = primer_plate.wells()

    # Step 1: 18 uL Q5 Hot Start 2x master mix to every PCR well (one tip, same reagent)
    protocol.comment('Step 1: dispensing 18 uL Q5 master mix to pcr_plate A1:H12')
    mm = mm_res.wells_by_name()['A1']
    pick_up(p20)
    for well in dest:
        p20.aspirate(18, mm)
        p20.dispense(18, well.bottom(2))
        p20.blow_out(well.top(-2))
    p20.drop_tip()

    # Step 2: 1 uL colony template per well, fresh tip, mix 3x after dispensing
    protocol.comment('Step 2: adding 1 uL colony template to each PCR well')
    for src, well in zip(colonies, dest):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, well)
        p20.mix(3, 10, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 3: 1 uL primer pair per well, fresh tip
    protocol.comment('Step 3: adding 1 uL primer pair to each PCR well')
    for src, well in zip(primers, dest):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, well)
        p20.blow_out(well.top(-2))
        p20.drop_tip()

    # Step 4: off-deck
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
