"""
Automated magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2.

Implementation of the "OT-2 in-house" protocol described in:
    Lazaro-Perona F, Rodriguez-Antolin C, et al. (2021) Evaluation of two
    automated low-cost RNA extraction protocols for SARS-CoV-2 detection.
    PLoS ONE 16(2): e0246302. doi:10.1371/journal.pone.0246302

Per well (48 samples, odd columns of the deep-well plate on the magnet):
    1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated
       sample, mixed by pipetting 5x, 5 min at room temperature.
    2. Magnet on for 4 min.
    3. Supernatant (540 uL) removed to the waste plate.
    4. 500 uL 70 % ethanol added, removed to waste.
    5. 500 uL 70 % ethanol added, removed to waste.
    6. Beads air-dried 4 min (magnet still on).
    7. Magnet off, 100 uL elution buffer added and beads resuspended.
    8. 30 s later the magnet is turned on.
    9. 90 s later the eluate is moved to the elution plate held at 4 C.

Deck layout (fixed by the operator):
    1   waste deep-well plate              usascientific_96_wellplate_2.4ml_deep
    2,3,9  200 uL filter tips (p300 multi) opentrons_96_filtertiprack_200ul
    4   Magnetic Module GEN1 + sample plate usascientific_96_wellplate_2.4ml_deep
    5   reagent reservoir                   nest_12_reservoir_15ml
    6   Temperature Module GEN1 + eluates   thermo_96_wellplate_200ul (custom)
    10  samples 1-24 (2 mL tubes)           opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
    7   samples 25-48 (2 mL tubes)          opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
    11  1000 uL filter tips (p1000 single)  opentrons_96_filtertiprack_1000ul
    12  fixed trash

Reservoir (slot 5): col 2 beads, col 4 elution buffer, cols 6-7 isopropanol,
cols 9-12 70 % ethanol.
"""

import math

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 magnetic-bead RNA extraction (48 samples, OT-2 in-house)',
    'author': 'Automated from Lazaro-Perona et al. 2021, PLoS ONE 16(2):e0246302',
    'description': 'Mag-Bind TotalPure NGS bead RNA extraction of 48 inactivated '
                   'nasopharyngeal samples with isopropanol binding, two 70 % '
                   'ethanol washes and 100 uL elution, on a GEN1 magnetic module.',
    'apiLevel': '2.13',
}

# --------------------------------------------------------------------------
# Protocol parameters (volumes in uL, times as noted) - taken from the paper
# --------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]      # odd columns of the magnet plate

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
BINDING_MIX_REPS = 5
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
ETHANOL_VOL = 500
NUM_WASHES = 2
AIR_DRY_MIN = 4
ELUTION_VOL = 100
ELUTION_INCUBATION_SEC = 30
ELUTION_MAGNET_SEC = 90
ELUTION_PLATE_TEMP_C = 4

# Reservoir map (slot 5, nest_12_reservoir_15ml, 15 mL per column)
BEAD_WELL = 'A2'
ELUTION_BUFFER_WELL = 'A4'
ISOPROPANOL_WELLS = ['A6', 'A7']            # 6 mL needed in each
ETHANOL_WELLS = {1: ['A9', 'A10'],          # wash 1: 12 mL needed in each
                 2: ['A11', 'A12']}         # wash 2: 12 mL needed in each

# Pipetting details
P300_MAX = 200           # 200 uL filter tips on the p300 multi
AIR_GAP = 20             # air gap after aspirating waste, keeps tips from dripping
# Bead pellet side on a GEN1 magnetic module: in each column pair (1-2, 3-4, ...)
# the magnet sits between the two columns, so beads in the odd columns pellet
# on the +x (right-hand) wall. Aspirate from the opposite (-x) wall.
PELLET_SIDE = 1
ASPIRATE_OFFSET_MM = 2.0
SUPERNATANT_ASPIRATE_RATE = 50   # uL/s - slow, keeps the pellet in place
ELUATE_ASPIRATE_RATE = 25        # uL/s - slower still for the 100 uL eluate


