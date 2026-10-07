"""
SARS-CoV-2 viral RNA extraction with magnetic beads on an Opentrons OT-2.

Implementation of the "OT-2 in-house" protocol described in
Automated low-cost SARS-CoV-2 RNA extraction protocols (PLOS ONE 2021,
doi:10.1371/journal.pone.0246302) for 48 inactivated samples.

Per well (odd columns 1, 3, 5, 7, 9, 11 of the deep-well plate on the magnet):
  1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL sample, mix 5x,
     incubate 5 min at room temperature.
  2. Engage GEN1 magnetic module, 4 min.
  3. Collect supernatant and discard.
  4. Add 500 uL 70% ethanol, collect and discard.
  5. Add 500 uL 70% ethanol, collect and discard.
  6. Air dry 4 min.
  7. Disengage magnet, add 100 uL elution buffer (resuspend beads).
  8. After 30 s engage magnet.
  9. After 90 s collect the eluate into the elution plate held at 4 C.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 magnetic-bead RNA extraction (OT-2 in-house, 48 samples)',
    'author': 'Automated from PLOS ONE 2021, doi:10.1371/journal.pone.0246302',
    'apiLevel': '2.9',
}

# ---------------------------------------------------------------------------
# Protocol parameters (volumes in uL, times as named)
# ---------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]      # odd columns of the magnet plate

BEAD_VOL = 40
ISOPROPANOL_VOL = 250
SAMPLE_VOL = 250
LYSATE_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL   # 540
ETHANOL_VOL = 500
ELUTION_VOL = 100
ELUATE_RECOVER_VOL = 90      # leave ~10 uL behind so the bead pellet is not carried over

SAMPLE_MIX_REPS = 5
INCUBATION_MIN = 5
MAGNET_BIND_MIN = 4
DRY_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90
ELUTION_PLATE_TEMP_C = 4

# Reservoir (slot 5) layout, by column number
BEADS_COL = 2
ELUTION_BUFFER_COL = 4
ISOPROPANOL_COLS = [6, 7]          # 48 x 250 uL = 12 mL -> 6 mL per column
ETHANOL_WASH1_COLS = [9, 10]       # 48 x 500 uL = 24 mL -> 12 mL per column
ETHANOL_WASH2_COLS = [11, 12]

# GEN1 magnet: for odd-numbered columns the beads pellet on the +x (right) side
# of the well, so supernatant is aspirated offset towards -x.
PELLET_SIDE = 1
ASPIRATE_OFFSET_MM = 2


def run(protocol: protocol_api.ProtocolContext):

    # -----------------------------------------------------------------------
    # Deck
    # -----------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['2', '3', '9']]
    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')
    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')
    rack_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10', 'samples 1-24')
    rack_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7', 'samples 25-48')
    tiprack_1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')

    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=[tiprack_1000])
    m300 = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks_200)

    # -----------------------------------------------------------------------
    # Well bookkeeping
    # -----------------------------------------------------------------------
    # Sample tubes in order 1..48: slot 10 A1,B1,C1,D1,A2,... then slot 7.
    sample_tubes = (rack_1_24.wells() + rack_25_48.wells())[:NUM_SAMPLES]
    # Destination wells: A1..H1, A3..H3, ... one sample per well.
    sample_wells = [
        well for col in SAMPLE_COLUMNS for well in mag_plate.columns()[col - 1]
    ][:NUM_SAMPLES]

    # Multichannel works on the A-row well of each column.
    mag_cols = [mag_plate.columns()[c - 1][0] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns()[c - 1][0] for c in SAMPLE_COLUMNS]
    # Supernatant goes to the same (odd) column of the waste plate, the two
    # ethanol washes to the adjacent even column (max 1 mL per waste well).
    waste_sup_cols = [waste_plate.columns()[c - 1][0] for c in SAMPLE_COLUMNS]
    waste_wash_cols = [waste_plate.columns()[c][0] for c in SAMPLE_COLUMNS]

    beads = reservoir.columns()[BEADS_COL - 1][0]
    elution_buffer = reservoir.columns()[ELUTION_BUFFER_COL - 1][0]

    def reagent_for(col_index, reagent_cols):
        """Split the 6 sample columns evenly over the reservoir columns."""
        per_col = len(SAMPLE_COLUMNS) // len(reagent_cols)
        return reservoir.columns()[reagent_cols[col_index // per_col] - 1][0]

    def split_volume(total, max_per_transfer=180):
        n = int(-(-total // max_per_transfer))
        return [total / n] * n

    def supernatant_loc(well):
        return well.bottom(0.5).move(Point(x=-PELLET_SIDE * ASPIRATE_OFFSET_MM))

    def remove_to_waste(src, dest, total_vol, aspirate_rate=50, air_gap=15):
        """Pull `total_vol` off the pellet in column `src` into waste column `dest`."""
        m300.flow_rate.aspirate = aspirate_rate
        m300.flow_rate.dispense = 150
        m300.pick_up_tip()
        for vol in split_volume(total_vol, 200 - air_gap):
            m300.aspirate(vol, supernatant_loc(src))
            m300.air_gap(air_gap)
            m300.dispense(vol + air_gap, dest.top(-5))
            m300.blow_out(dest.top(-5))
        m300.drop_tip()

    def add_reagent(reagent_of, total_vol, dispense_z=-15):
        """Add `total_vol` of a reagent to every sample column with one tip set,
        dispensing from above the liquid so the tip never touches the wells."""
        m300.flow_rate.aspirate = 94
        m300.flow_rate.dispense = 94
        m300.pick_up_tip()
        for i, dest in enumerate(mag_cols):
            for vol in split_volume(total_vol):
                m300.aspirate(vol, reagent_of(i).bottom(2))
                m300.dispense(vol, dest.top(dispense_z))
                m300.blow_out(dest.top(dispense_z))
        m300.drop_tip()

    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------
    mag_mod.disengage()
    temp_mod.start_set_temperature(ELUTION_PLATE_TEMP_C)   # elution plate kept at 4 C

    # -----------------------------------------------------------------------
    # Step 1: 40 uL beads + 250 uL isopropanol + 250 uL sample, mix 5x, 5 min
    # -----------------------------------------------------------------------
    protocol.comment('Step 1a: %d uL magnetic beads per well' % BEAD_VOL)
    m300.flow_rate.aspirate = 94
    m300.flow_rate.dispense = 94
    m300.pick_up_tip()
    for i, dest in enumerate(mag_cols):
        m300.mix(5, 150, beads.bottom(2))            # keep beads in suspension
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dest.top(-15))
        m300.blow_out(dest.top(-15))
    m300.drop_tip()

    protocol.comment('Step 1b: %d uL isopropanol per well' % ISOPROPANOL_VOL)
    add_reagent(lambda i: reagent_for(i, ISOPROPANOL_COLS), ISOPROPANOL_VOL)

    protocol.comment('Step 1c: %d uL inactivated sample per well, mix %d times'
                     % (SAMPLE_VOL, SAMPLE_MIX_REPS))
    p1000.flow_rate.aspirate = 274
    p1000.flow_rate.dispense = 274
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(SAMPLE_MIX_REPS, 400, well.bottom(2))
        p1000.blow_out(well.top(-10))
        p1000.touch_tip(well, v_offset=-10)
        p1000.drop_tip()

    protocol.comment('Step 1d: incubate %d min at room temperature' % INCUBATION_MIN)
    protocol.delay(minutes=INCUBATION_MIN)

    # -----------------------------------------------------------------------
    # Step 2: engage magnet 4 min
    # -----------------------------------------------------------------------
    protocol.comment('Step 2: engage magnetic module for %d min' % MAGNET_BIND_MIN)
    mag_mod.engage()
    protocol.delay(minutes=MAGNET_BIND_MIN)

    # -----------------------------------------------------------------------
    # Step 3: collect supernatant and discard
    # -----------------------------------------------------------------------
    protocol.comment('Step 3: remove %d uL supernatant to waste' % LYSATE_VOL)
    for src, dest in zip(mag_cols, waste_sup_cols):
        remove_to_waste(src, dest, LYSATE_VOL + 15)

    # -----------------------------------------------------------------------
    # Steps 4 and 5: two washes with 500 uL 70% ethanol, magnet engaged
    # -----------------------------------------------------------------------
    for wash_no, ethanol_cols in enumerate([ETHANOL_WASH1_COLS, ETHANOL_WASH2_COLS], 1):
        protocol.comment('Step %d: wash %d - add %d uL 70%% ethanol'
                         % (wash_no + 3, wash_no, ETHANOL_VOL))
        add_reagent(lambda i, cols=ethanol_cols: reagent_for(i, cols), ETHANOL_VOL)

        protocol.comment('Step %d: wash %d - remove ethanol to waste'
                         % (wash_no + 3, wash_no))
        for src, dest in zip(mag_cols, waste_wash_cols):
            remove_to_waste(src, dest, ETHANOL_VOL + 10, aspirate_rate=94)

    # -----------------------------------------------------------------------
    # Step 6: air dry 4 min
    # -----------------------------------------------------------------------
    protocol.comment('Step 6: air dry beads for %d min' % DRY_MIN)
    protocol.delay(minutes=DRY_MIN)

    # -----------------------------------------------------------------------
    # Step 7: disengage magnet, add 100 uL elution buffer and resuspend beads
    # -----------------------------------------------------------------------
    protocol.comment('Step 7: disengage magnet, add %d uL elution buffer' % ELUTION_VOL)
    mag_mod.disengage()
    m300.flow_rate.aspirate = 94
    m300.flow_rate.dispense = 94
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        m300.mix(10, 80, dest.bottom(1))
        m300.blow_out(dest.top(-15))
        m300.touch_tip(dest, v_offset=-15)
        m300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 8: after 30 s engage magnet; Step 9: after 90 s collect eluate
    # -----------------------------------------------------------------------
    protocol.comment('Step 8: %d s resuspension, then engage magnet' % ELUTION_RESUSPEND_SEC)
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()
    protocol.comment('Step 9: %d s on magnet, then recover eluate' % ELUTION_MAGNET_SEC)
    protocol.delay(seconds=ELUTION_MAGNET_SEC)

    temp_mod.await_temperature(ELUTION_PLATE_TEMP_C)
    m300.flow_rate.aspirate = 30
    m300.flow_rate.dispense = 94
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_RECOVER_VOL, supernatant_loc(src))
        m300.dispense(ELUATE_RECOVER_VOL, dest.bottom(1))
        m300.blow_out(dest.top(-2))
        m300.touch_tip(dest, v_offset=-2)
        m300.drop_tip()

    mag_mod.disengage()
    protocol.comment('Extraction finished. Eluates are in the odd columns of the '
                     'elution plate on the temperature module (4 C).')
