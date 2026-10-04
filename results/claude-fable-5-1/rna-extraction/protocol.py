"""
Magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2 (48 samples).

Implementation of the "OT-2 in-house" protocol described in:
  Lázaro-Perona F. et al. "Automated low-cost SARS-CoV-2 RNA extraction
  protocols", PLOS ONE 2021, doi:10.1371/journal.pone.0246302

Protocol as described in the paper (per sample well):
  1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated sample,
     mix by pipetting 5 times, incubate 5 min at room temperature.
  2. Engage GEN1 magnetic module, 4 min.
  3. Collect supernatant and discard.
  4. Add 500 uL ethanol 70 %, collect and discard.
  5. Add 500 uL ethanol 70 %, collect and discard.
  6. Air dry 4 min.
  7. Disengage magnet, add 100 uL elution buffer (resuspend beads).
  8. After 30 s engage magnet.
  9. After 90 s collect the eluate into a 96-well plate (kept at 4 C).

Deck layout (fixed):
  1  waste deep-well plate            usascientific_96_wellplate_2.4ml_deep
  2,3,9  200 uL filter tips           opentrons_96_filtertiprack_200ul
  4  Magnetic Module GEN1 + sample/extraction deep-well plate
  5  reagent reservoir                nest_12_reservoir_15ml
       col 2  magnetic beads, col 4 elution buffer,
       cols 6-7 isopropanol, cols 9-12 ethanol 70 %
  6  Temperature Module GEN1 + elution plate thermo_96_wellplate_200ul (4 C)
  7  samples 25-48 (2 mL tubes)       opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
  10 samples 1-24  (2 mL tubes)       opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
  11 1000 uL filter tips              opentrons_96_filtertiprack_1000ul
  left  mount: p1000_single_gen2     right mount: p300_multi_gen2

Samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the magnetic-module
plate; sample n goes to the n-th well of those columns in column order
(samples 1-8 -> column 1 A-H, 9-16 -> column 3, ... 41-48 -> column 11).
Each eluate is recovered into the same well position of the elution plate.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 magnetic-bead RNA extraction (OT-2 in-house, 48 samples)',
    'author': 'Implementation of Lazaro-Perona et al., PLOS ONE 2021',
    'description': 'Isopropanol/magnetic bead binding, 2x 70% ethanol washes, '
                   '100 uL elution at 4 C; 48 samples in odd columns.',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------- parameters
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [0, 2, 4, 6, 8, 10]      # 0-based -> plate columns 1,3,5,7,9,11

BEAD_VOL = 40            # uL magnetic beads per sample
ISOPROPANOL_VOL = 250    # uL isopropanol per sample
SAMPLE_VOL = 250         # uL inactivated sample per sample
SAMPLE_MIX_REPS = 5      # "mix by pipetting five times"
BINDING_VOL = BEAD_VOL + ISOPROPANOL_VOL + SAMPLE_VOL   # 540 uL supernatant
ETHANOL_VOL = 500        # uL 70 % ethanol per wash
ELUTION_VOL = 100        # uL elution buffer
ELUTION_MIX_REPS = 10    # resuspension of the dried beads

INCUBATION_MIN = 5       # binding incubation at room temperature
MAGNET_MIN = 4           # bead capture before supernatant removal
DRY_MIN = 4              # air drying after the second ethanol wash
ELUTION_RESUSPEND_SEC = 30   # beads in elution buffer before magnet on
ELUTION_MAGNET_SEC = 90      # bead capture before collecting the eluate

ELUTION_TEMP_C = 4

MULTI_MAX = 200          # 200 uL filter tips on the p300 multi
# Beads are pulled to one side of the well by the GEN1 magnets; aspirate
# from the opposite side of the well bottom.  For the odd (1-based) columns
# used here the pellet forms on the +x side, so we aspirate at -x.
BEAD_SIDE_OFFSET_MM = -2.0


def split_volume(total, max_vol=MULTI_MAX):
    """Split a per-well volume into equal chunks the multi-channel can carry."""
    n = int(-(-total // max_vol))  # ceil
    return [total / n] * n


def run(protocol: protocol_api.ProtocolContext):

    # ----------------------------------------------------------- labware
    waste = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', '1',
                                  'waste plate')
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
               for s in ['2', '3', '9']]
    tips1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')

    magdeck = protocol.load_module('magnetic module', '4')
    magplate = magdeck.load_labware('usascientific_96_wellplate_2.4ml_deep',
                                    'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    tempdeck = protocol.load_module('tempdeck', '6')
    elution_plate = tempdeck.load_labware('thermo_96_wellplate_200ul',
                                          'elution plate')

    tuberack_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    tuberack_2 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=[tips1000])
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tips200)

    # ----------------------------------------------------------- reagents
    beads = reservoir.wells_by_name()['A2']
    elution_buffer = reservoir.wells_by_name()['A4']
    # 48 x 250 uL = 12 mL isopropanol  -> 6 mL from each of columns 6 and 7
    isopropanol = {0: 'A6', 2: 'A6', 4: 'A6', 6: 'A7', 8: 'A7', 10: 'A7'}
    # 48 x 500 uL = 24 mL per wash -> 12 mL per reservoir column
    ethanol_wash1 = {0: 'A9', 2: 'A9', 4: 'A9', 6: 'A10', 8: 'A10', 10: 'A10'}
    ethanol_wash2 = {0: 'A11', 2: 'A11', 4: 'A11', 6: 'A12', 8: 'A12', 10: 'A12'}

    # multi-channel targets: the A-row well of every sample column
    mag_cols = [magplate.columns()[c][0] for c in SAMPLE_COLUMNS]
    # supernatant goes to the matching odd waste column, the two ethanol
    # washes to the even column to its right (max 1000 uL per waste well)
    waste_super = [waste.columns()[c][0] for c in SAMPLE_COLUMNS]
    waste_wash = [waste.columns()[c + 1][0] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns()[c][0] for c in SAMPLE_COLUMNS]

    # single-channel sample routing: tube n -> n-th well of the odd columns
    sample_tubes = tuberack_1.wells() + tuberack_2.wells()
    sample_wells = []
    for c in SAMPLE_COLUMNS:
        sample_wells += magplate.columns()[c]
    sample_tubes = sample_tubes[:NUM_SAMPLES]
    sample_wells = sample_wells[:NUM_SAMPLES]

    # ----------------------------------------------------------- helpers
    def remove_liquid(volume, source, dest, pip=m300):
        """Slowly aspirate `volume` from the bead-free side of the well
        bottom (magnet engaged) and discard it into the waste plate."""
        pip.flow_rate.aspirate = 50
        pip.flow_rate.dispense = 150
        for vol in split_volume(volume):
            pip.aspirate(vol, source.bottom(0.5).move(Point(x=BEAD_SIDE_OFFSET_MM)))
            pip.air_gap(10)
            pip.dispense(vol + 10, dest.top(-5))
            pip.blow_out(dest.top(-5))
        pip.flow_rate.aspirate = 94
        pip.flow_rate.dispense = 94

    def add_reagent(volume, source_name_by_col, dests):
        """Dispense a reagent from the reservoir onto all sample columns from
        above the liquid with a single set of tips."""
        m300.pick_up_tip()
        for c, dest in zip(SAMPLE_COLUMNS, dests):
            src = reservoir.wells_by_name()[source_name_by_col[c]]
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dest.top(-5))
                m300.blow_out(dest.top(-5))
        m300.drop_tip()

    # ----------------------------------------------------------- start-up
    magdeck.disengage()
    protocol.comment('Cooling the elution plate to %d C' % ELUTION_TEMP_C)
    tempdeck.set_temperature(ELUTION_TEMP_C)

    # ============================================================ STEP 1
    # 40 uL beads + 250 uL isopropanol + 250 uL sample, mix 5x, 5 min RT
    protocol.comment('STEP 1a: %d uL magnetic beads per well' % BEAD_VOL)
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(2))       # resuspend the bead slurry
    m300.blow_out(beads.top(-5))
    for dest in mag_cols:
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dest.bottom(10))
        m300.blow_out(dest.top(-5))
    m300.drop_tip()

    protocol.comment('STEP 1b: %d uL isopropanol per well' % ISOPROPANOL_VOL)
    add_reagent(ISOPROPANOL_VOL, isopropanol, mag_cols)

    protocol.comment('STEP 1c: %d uL inactivated sample per well, mix %d times'
                     % (SAMPLE_VOL, SAMPLE_MIX_REPS))
    p1000.flow_rate.aspirate = 150
    p1000.flow_rate.dispense = 300
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(SAMPLE_MIX_REPS, 400, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-5)
        p1000.drop_tip()

    protocol.comment('STEP 1d: incubate %d min at room temperature' % INCUBATION_MIN)
    protocol.delay(minutes=INCUBATION_MIN)

    # ============================================================ STEP 2
    protocol.comment('STEP 2: engage magnetic module, %d min' % MAGNET_MIN)
    magdeck.engage()
    protocol.delay(minutes=MAGNET_MIN)

    # ============================================================ STEP 3
    protocol.comment('STEP 3: remove %d uL supernatant to waste' % BINDING_VOL)
    for src, dest in zip(mag_cols, waste_super):
        m300.pick_up_tip()
        remove_liquid(BINDING_VOL, src, dest)
        m300.drop_tip()

    # ============================================================ STEP 4 & 5
    for wash_no, ethanol in ((1, ethanol_wash1), (2, ethanol_wash2)):
        protocol.comment('STEP %d: wash %d - add %d uL ethanol 70%%'
                         % (3 + wash_no, wash_no, ETHANOL_VOL))
        add_reagent(ETHANOL_VOL, ethanol, mag_cols)

        protocol.comment('STEP %d: wash %d - remove %d uL ethanol to waste'
                         % (3 + wash_no, wash_no, ETHANOL_VOL))
        for src, dest in zip(mag_cols, waste_wash):
            m300.pick_up_tip()
            remove_liquid(ETHANOL_VOL, src, dest)
            m300.drop_tip()

    # ============================================================ STEP 6
    protocol.comment('STEP 6: air dry beads %d min (magnet engaged)' % DRY_MIN)
    protocol.delay(minutes=DRY_MIN)

    # ============================================================ STEP 7
    protocol.comment('STEP 7: disengage magnet, add %d uL elution buffer and '
                     'resuspend beads' % ELUTION_VOL)
    magdeck.disengage()
    for dest in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        # pipette over the bead pellet side to bring the beads back into
        # suspension
        m300.mix(ELUTION_MIX_REPS, 80,
                 dest.bottom(1).move(Point(x=-BEAD_SIDE_OFFSET_MM)))
        m300.blow_out(dest.top(-5))
        m300.touch_tip(dest, v_offset=-5)
        m300.drop_tip()

    # ============================================================ STEP 8
    protocol.comment('STEP 8: %d s elution, then engage magnet for %d s'
                     % (ELUTION_RESUSPEND_SEC, ELUTION_MAGNET_SEC))
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    magdeck.engage()
    protocol.delay(seconds=ELUTION_MAGNET_SEC)

    # ============================================================ STEP 9
    protocol.comment('STEP 9: transfer %d uL eluate to the elution plate at %d C'
                     % (ELUTION_VOL, ELUTION_TEMP_C))
    for src, dest in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.flow_rate.aspirate = 30
        m300.aspirate(ELUTION_VOL, src.bottom(0.5).move(Point(x=BEAD_SIDE_OFFSET_MM)))
        m300.flow_rate.aspirate = 94
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
        m300.touch_tip(dest, v_offset=-2)
        m300.drop_tip()

    magdeck.disengage()
    protocol.comment('Extraction finished. Eluates are held at %d C on the '
                     'temperature module.' % ELUTION_TEMP_C)