def split_volume(total, max_per_transfer):
    """Split `total` into the fewest near-equal integer transfers <= max."""
    n = int(math.ceil(total / float(max_per_transfer)))
    base, extra = divmod(int(round(total)), n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def run(protocol: protocol_api.ProtocolContext):

    # ----------------------------------------------------------------------
    # Labware, modules and pipettes
    # ----------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')

    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot,
                              '200 uL filter tips')
        for slot in ['2', '3', '9']
    ]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'sample / extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5',
                                      'reagent reservoir')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul',
                                          'elution plate')

    tuberack_a = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    tuberack_b = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    tiprack_1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul',
                                         '11', '1000 uL filter tips')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=[tiprack_1000])
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tipracks_200)

    # ----------------------------------------------------------------------
    # Well bookkeeping
    # ----------------------------------------------------------------------
    # Sample tubes: slot 10 holds samples 1-24, slot 7 holds 25-48, read
    # down the columns of each rack (A1, B1, C1, D1, A2, ...).
    sample_tubes = tuberack_a.wells() + tuberack_b.wells()
    sample_tubes = sample_tubes[:NUM_SAMPLES]

    # Sample wells: odd columns of the magnet plate, 8 wells per column,
    # filled top to bottom -> sample 1 in A1, sample 8 in H1, sample 9 in A3...
    sample_wells = []
    for col in SAMPLE_COLUMNS:
        sample_wells += mag_plate.columns_by_name()[str(col)]
    sample_wells = sample_wells[:NUM_SAMPLES]

    # Multichannel targets: the top (A) well of each used column
    mag_cols = [mag_plate.wells_by_name()['A%d' % c] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.wells_by_name()['A%d' % c]
                    for c in SAMPLE_COLUMNS]
    # Waste: binding supernatant goes to the matching odd column of the
    # waste plate (540 uL), both ethanol washes go to the neighbouring even
    # column (2 x 500 uL). Both stay well below the 2.4 mL well capacity.
    waste_sup_cols = [waste_plate.wells_by_name()['A%d' % c]
                      for c in SAMPLE_COLUMNS]
    waste_wash_cols = [waste_plate.wells_by_name()['A%d' % (c + 1)]
                       for c in SAMPLE_COLUMNS]

    def reservoir_source(wells, col_index):
        """First half of the sample columns from the first reservoir well,
        second half from the second (6 mL isopropanol / 12 mL ethanol each)."""
        half = int(math.ceil(len(SAMPLE_COLUMNS) / 2.0))
        return reservoir.wells_by_name()[wells[col_index // half]]

    def away_from_pellet(well, z=0.5):
        """Aspiration point near the well bottom on the wall opposite the
        bead pellet."""
        return well.bottom(z).move(Point(x=-PELLET_SIDE * ASPIRATE_OFFSET_MM))

    def on_pellet(well, z=1.0):
        """Point on the pellet side of the well, used to resuspend beads."""
        return well.bottom(z).move(Point(x=PELLET_SIDE * ASPIRATE_OFFSET_MM))

    # ----------------------------------------------------------------------
    # Helper operations (multichannel)
    # ----------------------------------------------------------------------
    def add_reagent_from_top(volume, source_for_col, label,
                             premix=None):
        """Dispense `volume` uL of a reagent into every sample column from
        above the liquid with a single set of tips (the tips never touch the
        sample wells, so no cross-contamination is possible)."""
        protocol.comment('Adding %d uL %s to each sample well' % (volume, label))
        m300.flow_rate.aspirate = 94
        m300.flow_rate.dispense = 94
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            src = source_for_col(i)
            if premix:
                m300.mix(premix[0], premix[1], src.bottom(2))
            for vol in split_volume(volume, P300_MAX):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dest.top(-5))
                m300.blow_out(dest.top(-5))
        m300.drop_tip()

    def remove_to_waste(volume, waste_cols, label, z=0.5):
        """Remove `volume` uL from each sample column (magnet engaged) to the
        waste plate, fresh tips for each column, aspirating slowly from the
        wall opposite the bead pellet."""
        protocol.comment('Removing %d uL %s from each column to the waste plate'
                         % (volume, label))
        m300.flow_rate.aspirate = SUPERNATANT_ASPIRATE_RATE
        m300.flow_rate.dispense = 94
        for src, waste in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume, P300_MAX - AIR_GAP):
                m300.aspirate(vol, away_from_pellet(src, z))
                m300.air_gap(AIR_GAP)
                m300.dispense(vol + AIR_GAP, waste.top(-5))
                m300.blow_out(waste.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94

    # ----------------------------------------------------------------------
    # Set-up: elution plate cooled to 4 C, magnet off
    # ----------------------------------------------------------------------
    protocol.comment('Cooling the elution plate to %d C and making sure the '
                     'magnet is disengaged' % ELUTION_PLATE_TEMP_C)
    temp_mod.start_set_temperature(ELUTION_PLATE_TEMP_C)
    mag_mod.disengage()

    # ----------------------------------------------------------------------
    # Step 1 - binding mix: beads, isopropanol, sample; mix 5x; 5 min RT
    # ----------------------------------------------------------------------
    protocol.comment('STEP 1: binding mix (40 uL beads + 250 uL isopropanol '
                     '+ 250 uL sample)')

    # 1a) 40 uL magnetic beads (resuspended in the reservoir before each draw)
    add_reagent_from_top(
        BEAD_VOL,
        lambda i: reservoir.wells_by_name()[BEAD_WELL],
        'magnetic beads (Mag-Bind TotalPure NGS)',
        premix=(5, 150))

    # 1b) 250 uL isopropanol (reservoir columns 6 and 7)
    add_reagent_from_top(
        ISOPROPANOL_VOL,
        lambda i: reservoir_source(ISOPROPANOL_WELLS, i),
        'isopropanol')

    # 1c) 250 uL inactivated sample, one fresh 1000 uL filter tip per sample,
    #     mixed by pipetting 5 times in the destination well
    protocol.comment('Transferring %d uL of each of the %d inactivated samples '
                     'and mixing %d times' % (SAMPLE_VOL, NUM_SAMPLES,
                                              BINDING_MIX_REPS))
    p1000.flow_rate.aspirate = 150
    p1000.flow_rate.dispense = 150
    mix_vol = SAMPLE_VOL + ISOPROPANOL_VOL   # 500 uL of the 540 uL in the well
    for n, (tube, well) in enumerate(zip(sample_tubes, sample_wells), start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(BINDING_MIX_REPS, mix_vol, well.bottom(2))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-5)
        p1000.drop_tip()

    # 1d) 5 min binding incubation at room temperature
    protocol.comment('Incubating %d min at room temperature for RNA binding'
                     % BINDING_INCUBATION_MIN)
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ----------------------------------------------------------------------
    # Step 2 - magnet on for 4 min
    # ----------------------------------------------------------------------
    protocol.comment('STEP 2: engaging the magnetic module for %d min'
                     % MAGNET_BINDING_MIN)
    mag_mod.engage()      # labware-defined engage height for this deep-well plate
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # ----------------------------------------------------------------------
    # Step 3 - discard the binding supernatant
    # ----------------------------------------------------------------------
    protocol.comment('STEP 3: discarding the binding supernatant')
    remove_to_waste(BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL, waste_sup_cols,
                    'binding supernatant')

    # ----------------------------------------------------------------------
    # Steps 4 and 5 - two washes with 500 uL 70 % ethanol (magnet stays on)
    # ----------------------------------------------------------------------
    for wash in range(1, NUM_WASHES + 1):
        protocol.comment('STEP %d: wash %d with %d uL 70 %% ethanol'
                         % (wash + 3, wash, ETHANOL_VOL))
        add_reagent_from_top(
            ETHANOL_VOL,
            lambda i, w=wash: reservoir_source(ETHANOL_WELLS[w], i),
            '70 %% ethanol (wash %d)' % wash)
        remove_to_waste(ETHANOL_VOL, waste_wash_cols,
                        '70 %% ethanol (wash %d)' % wash)

    # ----------------------------------------------------------------------
    # Step 6 - air-dry the beads for 4 min with the magnet engaged
    # ----------------------------------------------------------------------
    protocol.comment('STEP 6: air-drying the beads for %d min' % AIR_DRY_MIN)
    protocol.delay(minutes=AIR_DRY_MIN)

    # ----------------------------------------------------------------------
    # Step 7 - magnet off, 100 uL elution buffer, resuspend the beads
    # ----------------------------------------------------------------------
    protocol.comment('STEP 7: disengaging the magnet and adding %d uL elution '
                     'buffer' % ELUTION_VOL)
    mag_mod.disengage()
    elution_buffer = reservoir.wells_by_name()[ELUTION_BUFFER_WELL]
    m300.flow_rate.aspirate = 94
    m300.flow_rate.dispense = 94
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, on_pellet(dest, z=2))
        # resuspend the dried pellet in the elution buffer
        m300.mix(10, 80, on_pellet(dest, z=1))
        m300.blow_out(dest.top(-5))
        m300.touch_tip(dest, v_offset=-5)
        m300.drop_tip()

    # ----------------------------------------------------------------------
    # Step 8 - 30 s elution, then magnet on for 90 s
    # ----------------------------------------------------------------------
    protocol.comment('STEP 8: eluting %d s, then engaging the magnet for %d s'
                     % (ELUTION_INCUBATION_SEC, ELUTION_MAGNET_SEC))
    protocol.delay(seconds=ELUTION_INCUBATION_SEC)
    mag_mod.engage()
    protocol.delay(seconds=ELUTION_MAGNET_SEC)

    # ----------------------------------------------------------------------
    # Step 9 - recover the eluate into the 4 C elution plate
    # ----------------------------------------------------------------------
    protocol.comment('STEP 9: transferring %d uL eluate to the elution plate at '
                     '%d C' % (ELUTION_VOL, ELUTION_PLATE_TEMP_C))
    temp_mod.await_temperature(ELUTION_PLATE_TEMP_C)
    m300.flow_rate.aspirate = ELUATE_ASPIRATE_RATE
    m300.flow_rate.dispense = 50
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, away_from_pellet(src, z=0.5))
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
        m300.touch_tip(dest, v_offset=-2)
        m300.drop_tip()

    mag_mod.disengage()
    protocol.comment('Extraction complete: %d eluates (%d uL each) are in the '
                     'odd columns of the elution plate on the temperature module '
                     'at %d C.' % (NUM_SAMPLES, ELUTION_VOL, ELUTION_PLATE_TEMP_C))
