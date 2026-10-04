"""
Magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2 (48 samples).

Implements the "OT-2 in-house" protocol of Lazaro-Perona et al., PLOS ONE 2021,
doi:10.1371/journal.pone.0246302 (Methods, "OT-2 in-house protocol", Table 1):

  1. Per well: 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated
     sample. Mix by pipetting 5x, incubate 5 min at room temperature.
  2. Engage the GEN1 magnetic module, 4 min.
  3. Collect the supernatant and discard.
  4. Add 500 uL 70 % ethanol, collect and discard.
  5. Add 500 uL 70 % ethanol, collect and discard.
  6. Air-dry 4 min.
  7. Disengage the magnet, add 100 uL elution buffer.
  8. After 30 s engage the magnet.
  9. After 90 s collect the eluate into the 96-well elution plate (kept at 4 C).

Deck layout (fixed by the operator):
  1   waste deep-well plate          usascientific_96_wellplate_2.4ml_deep
  2,3,9  200 uL filter tips           opentrons_96_filtertiprack_200ul
  4   Magnetic Module GEN1 + sample/extraction deep-well plate
  5   nest_12_reservoir_15ml: col 2 beads, col 4 elution buffer,
      cols 6-7 isopropanol, cols 9-12 70 % ethanol
  6   Temperature Module GEN1 + elution plate (thermo_96_wellplate_200ul)
  10  samples 1-24   (2 mL tubes)     opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
  7   samples 25-48  (2 mL tubes)
  11  1000 uL filter tips             opentrons_96_filtertiprack_1000ul

Samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the magnetic-module
plate.  Each eluate is recovered into the same well position of the elution
plate on the temperature module.

Reagent loading guide (reservoir, slot 5), 48 samples:
  beads      col 2       48 x 40 uL  = 1.9 mL   (load >= 3 mL)
  elution    col 4       48 x 100 uL = 4.8 mL   (load >= 6 mL)
  isoprop.   cols 6, 7   24 x 250 uL = 6.0 mL per column (load >= 7.5 mL each)
  EtOH 70 %  cols 9-12   24 x 500 uL = 12 mL per column  (load >= 13.5 mL each)
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 magnetic-bead RNA extraction (48 samples, OT-2 in-house)',
    'author': 'Implemented from Lazaro-Perona et al. 2021, PLOS ONE 16(2): e0246302',
    'description': 'Mag-Bind TotalPure NGS beads / isopropanol binding, 2x 70 % '
                   'ethanol wash, 100 uL elution; GEN1 magnetic module, 48 samples.',
    'apiLevel': '2.9',
}

# --------------------------------------------------------------------------
# Protocol parameters (paper values)
# --------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = ['1', '3', '5', '7', '9', '11']   # odd columns of the mag plate

BEAD_VOL = 40           # uL magnetic beads per sample
ISOPROPANOL_VOL = 250   # uL isopropanol per sample
SAMPLE_VOL = 250        # uL inactivated sample per well
BINDING_MIX_REPS = 5    # "mix by pipetting five times"
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
WASH_VOL = 500          # uL 70 % ethanol, two washes
DRY_MIN = 4
ELUTION_VOL = 100       # uL elution buffer
ELUTION_MIX_REPS = 10   # resuspend the dried beads in the elution buffer
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90
ELUATE_VOL = 90         # uL recovered; ~10 uL is left over the bead pellet
ELUTION_PLATE_TEMP_C = 4

# Volume removed to waste: the full volume present plus a small excess so that
# the well is left as dry as possible (the excess is just air in the tip).
BINDING_TOTAL_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL   # 540 uL
SUPERNATANT_REMOVE_VOL = BINDING_TOTAL_VOL + 20               # 560 uL
WASH_REMOVE_VOL = WASH_VOL + 20                               # 520 uL

# Beads pellet against the GEN1 magnets, which sit between the column pairs
# (1|2, 3|4, ...).  For the odd columns used here the pellet forms on the
# right-hand (+x) wall, so all aspirations from the pelleted plate are taken
# from the left-hand side of the well, a little above the bottom.
PELLET_AVOID_X_OFFSET = -2.0   # mm toward the wall opposite the pellet
PELLET_AVOID_Z = 0.8           # mm above the well bottom
ASPIRATE_SLOW_RATE = 40        # uL/s when drawing supernatant off a pellet
P300_MAX_VOL = 200             # uL, 200 uL filter tips

# Reservoir map (slot 5, nest_12_reservoir_15ml)
BEAD_COL = '2'
ELUTION_COL = '4'
ISOPROPANOL_COLS = ['6', '7']          # 3 sample columns per reservoir column
ETHANOL_WASH1_COLS = ['9', '10']       # 3 sample columns per reservoir column
ETHANOL_WASH2_COLS = ['11', '12']


def run(protocol: protocol_api.ProtocolContext):

    # ----------------------------------------------------------------------
    # Labware, modules, pipettes
    # ----------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'supernatant waste')

    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    samples_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    samples_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ----------------------------------------------------------------------
    # Well bookkeeping
    # ----------------------------------------------------------------------
    # Multi-channel targets: the top (row A) well of each used column.
    mag_cols = [mag_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]
    waste_cols = [waste_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]

    beads = reservoir.wells_by_name()['A' + BEAD_COL]
    elution_buffer = reservoir.wells_by_name()['A' + ELUTION_COL]

    def reagent_for(col_index, reservoir_cols):
        """Map the i-th sample column to one of two reservoir columns (3+3)."""
        return reservoir.wells_by_name()['A' + reservoir_cols[col_index // 3]]

    # Single-channel sample routing: tube racks are read column-wise
    # (A1, B1, C1, D1, A2, ...) so samples 1-24 and 25-48 keep their numbering.
    sample_tubes = samples_1_24.wells() + samples_25_48.wells()
    sample_wells = []
    for c in SAMPLE_COLUMNS:
        sample_wells += mag_plate.columns_by_name()[c]
    sample_tubes = sample_tubes[:NUM_SAMPLES]
    sample_wells = sample_wells[:NUM_SAMPLES]

    def pellet_side(well):
        """Aspiration point in a pelleted well, away from the bead pellet."""
        return well.bottom(PELLET_AVOID_Z).move(Point(x=PELLET_AVOID_X_OFFSET))

    def split_volume(total, max_vol=P300_MAX_VOL):
        """Split a volume into equal aliquots that fit a 200 uL tip."""
        n = int(-(-total // max_vol))
        return [total / n] * n

    def remove_to_waste(volume):
        """Draw `volume` off the pelleted beads (magnet engaged) in every
        sample column and send it to the matching waste column.  One tip
        column per sample column, slow aspiration from the side opposite the
        pellet."""
        m300.flow_rate.aspirate = ASPIRATE_SLOW_RATE
        for src, dst in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                m300.aspirate(vol, pellet_side(src))
                m300.dispense(vol, dst.top(-5))
                m300.blow_out(dst.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94   # p300 multi GEN2 default

    def add_reagent_to_all(volume, source_for_col, dispense_top_offset=-5):
        """Dispense `volume` into every sample column from the top of the
        well (no contact with the well contents), reusing one tip column."""
        m300.pick_up_tip()
        for i, dst in enumerate(mag_cols):
            src = source_for_col(i)
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(1))
                m300.dispense(vol, dst.top(dispense_top_offset))
                m300.blow_out(dst.top(dispense_top_offset))
        m300.drop_tip()

    # ----------------------------------------------------------------------
    # Start-up: magnet off, elution plate cooling to 4 C
    # ----------------------------------------------------------------------
    protocol.comment('Start: magnet disengaged, elution plate held at %d C'
                     % ELUTION_PLATE_TEMP_C)
    mag_mod.disengage()
    temp_mod.set_temperature(ELUTION_PLATE_TEMP_C)

    # ----------------------------------------------------------------------
    # Step 1a: 40 uL magnetic beads per well
    # ----------------------------------------------------------------------
    protocol.comment('Step 1a: %d uL magnetic beads per well' % BEAD_VOL)
    m300.pick_up_tip()
    m300.mix(5, 150, beads.bottom(2))          # resuspend the bead slurry
    m300.blow_out(beads.top(-5))
    for dst in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(1))
        m300.dispense(BEAD_VOL, dst.bottom(5))
        m300.blow_out(dst.bottom(5))
        m300.touch_tip(dst, v_offset=-10)
    m300.drop_tip()

    # ----------------------------------------------------------------------
    # Step 1b: 250 uL isopropanol per well
    # ----------------------------------------------------------------------
    protocol.comment('Step 1b: %d uL isopropanol per well' % ISOPROPANOL_VOL)
    add_reagent_to_all(ISOPROPANOL_VOL,
                       lambda i: reagent_for(i, ISOPROPANOL_COLS))

    # ----------------------------------------------------------------------
    # Step 1c: 250 uL inactivated sample per well, mix 5x, one tip per sample
    # ----------------------------------------------------------------------
    protocol.comment('Step 1c: %d uL inactivated sample per well, mix %dx'
                     % (SAMPLE_VOL, BINDING_MIX_REPS))
    p1000.flow_rate.aspirate = 150
    p1000.flow_rate.dispense = 150
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        # mix the 540 uL bead/isopropanol/sample suspension 5 times
        p1000.mix(BINDING_MIX_REPS, 400, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-10)
        p1000.drop_tip()

    # ----------------------------------------------------------------------
    # Step 1d: 5 min binding at room temperature
    # ----------------------------------------------------------------------
    protocol.comment('Step 1d: %d min binding incubation at room temperature'
                     % BINDING_INCUBATION_MIN)
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ----------------------------------------------------------------------
    # Step 2: engage the GEN1 magnetic module for 4 min
    # ----------------------------------------------------------------------
    protocol.comment('Step 2: engage magnet, %d min' % MAGNET_BINDING_MIN)
    mag_mod.engage()      # labware-defined engage height for this deep-well plate
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # ----------------------------------------------------------------------
    # Step 3: remove and discard the binding supernatant
    # ----------------------------------------------------------------------
    protocol.comment('Step 3: remove %d uL supernatant to waste' % BINDING_TOTAL_VOL)
    remove_to_waste(SUPERNATANT_REMOVE_VOL)

    # ----------------------------------------------------------------------
    # Steps 4 and 5: two washes with 500 uL 70 % ethanol (magnet stays on)
    # ----------------------------------------------------------------------
    for wash_no, etoh_cols in enumerate([ETHANOL_WASH1_COLS, ETHANOL_WASH2_COLS], 1):
        protocol.comment('Step %d: wash %d, add %d uL 70 %% ethanol'
                         % (3 + wash_no, wash_no, WASH_VOL))
        add_reagent_to_all(WASH_VOL, lambda i, cols=etoh_cols: reagent_for(i, cols))
        protocol.comment('Step %d: wash %d, remove ethanol to waste'
                         % (3 + wash_no, wash_no))
        remove_to_waste(WASH_REMOVE_VOL)

    # ----------------------------------------------------------------------
    # Step 6: air-dry the beads 4 min (magnet still engaged)
    # ----------------------------------------------------------------------
    protocol.comment('Step 6: air-dry beads %d min' % DRY_MIN)
    protocol.delay(minutes=DRY_MIN)

    # ----------------------------------------------------------------------
    # Step 7: magnet off, 100 uL elution buffer, resuspend the beads
    # ----------------------------------------------------------------------
    protocol.comment('Step 7: disengage magnet, add %d uL elution buffer and '
                     'resuspend beads' % ELUTION_VOL)
    mag_mod.disengage()
    for dst in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(1))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        # pellet is on the +x wall: dispense the mix stream onto it
        m300.mix(ELUTION_MIX_REPS, 80,
                 dst.bottom(1).move(Point(x=-PELLET_AVOID_X_OFFSET)))
        m300.blow_out(dst.top(-10))
        m300.touch_tip(dst, v_offset=-10)
        m300.drop_tip()

    # ----------------------------------------------------------------------
    # Step 8: 30 s elution, then magnet on for 90 s
    # ----------------------------------------------------------------------
    protocol.comment('Step 8: %d s elution, then engage magnet %d s'
                     % (ELUTION_RESUSPEND_SEC, ELUTION_MAGNET_SEC))
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()
    protocol.delay(seconds=ELUTION_MAGNET_SEC)

    # ----------------------------------------------------------------------
    # Step 9: transfer the eluted RNA to the 4 C elution plate
    # ----------------------------------------------------------------------
    protocol.comment('Step 9: transfer %d uL eluate to the elution plate (%d C)'
                     % (ELUATE_VOL, ELUTION_PLATE_TEMP_C))
    m300.flow_rate.aspirate = 25
    m300.flow_rate.dispense = 50
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, pellet_side(src))
        m300.dispense(ELUATE_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
        m300.touch_tip(dst, v_offset=-2)
        m300.drop_tip()
    m300.flow_rate.aspirate = 94
    m300.flow_rate.dispense = 94

    mag_mod.disengage()
    protocol.comment('Done. Eluates are in columns %s of the elution plate, '
                     'held at %d C on the temperature module.'
                     % (', '.join(SAMPLE_COLUMNS), ELUTION_PLATE_TEMP_C))
