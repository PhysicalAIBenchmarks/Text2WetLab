"""
SARS-CoV-2 viral RNA extraction with magnetic beads on an Opentrons OT-2.

Implementation of the "OT-2 in-house" protocol described in:
    Lazaro-Perona F, Rodriguez-Antolin C, et al. (2021) Evaluation of two
    automated low-cost RNA extraction protocols for SARS-CoV-2 detection.
    PLoS ONE 16(2): e0246302. doi:10.1371/journal.pone.0246302

Per sample (paper, Table 1 and "OT-2 in-house protocol"):
    1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample
       in a deep-well plate; mix 5x by pipetting; incubate 5 min at RT.
    2. Engage the GEN1 magnetic module, 4 min.
    3. Collect and discard the supernatant.
    4. Add 500 uL 70% ethanol; collect and discard.
    5. Add 500 uL 70% ethanol; collect and discard.
    6. Air dry 4 min.
    7. Disengage the magnet; add 100 uL elution buffer.
    8. After 30 s engage the magnet.
    9. After 90 s collect the eluate into a 96-well microtiter plate (4 C).

Deck layout (fixed by the operator):
    1   waste deep-well plate (supernatant and washes)
    2,3,9  200 uL filter tips (p300 multi)
    4   Magnetic Module GEN1 + USA Scientific 2.4 mL deep-well extraction plate
    5   NEST 12-channel reservoir:  col 2 beads | col 4 elution buffer |
                                    cols 6-7 isopropanol | cols 9-12 70% ethanol
    6   Temperature Module GEN1 + Thermo 96-well 200 uL elution plate (4 C)
    10  samples 1-24  (2 mL tubes)
    7   samples 25-48 (2 mL tubes)
    11  1000 uL filter tips (p1000 single)

The 48 samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the extraction
plate; sample n goes to well n of those columns (A1..H1 = samples 1-8,
A3..H3 = samples 9-16, ...). Each eluate is recovered into the same well
position of the elution plate on the temperature module.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'SARS-CoV-2 RNA extraction, magnetic beads, 48 samples (OT-2 in-house)',
    'author': 'Implementation of Lazaro-Perona et al. 2021, PLoS ONE 16(2):e0246302',
    'description': 'Isopropanol/bead binding, 2x 70% ethanol washes, 100 uL elution',
    'apiLevel': '2.9',
}

# ----------------------------------------------------------------------------
# Protocol parameters (from the paper)
# ----------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]       # odd columns of the extraction plate

BEAD_VOL = 40            # uL magnetic beads per sample
ISOPROPANOL_VOL = 250    # uL isopropanol per sample
SAMPLE_VOL = 250         # uL inactivated sample per sample
BINDING_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL   # 540 uL supernatant
WASH_VOL = 500           # uL 70% ethanol per wash
ELUTION_VOL = 100        # uL elution buffer

MIX_REPEATS_BINDING = 5  # "Mix by pipetting five times"
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_PRE_MAGNET_SEC = 30
ELUTION_ON_MAGNET_SEC = 90
ELUTION_TEMP_C = 4

TIP200_MAX = 200         # 200 uL filter tips on the p300 multi
AIR_GAP = 20             # uL air gap for alcohol transfers (volatile, drippy)


def split_volume(total, max_per_transfer):
    """Split `total` into the fewest equal transfers that fit the tip."""
    n = int(-(-total // max_per_transfer))  # ceil
    return [total / n] * n


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------------
    # Labware, modules, pipettes
    # ------------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')

    tips200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot,
                              '200 uL filter tips')
        for slot in ['2', '3', '9']
    ]
    tips1000 = [
        protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11',
                              '1000 uL filter tips')
    ]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5',
                                      'reagent reservoir')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul',
                                          'elution plate')

    samples_rack_a = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    samples_rack_b = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ------------------------------------------------------------------------
    # Reagents in the reservoir (slot 5)
    # ------------------------------------------------------------------------
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    # 6 columns x 8 wells x 250 uL = 12 mL isopropanol -> split over 2 wells
    isopropanol = {1: 'A6', 3: 'A6', 5: 'A6', 7: 'A7', 9: 'A7', 11: 'A7'}
    # 6 columns x 8 wells x 500 uL = 24 mL per wash -> 2 wells per wash
    ethanol_wash1 = {1: 'A9', 3: 'A9', 5: 'A9', 7: 'A10', 9: 'A10', 11: 'A10'}
    ethanol_wash2 = {1: 'A11', 3: 'A11', 5: 'A11', 7: 'A12', 9: 'A12', 11: 'A12'}

    # Column handles for the 8-channel pipette (well A of each column)
    mag_cols = {c: mag_plate.wells_by_name()['A%d' % c] for c in SAMPLE_COLUMNS}
    elution_cols = {c: elution_plate.wells_by_name()['A%d' % c]
                    for c in SAMPLE_COLUMNS}
    # Waste: supernatant into the same odd column, both ethanol washes into
    # the adjacent even column (540 uL and 1000 uL, both < 2.4 mL).
    waste_supernatant = {c: waste_plate.wells_by_name()['A%d' % c]
                         for c in SAMPLE_COLUMNS}
    waste_wash = {c: waste_plate.wells_by_name()['A%d' % (c + 1)]
                  for c in SAMPLE_COLUMNS}

    # Sample tubes (column-major: A1, B1, C1, D1, A2, ...) and destinations
    sample_tubes = (samples_rack_a.wells() + samples_rack_b.wells())[:NUM_SAMPLES]
    sample_wells = []
    for c in SAMPLE_COLUMNS:
        sample_wells += mag_plate.columns_by_name()[str(c)]
    sample_wells = sample_wells[:NUM_SAMPLES]

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------
    def add_reagent(source, dest_col, volume, air_gap=0, mix_source=None):
        """Dispense `volume` of a reagent into a column from above the liquid
        (no contact with the well contents), using the tip already on m300."""
        for v in split_volume(volume, TIP200_MAX - air_gap):
            if mix_source:
                m300.mix(mix_source[0], mix_source[1], source.bottom(2))
            m300.aspirate(v, source.bottom(2))
            if air_gap:
                m300.air_gap(air_gap)
            m300.dispense(v + air_gap, dest_col.top(-5))
            m300.blow_out(dest_col.top(-5))

    def remove_to_waste(src_col, waste_col, volume):
        """Slowly aspirate `volume` from the bottom of a column (beads held on
        the magnet) and discard it into the waste plate. Fresh tips per column."""
        m300.pick_up_tip()
        for v in split_volume(volume, TIP200_MAX):
            m300.aspirate(v, src_col.bottom(0.5), rate=0.5)
            m300.dispense(v, waste_col.top(-5))
            m300.blow_out(waste_col.top(-5))
        m300.drop_tip()

    # ------------------------------------------------------------------------
    # Start: magnet off, elution plate cooling to 4 C
    # ------------------------------------------------------------------------
    protocol.comment('--- Start: magnet disengaged, cooling elution plate to %d C' % ELUTION_TEMP_C)
    mag_mod.disengage()
    temp_mod.start_set_temperature(ELUTION_TEMP_C)

    # ------------------------------------------------------------------------
    # Step 1a: 40 uL magnetic beads into each sample column
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 1a: %d uL magnetic beads per well' % BEAD_VOL)
    m300.pick_up_tip()
    # Resuspend the beads in the reservoir before the first aspiration
    m300.mix(10, 150, beads.bottom(2))
    for c in SAMPLE_COLUMNS:
        # keep beads homogeneous between columns
        add_reagent(beads, mag_cols[c], BEAD_VOL, mix_source=(3, 150))
    m300.drop_tip()

    # ------------------------------------------------------------------------
    # Step 1b: 250 uL isopropanol into each sample column
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 1b: %d uL isopropanol per well' % ISOPROPANOL_VOL)
    m300.pick_up_tip()
    for c in SAMPLE_COLUMNS:
        add_reagent(reservoir.wells_by_name()[isopropanol[c]], mag_cols[c],
                    ISOPROPANOL_VOL, air_gap=AIR_GAP)
    m300.drop_tip()

    # ------------------------------------------------------------------------
    # Step 1c: 250 uL inactivated sample, mixed 5x, one tip per sample
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 1c: %d uL inactivated sample per well, mix %dx'
                     % (SAMPLE_VOL, MIX_REPEATS_BINDING))
    for i, (tube, well) in enumerate(zip(sample_tubes, sample_wells), start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        # Mix beads + isopropanol + sample (540 uL total) by pipetting 5 times
        p1000.mix(MIX_REPEATS_BINDING, 300, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-5)
        p1000.drop_tip()

    # ------------------------------------------------------------------------
    # Step 1d: 5 min binding incubation at room temperature
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 1d: incubate %d min at room temperature' % BINDING_INCUBATION_MIN)
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ------------------------------------------------------------------------
    # Step 2: engage the GEN1 magnetic module, 4 min
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 2: engage magnet, %d min' % MAGNET_BINDING_MIN)
    mag_mod.engage()  # labware default height for the 2.4 mL deep-well plate
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # ------------------------------------------------------------------------
    # Step 3: collect and discard the supernatant (540 uL)
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 3: remove %d uL supernatant to waste' % BINDING_VOL)
    for c in SAMPLE_COLUMNS:
        remove_to_waste(mag_cols[c], waste_supernatant[c], BINDING_VOL)

    # ------------------------------------------------------------------------
    # Steps 4 and 5: two washes with 500 uL 70% ethanol (magnet stays engaged)
    # ------------------------------------------------------------------------
    for wash_no, ethanol in ((1, ethanol_wash1), (2, ethanol_wash2)):
        protocol.comment('--- Step %d: wash %d, add %d uL 70%% ethanol'
                         % (3 + wash_no, wash_no, WASH_VOL))
        m300.pick_up_tip()
        for c in SAMPLE_COLUMNS:
            add_reagent(reservoir.wells_by_name()[ethanol[c]], mag_cols[c],
                        WASH_VOL, air_gap=AIR_GAP)
        m300.drop_tip()

        protocol.comment('--- Step %d: wash %d, remove %d uL ethanol to waste'
                         % (3 + wash_no, wash_no, WASH_VOL))
        for c in SAMPLE_COLUMNS:
            remove_to_waste(mag_cols[c], waste_wash[c], WASH_VOL)

    # ------------------------------------------------------------------------
    # Step 6: air dry the beads 4 min (magnet still engaged)
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 6: air dry beads %d min' % AIR_DRY_MIN)
    protocol.delay(minutes=AIR_DRY_MIN)

    # ------------------------------------------------------------------------
    # Step 7: disengage magnet, add 100 uL elution buffer and resuspend beads
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 7: disengage magnet, %d uL elution buffer, resuspend beads'
                     % ELUTION_VOL)
    mag_mod.disengage()
    for c in SAMPLE_COLUMNS:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, mag_cols[c].bottom(2))
        m300.mix(10, 80, mag_cols[c].bottom(1))
        m300.blow_out(mag_cols[c].top(-5))
        m300.touch_tip(mag_cols[c], v_offset=-5)
        m300.drop_tip()

    # ------------------------------------------------------------------------
    # Step 8: after 30 s engage the magnet
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 8: wait %d s, then engage magnet' % ELUTION_PRE_MAGNET_SEC)
    protocol.delay(seconds=ELUTION_PRE_MAGNET_SEC)
    mag_mod.engage()

    # ------------------------------------------------------------------------
    # Step 9: after 90 s transfer the eluate to the elution plate at 4 C
    # ------------------------------------------------------------------------
    protocol.comment('--- Step 9: wait %d s on magnet, then recover eluates to the elution plate'
                     % ELUTION_ON_MAGNET_SEC)
    protocol.delay(seconds=ELUTION_ON_MAGNET_SEC)
    temp_mod.await_temperature(ELUTION_TEMP_C)
    for c in SAMPLE_COLUMNS:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, mag_cols[c].bottom(0.5), rate=0.3)
        m300.dispense(ELUTION_VOL, elution_cols[c].bottom(2))
        m300.blow_out(elution_cols[c].top(-2))
        m300.touch_tip(elution_cols[c], v_offset=-2)
        m300.drop_tip()

    # ------------------------------------------------------------------------
    # End: magnet off; elution plate kept at 4 C until the operator unloads it
    # ------------------------------------------------------------------------
    mag_mod.disengage()
    protocol.comment('--- Done: %d eluates (%d uL) in the odd columns of the elution plate at %d C'
                     % (NUM_SAMPLES, ELUTION_VOL, ELUTION_TEMP_C))
