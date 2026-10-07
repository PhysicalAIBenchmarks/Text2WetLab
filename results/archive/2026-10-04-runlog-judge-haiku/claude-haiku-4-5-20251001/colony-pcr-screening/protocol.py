from opentrons import protocol_api

metadata = {
    'protocolName': 'Colony PCR Screening on OT-2',
    'author': 'Slowpoke',
    'description': 'Screen 96 transformant colonies by colony PCR on OT-2 following Slowpoke workflow',
    'apiLevel': '2.15'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware with specified labels
    colony_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='colony_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2, label='pcr_plate')
    master_mix_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='master_mix_reservoir')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='primer_plate')

    # Load tip racks
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Load pipettes
    p20 = protocol.get_instrument_by_name('p20_single_gen2')
    p300 = protocol.get_instrument_by_name('p300_single_gen2')

    # Assign tip racks
    p20.tip_racks = [tiprack_20]
    p300.tip_racks = [tiprack_300]

    # Dispense Q5 2x master mix to all 96 wells (5 µL per well)
    # 5 µL of 2x master mix achieves 1x final concentration in a 10 µL reaction
    p20.distribute(
        5,
        master_mix_reservoir[0],
        pcr_plate.wells(),
        new_tip='once'
    )

    # Transfer primer pairs from primer_plate to pcr_plate (3 µL per well)
    # Each well receives its corresponding primer pair for that colony position
    for primer_src, pcr_dest in zip(primer_plate.wells(), pcr_plate.wells()):
        p20.transfer(
            3,
            primer_src,
            pcr_dest,
            new_tip='always'
        )

    # Transfer colony template from colony_plate to pcr_plate (1 µL per well)
    for colony_src, pcr_dest in zip(colony_plate.wells(), pcr_plate.wells()):
        p20.transfer(
            1,
            colony_src,
            pcr_dest,
            new_tip='always'
        )

    # Manual steps that the robot cannot perform
    protocol.comment('Seal the PCR plate with foil or adhesive sealing film')
    protocol.comment('Transfer sealed plate to thermocycler and run PCR program: 98°C 2 min, then 30-35 cycles of [98°C 10 s, 50-72°C 15 s (adjust annealing temperature based on primer Tm), 72°C 15-20 s], final extension 72°C 2 min')
