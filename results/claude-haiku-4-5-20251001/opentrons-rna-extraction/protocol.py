from opentrons import protocol_api

metadata = {
    'protocolName': 'Magnetic Bead RNA Extraction (48 samples)',
    'author': 'Opentrons',
    'description': 'OT-2in-house protocol for automated RNA extraction using magnetic beads',
    'apiLevel': '2.15'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    waste_plate = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', 1)
    tiprack_200_1 = protocol.load_labware('opentrons_96_filtertiprack_200ul', 2)
    tiprack_200_2 = protocol.load_labware('opentrons_96_filtertiprack_200ul', 3)

    magmod = protocol.load_module('magnetic module', 4)
    mag_plate = magmod.load_labware('usascientific_96_wellplate_2.4ml_deep')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 5)

    tempdeck = protocol.load_module('tempdeck', 6)
    elution_plate = tempdeck.load_labware('thermo_96_wellplate_200ul')

    sample_rack_1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 10)
    sample_rack_2 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 7)

    tiprack_1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', 11)

    # Load pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tiprack_1000])
    p300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[tiprack_200_1, tiprack_200_2])

    # Set temperature module to 4°C
    tempdeck.set_temperature(4)

    # Define target wells (odd columns: A, C, E, G of 96-well plate)
    # 4 columns × 12 rows = 48 samples
    sample_cols = ['A', 'C', 'E', 'G']
    target_wells = [f'{col}{row}' for col in sample_cols for row in range(1, 13)]

    # Reagent locations in reservoir
    magnetic_beads = reservoir.columns()[1]  # Column 2
    elution_buffer = reservoir.columns()[3]  # Column 4
    isopropanol = reservoir.columns()[5:7]  # Columns 6-7
    ethanol_70 = reservoir.columns()[8:12]  # Columns 9-12

    # ===== STEP 1: Transfer samples from racks to magnetic plate =====
    protocol.comment("Step 1: Transferring samples to magnetic plate")

    # Samples 1-24 from rack 1
    for i, sample_well in enumerate(sample_rack_1.wells()):
        target_well = mag_plate[target_wells[i]]
        p1000.pick_up_tip()
        p1000.aspirate(250, sample_well)
        p1000.dispense(250, target_well)
        p1000.drop_tip()

    # Samples 25-48 from rack 2
    for i, sample_well in enumerate(sample_rack_2.wells()):
        target_well = mag_plate[target_wells[24 + i]]
        p1000.pick_up_tip()
        p1000.aspirate(250, sample_well)
        p1000.dispense(250, target_well)
        p1000.drop_tip()

    # ===== STEP 2: Add isopropanol =====
    protocol.comment("Step 2: Adding isopropanol")
    for i, target_well_name in enumerate(target_wells):
        iso_col = isopropanol[i % len(isopropanol)][0]
        p300.pick_up_tip()
        p300.aspirate(250, iso_col)
        p300.dispense(250, mag_plate[target_well_name])
        p300.drop_tip()

    # ===== STEP 3: Add magnetic beads =====
    protocol.comment("Step 3: Adding magnetic beads")
    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(40, magnetic_beads[0])
        p300.dispense(40, mag_plate[target_well_name])
        p300.drop_tip()

    # ===== STEP 4: Mix by pipetting 5 times =====
    protocol.comment("Step 4: Mixing by pipetting 5 times")
    for target_well_name in target_wells:
        p300.pick_up_tip()
        for _ in range(5):
            p300.aspirate(200, mag_plate[target_well_name])
            p300.dispense(200, mag_plate[target_well_name])
        p300.drop_tip()

    # ===== STEP 5: Incubate 5 minutes at room temperature =====
    protocol.comment("Step 5: Incubating 5 minutes at room temperature")
    protocol.delay(minutes=5)

    # ===== STEP 6: Activate magnetic module for 4 minutes =====
    protocol.comment("Step 6: Activating magnetic module for 4 minutes")
    magmod.engage(height_from_base=13.15)
    protocol.delay(minutes=4)

    # ===== STEP 7: Remove supernatant =====
    protocol.comment("Step 7: Removing supernatant")
    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(500, mag_plate[target_well_name])
        waste_well = waste_plate.wells()[i % 96]
        p300.dispense(500, waste_well)
        p300.drop_tip()

    # ===== STEP 8: First ethanol wash =====
    protocol.comment("Step 8: Adding first 500µL ethanol wash")
    for i, target_well_name in enumerate(target_wells):
        eth_col = ethanol_70[i % len(ethanol_70)][0]
        p300.pick_up_tip()
        p300.aspirate(500, eth_col)
        p300.dispense(500, mag_plate[target_well_name])
        p300.drop_tip()

    # Incubate briefly with magnet engaged
    protocol.delay(seconds=30)

    # Remove first ethanol wash
    protocol.comment("Removing first ethanol wash")
    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(500, mag_plate[target_well_name])
        waste_well = waste_plate.wells()[(48 + i) % 96]
        p300.dispense(500, waste_well)
        p300.drop_tip()

    # ===== STEP 9: Second ethanol wash =====
    protocol.comment("Step 9: Adding second 500µL ethanol wash")
    for i, target_well_name in enumerate(target_wells):
        eth_col = ethanol_70[i % len(ethanol_70)][0]
        p300.pick_up_tip()
        p300.aspirate(500, eth_col)
        p300.dispense(500, mag_plate[target_well_name])
        p300.drop_tip()

    # Incubate briefly with magnet engaged
    protocol.delay(seconds=30)

    # Remove second ethanol wash
    protocol.comment("Removing second ethanol wash")
    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(500, mag_plate[target_well_name])
        waste_well = waste_plate.wells()[(96 + i) % 96]
        p300.dispense(500, waste_well)
        p300.drop_tip()

    # ===== STEP 10: Air dry for 4 minutes =====
    protocol.comment("Step 10: Air drying for 4 minutes")
    protocol.delay(minutes=4)

    # ===== STEP 11: Turn off magnetic module and add elution buffer =====
    protocol.comment("Step 11: Disengaging magnetic module and adding elution buffer")
    magmod.disengage()

    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(100, elution_buffer[0])
        p300.dispense(100, mag_plate[target_well_name])
        p300.drop_tip()

    # ===== STEP 12: Incubate 30 seconds =====
    protocol.comment("Step 12: Incubating for 30 seconds")
    protocol.delay(seconds=30)

    # ===== STEP 13: Engage magnetic module for 90 seconds =====
    protocol.comment("Step 13: Engaging magnetic module for 90 seconds")
    magmod.engage(height_from_base=13.15)
    protocol.delay(seconds=90)

    # ===== STEP 14: Transfer eluate to elution plate =====
    protocol.comment("Step 14: Transferring eluate to temperature-controlled elution plate")
    for i, target_well_name in enumerate(target_wells):
        p300.pick_up_tip()
        p300.aspirate(100, mag_plate[target_well_name])
        # Transfer to corresponding odd column in elution plate
        col_letter = target_wells[i][0]
        row_num = int(target_wells[i][1:])
        elution_well = f'{col_letter}{row_num}'
        p300.dispense(100, elution_plate[elution_well])
        p300.drop_tip()

    # ===== STEP 15: Disengage magnetic module =====
    protocol.comment("Step 15: Disengaging magnetic module")
    magmod.disengage()

    protocol.comment("Protocol complete!")
