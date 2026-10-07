from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke workflow (Golden Gate cloning and colony PCR on OT-2/Flex)',
    'description': (
        '18 uL Q5 Hot Start 2x master mix per well, then 1 uL colony template '
        'and 1 uL primer pair per well of a 96-well PCR plate.'
    ),
    'apiLevel': '2.15',
}

MASTER_MIX_VOL = 18
TEMPLATE_VOL = 1
PRIMER_VOL = 1
MIX_REPS = 3
MIX_VOL = 10


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    def pick_up(pipette):
        """Pick up a tip, refilling the rack when it runs out."""
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            protocol.comment('Tip rack empty - replace with a fresh rack.')
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    master_mix = master_mix_reservoir['A1']
    dest_wells = pcr_plate.wells()
    template_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # Step 1: 18 uL Q5 2x master mix into every well of the PCR plate.
    # Destination wells are empty, so one tip is reused for all dispenses.
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix '
                     'into pcr_plate A1:H12.')
    pick_up(p20)
    for dest in dest_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest)
        p20.blow_out(dest.top())
    p20.drop_tip()

    # Step 2: 1 uL colony template, fresh tip per colony, mix 3x after dispense.
    protocol.comment('Step 2: adding 1 uL colony template from colony_plate '
                     'to pcr_plate (A1 to A1 ... H12 to H12), mixing 3x.')
    for src, dest in zip(template_wells, dest_wells):
        pick_up(p20)
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(MIX_REPS, MIX_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 3: 1 uL primer pair, fresh tip per well.
    protocol.comment('Step 3: adding 1 uL primer pair from primer_plate '
                     'to pcr_plate (A1 to A1 ... H12 to H12).')
    for src, dest in zip(primer_wells, dest_wells):
        pick_up(p20)
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 4: off-deck, not simulated.
    protocol.comment('Step 4: Seal pcr_plate and thermocycle: 98C 30 s; '
                     '[98C 10 s, 60C 30 s, 72C 30 s] x 30 cycles; '
                     '72C 2 min; hold at 4C.')
    protocol.comment('Protocol complete: each pcr_plate well holds 20 uL '
                     '(18 uL master mix + 1 uL template + 1 uL primers).')
