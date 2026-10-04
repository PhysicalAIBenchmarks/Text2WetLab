"""Colony PCR screening with Q5 Hot Start master mix (OT-2).

Based on the Slowpoke colony PCR workflow (ACS Synth. Biol.,
doi:10.1021/acssynbio.5c00629): master mix is dispensed into every well of
the PCR plate first, then 1 uL of colony template and 1 uL of the matching
primer pair are added per well, and the sealed plate is thermocycled.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'author': 'Slowpoke-derived OT-2 protocol',
    'description': ('96 colony PCR reactions: 18 uL Q5 Hot Start 2x master mix, '
                    '1 uL colony template, 1 uL primer pair per well.'),
    'apiLevel': '2.15',
}

# Volumes (uL)
MASTER_MIX_VOL = 18
TEMPLATE_VOL = 1
PRIMER_VOL = 1
MIX_REPETITIONS = 3
MIX_VOL = 10  # ~half of the 19 uL in the well after template addition


def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
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

    # ----- Pipettes -----
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(  # noqa: F841 (loaded per deck setup; all volumes are <= 20 uL)
        'p300_single_gen2', 'right', tip_racks=[tips300])

    master_mix = master_mix_reservoir['A1']
    dest_wells = pcr_plate.wells()          # A1..H12, column-major order
    template_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # ----- Step 1: 18 uL Q5 Hot Start 2x master mix into every PCR well -----
    # Destination wells are empty, so one tip can be reused for the whole plate.
    protocol.comment('Step 1: dispensing 18 uL Q5 Hot Start 2x master mix into pcr_plate A1:H12')
    p20.pick_up_tip()
    for dest in dest_wells:
        p20.aspirate(MASTER_MIX_VOL, master_mix)
        p20.dispense(MASTER_MIX_VOL, dest)
        p20.blow_out(dest.top())
    p20.drop_tip()
    p20.reset_tipracks()

    # ----- Step 2: 1 uL colony template, fresh tip per well, mix 3x after -----
    protocol.comment('Step 2: adding 1 uL colony template (colony_plate -> pcr_plate, well to well), '
                     'mixing 3x after dispensing')
    for src, dest in zip(template_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, src)
        p20.dispense(TEMPLATE_VOL, dest)
        p20.mix(MIX_REPETITIONS, MIX_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()
    p20.reset_tipracks()

    # ----- Step 3: 1 uL primer pair, fresh tip per well -----
    protocol.comment('Step 3: adding 1 uL primer pair (primer_plate -> pcr_plate, well to well)')
    for src, dest in zip(primer_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, src)
        p20.dispense(PRIMER_VOL, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()
    p20.reset_tipracks()

    # ----- Step 4: off-deck seal and thermocycle -----
    protocol.comment('Step 4 (manual): seal pcr_plate and thermocycle: '
                     '98C 30 s; [98C 10 s, 60C 30 s, 72C 30 s] x 30 cycles; '
                     '72C 2 min; hold at 4C.')
    protocol.comment('Protocol complete: 96 x 20 uL colony PCR reactions ready.')
