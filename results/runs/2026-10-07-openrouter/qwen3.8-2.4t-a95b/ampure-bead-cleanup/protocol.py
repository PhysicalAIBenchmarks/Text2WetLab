metadata = {'apiLevel': '2.13'}


def run(protocol):
    # Labware
    sample_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 1, label='sample_plate')
    beads_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 2, label='beads_reservoir')
    ethanol_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 3, label='ethanol_reservoir')
    water_reservoir = protocol.load_labware(
        'nest_1_reservoir_195ml', 4, label='water_reservoir')
    waste = protocol.load_labware(
        'nest_1_reservoir_195ml', 5, label='waste')
    elution_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 6, label='elution_plate')

    # Tip racks
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    sample_wells = sample_plate.wells()    # A1:H12, row-major
    elution_wells = elution_plate.wells()  # A1:H12, row-major (pairs in order)
    waste_well = [waste['A1']] * len(sample_wells)
    ethanol_source = [ethanol_reservoir['A1']] * len(sample_wells)
    beads_source = beads_reservoir['A1']
    water_source = water_reservoir['A1']

    # Step 1: add 40 uL AMPure XP beads to each sample well, mix 10x
    protocol.comment('Step 1: Adding 40 uL AMPure XP beads to sample plate')
    for well in sample_wells:
        p300.transfer(40, beads_source, well,
                      mix_after=(10, 40), new_tip='always')
    p300.reset_tipracks()

    # Step 2: incubate
    protocol.comment(
        'Step 2: Incubate sample_plate 5 min at room temperature '
        '(beads bind DNA)')

    # Step 3: engage magnet
    protocol.comment(
        'Step 3: Engage magnetic module; wait 5 min until solution clears')

    # Step 4: remove 90 uL supernatant from each sample well to waste
    protocol.comment('Step 4: Removing 90 uL supernatant to waste')
    p300.transfer(90, sample_wells, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 5: first 200 uL 80% ethanol wash
    protocol.comment('Step 5: Adding 200 uL 80% ethanol (wash 1)')
    p300.transfer(200, ethanol_source, sample_wells, new_tip='always')
    p300.reset_tipracks()

    # Step 6: remove 200 uL ethanol waste 1
    protocol.comment('Step 6: Removing 200 uL ethanol waste 1')
    p300.transfer(200, sample_wells, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 7: second 200 uL 80% ethanol wash
    protocol.comment('Step 7: Adding 200 uL 80% ethanol (wash 2)')
    p300.transfer(200, ethanol_source, sample_wells, new_tip='always')
    p300.reset_tipracks()

    # Step 8: remove 200 uL ethanol waste 2
    protocol.comment('Step 8: Removing 200 uL ethanol waste 2')
    p300.transfer(200, sample_wells, waste_well, new_tip='always')
    p300.reset_tipracks()

    # Step 9: air dry
    protocol.comment(
        'Step 9: Air dry beads 5 min at room temperature (magnet engaged); '
        'beads should appear matte not shiny')

    # Step 10: disengage magnet
    protocol.comment('Step 10: Disengage magnetic module')

    # Step 11: elute in 50 uL nuclease-free water, mix 10x
    protocol.comment('Step 11: Adding 50 uL nuclease-free water to elute')
    for well in sample_wells:
        p300.transfer(50, water_source, well,
                      mix_after=(10, 50), new_tip='always')
    p300.reset_tipracks()

    # Step 12: incubate and re-engage magnet
    protocol.comment(
        'Step 12: Incubate sample_plate 2 min at room temperature; '
        'then re-engage magnetic module 5 min')

    # Step 13: transfer 45 uL cleaned DNA to elution plate
    protocol.comment('Step 13: Transferring 45 uL cleaned DNA to elution plate')
    p300.transfer(45, sample_wells, elution_wells, new_tip='always')
    p300.reset_tipracks()

    protocol.comment('AMPure XP cleanup complete.')
