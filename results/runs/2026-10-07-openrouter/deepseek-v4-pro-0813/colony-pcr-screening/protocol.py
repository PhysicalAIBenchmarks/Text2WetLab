"""Colony PCR screening with Q5 Hot Start master mix (OT-2).

Transfer 18 µL Q5 master mix 2x, then 1 µL colony template, then 1 µL primer
mix into each well of a 96-well PCR plate, then seal and thermocycle.
"""

from opentrons import protocol_api

metadata = {
    'apiLevel': '2.15',
    'protocolName': 'Colony PCR screening with Q5 Hot Start master mix',
    'description': 'Distribute Q5 master mix, colony template and primer '
                   'pairs to a 96-well PCR plate, then seal and thermocycle.',
}


def run(protocol: protocol_api.ProtocolContext):
    # Tip racks
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left',
                                   tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips300])

    # Labware (deck layout is fixed)
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1,
                                         label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2,
                                      label='pcr_plate')
    master_mix_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3,
                                                 label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4,
                                         label='primer_plate')

    # All 96 wells in row-major order: A1..A12, B1..B12, ..., H1..H12.
    pcr_wells = pcr_plate.wells()
    colony_wells = colony_plate.wells()
    primer_wells = primer_plate.wells()

    # Step 1: 18 µL Q5 master mix 2x -> every PCR well (single source well).
    p20.transfer(18,
                 master_mix_reservoir['A1'],
                 pcr_wells,
                 new_tip='once')

    # Step 2: 1 µL colony template -> every PCR well, mixing 3x after dispense.
    # Fresh tip per well to avoid cross-contaminating colonies.
    p20.reset_tipracks()
    p20.transfer(1,
                 colony_wells,
                 pcr_wells,
                 new_tip='always',
                 mix_after=(3, 10))

    # Step 3: 1 µL primer mix -> every PCR well (fresh tip per primer pair).
    p20.reset_tipracks()
    p20.transfer(1,
                 primer_wells,
                 pcr_wells,
                 new_tip='always')

    # Step 4: sealing and thermocycling (not simulated).
    protocol.comment(
        'Seal pcr_plate, thermocycle: 98°C 30 s; '
        '[98°C 10 s, 60°C 30 s, 72°C 30 s] × 30; 72°C 2 min; hold 4°C')