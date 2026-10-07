from opentrons import protocol_api

metadata = {
    'apiLevel': '2.15',
    'protocolName': 'AMPure XP Cleanup',
    'author': 'Claude'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    sample_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware('nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    # Load pipette and tiprack
    tiprack_p300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_p300])

    # Get all sample wells (A1 through H12 in row-major order)
    sample_wells = [well for row in sample_plate.rows() for well in row]
    elution_wells = [well for row in elution_plate.rows() for well in row]

    # Step 1: Add 40 µL beads to each well, mix 10 times
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(40, beads_reservoir['A1'])
        p300.dispense(40, well)
        p300.mix(10, 20, well)
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 2: Incubate 5 min at room temperature
    protocol.comment('Incubate sample_plate 5 min at room temperature (beads bind DNA)')

    # Step 3: Engage magnetic module, wait 5 min
    protocol.comment('Engage magnetic module; wait 5 min until solution clears')

    # Step 4: Remove 90 µL supernatant
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(90, well)
        p300.dispense(90, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 5: Add 200 µL ethanol (wash 1)
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(200, ethanol_reservoir['A1'])
        p300.dispense(200, well)
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 6: Remove 200 µL ethanol waste 1
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(200, well)
        p300.dispense(200, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 7: Add 200 µL ethanol (wash 2)
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(200, ethanol_reservoir['A1'])
        p300.dispense(200, well)
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 8: Remove 200 µL ethanol waste 2
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(200, well)
        p300.dispense(200, waste['A1'])
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 9: Air dry beads 5 min
    protocol.comment('Air dry beads 5 min at room temperature (magnet engaged); beads should appear matte not shiny')

    # Step 10: Disengage magnetic module
    protocol.comment('Disengage magnetic module')

    # Step 11: Add 50 µL water, mix 10 times
    for well in sample_wells:
        p300.pick_up_tip()
        p300.aspirate(50, water_reservoir['A1'])
        p300.dispense(50, well)
        p300.mix(10, 20, well)
        p300.drop_tip()

    p300.reset_tipracks()

    # Step 12: Incubate 2 min, then re-engage magnet 5 min
    protocol.comment('Incubate sample_plate 2 min at room temperature; then re-engage magnetic module 5 min')

    # Step 13: Transfer 45 µL cleaned DNA to elution plate
    for sample_well, elution_well in zip(sample_wells, elution_wells):
        p300.pick_up_tip()
        p300.aspirate(45, sample_well)
        p300.dispense(45, elution_well)
        p300.drop_tip()
