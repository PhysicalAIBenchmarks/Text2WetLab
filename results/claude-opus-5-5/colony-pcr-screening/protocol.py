from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-style colony PCR (ACS Synth. Biol., doi:10.1021/acssynbio.5c00629)',
    'description': '18 uL Q5 2x master mix + 1 uL colony template + 1 uL primer mix per well of a 96-well PCR plate.',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware (fixed deck)
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    mm_res = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # p20 handles every volume here (1-18 uL); p300 is loaded but not needed.
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    def pick_up(pip):
        # Tips are unlimited: refill the rack when it runs out
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.reset_tipracks()
            pip.pick_up_tip()

    dests = pcr_plate.wells()  # A1..H12
    mm = mm_res.wells_by_name()['A1']

    # Step 1: 18 uL Q5 2x master mix to every PCR well (one tip, same reagent, clean wells)
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix to pcr_plate A1:H12')
    pick_up(p20)
    for d in dests:
        p20.aspirate(18, mm)
        p20.dispense(18, d.bottom(2))
        p20.blow_out(d.top(-2))
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per colony, mix 3x after dispensing
    protocol.comment('Step 2: adding 1 uL colony template (colony_plate A1:H12 -> pcr_plate A1:H12), mix 3x')
    for src, d in zip(colony_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    # Step 3: 1 uL primer pair mix, fresh tip per well
    protocol.comment('Step 3: adding 1 uL primer pairs (primer_plate A1:H12 -> pcr_plate A1:H12)')
    for src, d in zip(primer_plate.wells(), dests):
        pick_up(p20)
        p20.aspirate(1, src)
        p20.dispense(1, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    # Step 4: off-deck thermocycling
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30; 72C 2 min; hold 4C')
