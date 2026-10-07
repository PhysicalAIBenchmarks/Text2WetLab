"""Colony PCR screening with Q5 Hot Start master mix (OT-2).

Screen transformant colonies by PCR: dispense 18 uL of Q5 Hot Start master
mix into each well of a 96-well PCR plate, add 1 uL of colony template per
well (mix after dispensing), then add 1 uL of the corresponding primer pair.
Based on the Slowpoke colony PCR workflow (ACS Synth. Biol.,
doi:10.1021/acssynbio.5c00629).
"""

from opentrons import protocol_api

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'description': '96-well colony PCR setup: 18 uL Q5 master mix, '
                   '1 uL colony template (mix 3x), 1 uL primer pair per well.',
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------
    # Labware (fixed deck layout)
    # ------------------------------------------------------------------
    colony_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    # Tip racks
    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes: p20 for 1-20 uL, p300 for 20-300 uL
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips_300])

    # Wells A1:H12 in plate order (A1, A2, ..., A12, B1, ..., H12);
    # source and destination wells pair in this order.
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()
    pcr_wells = pcr_plate.wells()

    # ------------------------------------------------------------------
    # Step 1: dispense 18 uL of Q5 Hot Start master mix 2x from the
    # reservoir into every well of the PCR plate.
    # (18 uL is within the p20 range of 1-20 uL.)
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 1: Dispense 18 uL of Q5 Hot Start master mix 2x from '
        'master_mix_reservoir A1 into all 96 wells of pcr_plate.')
    p20.transfer(
        18,
        master_mix_reservoir['A1'],
        pcr_wells,
        new_tip='always',
    )

    # ------------------------------------------------------------------
    # Step 2: add 1 uL of colony template to the corresponding well and
    # mix 3 times after dispensing. Fresh tip per well to avoid
    # cross-contamination between colonies.
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 2: Add 1 uL of colony template from colony_plate to the '
        'corresponding well of pcr_plate and mix 3 times.')
    p20.reset_tipracks()
    p20.transfer(
        1,
        colony_wells,
        pcr_wells,
        new_tip='always',
        mix_after=(3, 10),
    )

    # ------------------------------------------------------------------
    # Step 3: add 1 uL of primer pair to the corresponding well.
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 3: Add 1 uL of primer pair from primer_plate to the '
        'corresponding well of pcr_plate.')
    p20.reset_tipracks()
    p20.transfer(
        1,
        primer_wells,
        pcr_wells,
        new_tip='always',
    )

    # ------------------------------------------------------------------
    # Step 4: off-robot steps (sealing and thermocycling) - not simulated.
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 4: Seal pcr_plate and thermocycle: 98°C for 30 s; '
        '[98°C for 10 s, 60°C for 30 s, 72°C for 30 s] x 30 cycles; '
        '72°C for 2 min; hold at 4°C.')
