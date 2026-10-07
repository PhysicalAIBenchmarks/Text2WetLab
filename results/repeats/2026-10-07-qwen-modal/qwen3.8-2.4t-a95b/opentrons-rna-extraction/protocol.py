metadata = {
    'protocolName': 'In-house OT-2 magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'author': 'Implemented from Lazaro-Perona et al. 2021 (doi:10.1371/journal.pone.0246302)',
    'description': 'Automated low-cost magnetic-bead RNA extraction on an OT-2: '
                   '40 uL beads + 250 uL isopropanol + 250 uL sample, 5 min RT '
                   'incubation, magnetic capture, 2x 500 uL 70% ethanol washes, '
                   '4 min dry, elution in 100 uL buffer, recovery of 80 uL eluate '
                   'at 4 C. 48 samples in the odd columns of the deep-well plate.',
    'apiLevel': '2.11',
}


def run(protocol):
    # ------------------------------------------------------------------
    # Deck layout (fixed, as loaded by the operator)
    # ------------------------------------------------------------------
    # Slot 1: waste plate for removed supernatant and washes
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', label='Waste plate')
    # Slots 2, 3, 9: 200 uL filter tips (for the multi-channel pipette)
    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ('2', '3', '9')
    ]
    # Slot 4: Magnetic Module GEN1 with the sample/extraction plate
    magdeck = protocol.load_module('magnetic module', '4')
    mag_plate = magdeck.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', label='Sample/extraction plate')
    # Slot 5: reagent reservoir
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5')
    # Slot 6: Temperature Module GEN1 with the elution plate, held at 4 C
    tempdeck = protocol.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware(
        'thermo_96_wellplate_200ul', label='Elution plate')
    # Slots 10 and 7: inactivated samples in 2 mL tubes
    tuberack_10 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        label='Samples 1-24')
    tuberack_7 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        label='Samples 25-48')
    # Slot 11: 1000 uL filter tips (for the single-channel pipette)
    tiprack_1000 = protocol.load_labware(
        'opentrons_96_filtertiprack_1000ul', '11')

    # Slot 12: fixed trash (used implicitly by drop_tip)

    # Pipettes
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=[tiprack_1000])
    p300_multi = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks_200)

    # ------------------------------------------------------------------
    # Well maps
    # ------------------------------------------------------------------
    # The 48 samples sit in the odd columns of the extraction plate.
    odd_column_names = ['1', '3', '5', '7', '9', '11']
    mag_columns = [mag_plate.columns_by_name()[c] for c in odd_column_names]
    sample_wells = [well for column in mag_columns for well in column]

    # Samples 1-24 in slot 10, samples 25-48 in slot 7 (column-major order).
    sample_tubes = tuberack_10.wells()[:24] + tuberack_7.wells()[:24]

    # Each sample's waste (supernatant + both ethanol washes) goes to its
    # own well of the waste plate; samples 1-8 -> waste column 1, etc.
    waste_wells = waste_plate.wells()[:48]
    waste_columns = [waste_plate.columns()[i] for i in range(len(mag_columns))]

    # The eluate of each sample well goes to the matching column of the
    # elution plate on the temperature module.
    elution_columns = [elution_plate.columns_by_name()[c]
                       for c in odd_column_names]

    # Reservoir reagent positions (slot 5)
    bead_channel = reservoir.wells_by_name()['A2']        # magnetic beads
    elution_buffer_channel = reservoir.wells_by_name()['A4']  # elution buffer
    ipa_channels = [reservoir.wells_by_name()['A6'],      # isopropanol
                    reservoir.wells_by_name()['A7']]
    etoh_channels = {'wash_1': [reservoir.wells_by_name()['A9'],   # ethanol
                                reservoir.wells_by_name()['A10']],
                     'wash_2': [reservoir.wells_by_name()['A11'],
                                reservoir.wells_by_name()['A12']]}

    # ------------------------------------------------------------------
    # Step 1: magnet disengaged and elution plate chilled before any
    # eluate can reach it
    # ------------------------------------------------------------------
    protocol.comment('Step 1: disengage magnet, cool elution plate to 4 C')
    magdeck.disengage()
    tempdeck.set_temperature(4)

    # ------------------------------------------------------------------
    # Step 2: 40 uL magnetic beads into every sample well.
    # Dispensed only (never aspirated from a sample well), so one tip
    # column serves all six plate columns.
    # ------------------------------------------------------------------
    protocol.comment('Step 2: add 40 uL magnetic beads to each sample well')
    p300_multi.pick_up_tip()
    for column in mag_columns:
        p300_multi.aspirate(40, bead_channel)
        p300_multi.dispense(40, column[0])
    p300_multi.drop_tip()

    # ------------------------------------------------------------------
    # Step 3: 250 uL isopropanol into every sample well (dispense-only,
    # one tip column for all six plate columns). Reservoir channels 6-7
    # supply three plate columns each. The 200 uL tips limit each
    # aspiration to 200 uL, so the 250 uL are added as 150 + 100 uL.
    # ------------------------------------------------------------------
    protocol.comment('Step 3: add 250 uL isopropanol to each sample well')
    p300_multi.pick_up_tip()
    for i, column in enumerate(mag_columns):
        source = ipa_channels[i // 3]
        for volume in (150, 100):
            p300_multi.aspirate(volume, source)
            p300_multi.dispense(volume, column[0])
    p300_multi.drop_tip()

    # ------------------------------------------------------------------
    # Step 4: 250 uL of each sample into its own well, a fresh tip per
    # sample, mixed by pipetting 5 times.
    # ------------------------------------------------------------------
    protocol.comment('Step 4: add 250 uL of each sample, mix 5 times')
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(250, tube)
        p1000.dispense(250, well)
        p1000.mix(5, 250, well)
        p1000.drop_tip()

    # ------------------------------------------------------------------
    # Step 5: incubate 5 min at room temperature
    # ------------------------------------------------------------------
    protocol.comment('Step 5: incubate 5 min at room temperature')
    protocol.delay(minutes=5)

    # ------------------------------------------------------------------
    # Step 6: engage the magnet and wait 4 min
    # ------------------------------------------------------------------
    protocol.comment('Step 6: engage magnet, wait 4 min')
    magdeck.engage()
    protocol.delay(minutes=4)

    # ------------------------------------------------------------------
    # Step 7: remove the supernatant (~540 uL) to the waste plate,
    # magnet engaged, one fresh tip per sample well.
    # ------------------------------------------------------------------
    protocol.comment('Step 7: remove ~540 uL supernatant to waste')
    for well, waste_well in zip(sample_wells, waste_wells):
        p1000.pick_up_tip()
        p1000.aspirate(540, well)
        p1000.dispense(540, waste_well)
        p1000.drop_tip()

    # ------------------------------------------------------------------
    # Steps 8-9: two 500 uL 70% ethanol washes, magnet engaged.
    # Ethanol is dispensed with one tip column (dispense-only); it is
    # removed with a fresh tip column per plate column.
    # ------------------------------------------------------------------
    for wash_number, wash_name in ((8, 'wash_1'), (9, 'wash_2')):
        protocol.comment(
            f'Step {wash_number}: 500 uL 70% ethanol wash ({wash_name})')

        # Add 500 uL ethanol as 200 + 200 + 100 uL passes (200 uL tip
        # limit); reservoir channels 9-10 serve wash 1, channels 11-12
        # serve wash 2 (3 plate columns each).
        p300_multi.pick_up_tip()
        for i, column in enumerate(mag_columns):
            source = etoh_channels[wash_name][i // 3]
            for volume in (200, 200, 100):
                p300_multi.aspirate(volume, source)
                p300_multi.dispense(volume, column[0])
        p300_multi.drop_tip()

        # Remove the ethanol to the waste plate (fresh tips per column).
        for column, waste_column in zip(mag_columns, waste_columns):
            p300_multi.pick_up_tip()
            for volume in (200, 200, 100):
                p300_multi.aspirate(volume, column[0])
                p300_multi.dispense(volume, waste_column[0])
            p300_multi.drop_tip()

    # ------------------------------------------------------------------
    # Step 10: air-dry the beads for 4 min with the magnet engaged
    # ------------------------------------------------------------------
    protocol.comment('Step 10: air-dry beads 4 min, magnet engaged')
    protocol.delay(minutes=4)

    # ------------------------------------------------------------------
    # Step 11: disengage the magnet, add 100 uL elution buffer and mix
    # to resuspend the beads. Fresh tips per plate column because mixing
    # aspirates from the sample wells.
    # ------------------------------------------------------------------
    protocol.comment('Step 11: disengage magnet, add 100 uL elution buffer, '
                     'mix to resuspend beads')
    magdeck.disengage()
    for column in mag_columns:
        p300_multi.pick_up_tip()
        p300_multi.aspirate(100, elution_buffer_channel)
        p300_multi.dispense(100, column[0])
        p300_multi.mix(10, 100, column[0])
        p300_multi.drop_tip()

    # ------------------------------------------------------------------
    # Step 12: wait 30 s, engage the magnet, wait 90 s
    # ------------------------------------------------------------------
    protocol.comment('Step 12: wait 30 s, engage magnet, wait 90 s')
    protocol.delay(seconds=30)
    magdeck.engage()
    protocol.delay(seconds=90)

    # ------------------------------------------------------------------
    # Step 13: transfer 80 uL of each eluate to its own well of the
    # elution plate kept at 4 C (fresh tips per plate column).
    # ------------------------------------------------------------------
    protocol.comment('Step 13: transfer 80 uL eluate to the 4 C elution plate')
    for column, elution_column in zip(mag_columns, elution_columns):
        p300_multi.pick_up_tip()
        p300_multi.aspirate(80, column[0])
        p300_multi.dispense(80, elution_column[0])
        p300_multi.drop_tip()

    # ------------------------------------------------------------------
    # Step 14: disengage the magnet at the end of the run
    # ------------------------------------------------------------------
    protocol.comment('Step 14: disengage magnet')
    magdeck.disengage()
