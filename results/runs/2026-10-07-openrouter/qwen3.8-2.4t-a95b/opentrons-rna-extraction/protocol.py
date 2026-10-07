"""
Automated low-cost SARS-CoV-2 RNA extraction (in-house magnetic-bead protocol)
adapted from PLOS ONE 2021, doi:10.1371/journal.pone.0246302.

48 samples, processed in the odd columns (1, 3, 5, 7, 9, 11) of a deep-well
plate on the Magnetic Module (slot 4). Eluates are recovered into the same
columns of a 200 uL plate on the Temperature Module (slot 6) held at 4 degC.

Pipettes:
  left  - p1000_single_gen2 (sample transfer from tubes, 1 fresh tip / sample)
  right - p300_multi_gen2   (all plate-column work)

Tip discipline: any tip that aspirates from a sample well is used on that
column only (with the multi, each of the 8 tips touches exactly one well).
Reagent-dispensing tips are only reused while they never aspirate from a
sample well.
"""

metadata = {
    'apiLevel': '2.11',
    'protocolName': 'OT-2 magnetic-bead RNA extraction, 48 samples',
    'description': 'In-house bead-based SARS-CoV-2 RNA extraction (PLOS ONE '
                   '2021, doi:10.1371/journal.pone.0246302), 48 samples.',
}

# Odd plate columns (0-based column indices 0,2,4,6,8,10 == columns 1,3,5,7,9,11)
SAMPLE_COL_IDX = [0, 2, 4, 6, 8, 10]


def run(protocol):
    # ------------------------------------------------------------------ labware
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', '1',
                                  'waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')

    mag = protocol.load_module('magnetic module', '4')
    mag_plate = mag.load_labware('usascientific_96_wellplate_2.4ml_deep',
                                 label='sample/extraction plate')

    temp = protocol.load_module('tempdeck', '6')
    elution_plate = temp.load_labware('thermo_96_wellplate_200ul',
                                      label='elution plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5',
                                      'reagent reservoir')
    rack10 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    rack7 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    # ---------------------------------------------------------------- pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=[tips1000])
    p300m = protocol.load_instrument('p300_multi_gen2', 'right',
                                     tip_racks=tips200)

    # ------------------------------------------------------------- reagents
    beads = reservoir.columns()[1]          # reservoir column 2
    elution_buf = reservoir.columns()[3]    # reservoir column 4
    iso_cols = [reservoir.columns()[5], reservoir.columns()[6]]   # columns 6-7
    etoh_cols = reservoir.columns()[8:12]                         # columns 9-12

    sample_cols = [mag_plate.columns()[i] for i in SAMPLE_COL_IDX]
    waste_cols = [waste.columns()[i] for i in SAMPLE_COL_IDX]
    elution_cols = [elution_plate.columns()[i] for i in SAMPLE_COL_IDX]

    # Sample tube order: column-major over the two 24-position racks.
    # Samples 1-24  -> rack in slot 10 -> plate columns 1, 3, 5
    # Samples 25-48 -> rack in slot 7  -> plate columns 7, 9, 11
    tubes = rack10.wells()[:24] + rack7.wells()[:24]

    # -------------------------------------------------- step 1: initial state
    mag.disengage()
    temp.set_temperature(4)

    # ------------------------------------- steps 2-4: beads, isopropanol, sample
    # Step 2: 40 uL magnetic beads into every sample well (dispense-only tip).
    p300m.pick_up_tip()
    for col in sample_cols:
        p300m.transfer(40, beads, col, new_tip='never')
    p300m.drop_tip()

    # Step 3: 250 uL isopropanol into every sample well (dispense-only tip).
    p300m.pick_up_tip()
    for i, col in enumerate(sample_cols):
        p300m.transfer(250, iso_cols[i % 2], col, new_tip='never')
    p300m.drop_tip()

    # Step 4: 250 uL of each sample from its tube into its own well,
    # fresh tip per sample, mix by pipetting 5 times.
    for i, tube in enumerate(tubes):
        dest = sample_cols[i // 8][i % 8]   # column-major within odd columns
        p1000.pick_up_tip()
        p1000.transfer(250, tube, dest, new_tip='never', mix_after=(5, 250))
        p1000.drop_tip()

    # ----------------------------------------- step 5: incubate 5 min at RT
    protocol.delay(minutes=5, msg='Incubating 5 min at room temperature')

    # ------------------------------------------- step 6: engage magnet, 4 min
    mag.engage()
    protocol.delay(minutes=4, msg='Incubating 4 min on magnet')

    # ----------------------------------------- step 7: remove supernatant
    for i, col in enumerate(sample_cols):
        p300m.pick_up_tip()
        # ~540 uL total, in two 270 uL aspirates (p300 limit is 300 uL)
        p300m.transfer(270, col, waste_cols[i], new_tip='never')
        p300m.transfer(270, col, waste_cols[i], new_tip='never')
        p300m.drop_tip()

    # -------------------------------------- steps 8-9: two 70% ethanol washes
    for wash in range(2):
        # Dispense 500 uL ethanol (2 x 250 uL) into every sample well,
        # magnet stays engaged; dispense-only tip reused across columns.
        p300m.pick_up_tip()
        for i, col in enumerate(sample_cols):
            p300m.transfer(250, etoh_cols[i % 4], col, new_tip='never')
            p300m.transfer(250, etoh_cols[(i + 1) % 4], col, new_tip='never')
        p300m.drop_tip()

        # Remove ethanol with the magnet engaged (fresh tips per column).
        for i, col in enumerate(sample_cols):
            p300m.pick_up_tip()
            p300m.transfer(250, col, waste_cols[i], new_tip='never')
            p300m.transfer(250, col, waste_cols[i], new_tip='never')
            p300m.drop_tip()

    # -------------------------------------- step 10: air-dry beads 4 min
    protocol.delay(minutes=4, msg='Air-drying beads 4 min, magnet engaged')

    # --------------------------- step 11: disengage, resuspend in elution buf
    mag.disengage()
    for col in sample_cols:
        # Fresh tips per column: this tip mixes (aspirates) in the sample wells.
        p300m.pick_up_tip()
        p300m.transfer(100, elution_buf, col, new_tip='never')
        p300m.mix(5, 100, col[0])
        p300m.drop_tip()

    # ------------------------- step 12: wait 30 s, engage magnet, wait 90 s
    protocol.delay(seconds=30, msg='Waiting 30 s off magnet')
    mag.engage()
    protocol.delay(seconds=90, msg='Waiting 90 s on magnet')

    # ---------------- step 13: transfer 80 uL eluate to the 4 degC elution plate
    for i, col in enumerate(sample_cols):
        p300m.pick_up_tip()
        p300m.transfer(80, col, elution_cols[i], new_tip='never')
        p300m.drop_tip()

    # ---------------------------------------------- step 14: disengage magnet
    mag.disengage()
