"""
Automated low-cost SARS-CoV-2 RNA extraction -- OT-2 in-house magnetic-bead protocol
(Lazaro-Perona et al., PLOS ONE 2021, doi:10.1371/journal.pone.0246302), 48 samples.

Protocol steps as described in the paper (OT-2in-house protocol, Table 1):
  1. Per well: 40 uL Mag-Bind TotalPure NGS beads + 250 uL isopropanol + 250 uL
     inactivated sample.  Mix by pipetting five times, incubate 5 min at RT.
  2. Engage the GEN1 magnetic module for 4 min.
  3. Collect the supernatant and discard.
  4. Add 500 uL ethanol 70 %, collect and discard.
  5. Add 500 uL ethanol 70 %, collect and discard.
  6. Air dry for 4 min.
  7. Disengage the magnet and add 100 uL elution buffer (resuspend beads).
  8. After 30 s engage the magnet.
  9. After 90 s collect the eluate and transfer it to the elution plate (kept at 4 C).

Deck layout (fixed):
  1   waste deep-well plate (removed supernatant and washes)
  2,3,9  200 uL filter tips (p300 multi)
  4   Magnetic Module GEN1 + usascientific 2.4 mL deep-well extraction plate
  5   nest 12-channel reservoir: col 2 beads, col 4 elution buffer,
      cols 6-7 isopropanol, cols 9-12 ethanol 70 %
  6   Temperature Module GEN1 + thermo_96_wellplate_200ul elution plate (4 C)
  10  samples 1-24 (2 mL tubes),  7  samples 25-48 (2 mL tubes)
  11  1000 uL filter tips (p1000 single)

Samples occupy the odd columns (1,3,5,7,9,11) of the extraction plate; each eluate
goes to the well with the same name on the elution plate.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'author': 'Implementation of Lazaro-Perona et al. 2021, PLOS ONE 16(2):e0246302',
    'description': 'Mag-Bind TotalPure NGS beads + isopropanol binding, 2x 70% ethanol '
                   'washes, 100 uL elution; 48 samples in odd columns of a deep-well '
                   'plate on a GEN1 magnetic module.',
    'apiLevel': '2.13',
}

# ----------------------------------------------------------------------------
# Volumes (uL) and times from the paper
# ----------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_VOL = 250           # inactivated sample (VTM + GTC)
ISOPROPANOL_VOL = 250      # 1:1 with the sample
BEADS_VOL = 40             # Mag-Bind TotalPure NGS
BINDING_MIX_REPS = 5       # "mix by pipetting five times"
BINDING_INCUBATION_MIN = 5
MAGNET_PULL_MIN = 4
ETHANOL_VOL = 500          # ethanol 70 %, two washes
AIR_DRY_MIN = 4
ELUTION_VOL = 100
ELUTION_RESUSPEND_SEC = 30  # time before engaging the magnet after adding elution buffer
ELUTION_MAGNET_SEC = 90     # time on the magnet before collecting the eluate
TEMP_MODULE_C = 4

SUPERNATANT_VOL = SAMPLE_VOL + ISOPROPANOL_VOL + BEADS_VOL   # 540 uL

SAMPLE_COLUMNS = [0, 2, 4, 6, 8, 10]   # odd columns 1,3,5,7,9,11 (0-based)
MULTI_TIP_MAX = 200                    # 200 uL filter tips on the p300 multi


def split_volume(total, max_vol=MULTI_TIP_MAX):
    """Split a volume into the fewest equal parts that fit the tip capacity."""
    n = int(-(-total // max_vol))      # ceil
    return [total / n] * n


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------ modules
    mag_mod = protocol.load_module('magnetic module', '4')
    temp_mod = protocol.load_module('tempdeck', '6')

    # ------------------------------------------------------------------ labware
    waste_plate = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', '1',
                                        'waste plate')
    mag_plate = mag_mod.load_labware('usascientific_96_wellplate_2.4ml_deep',
                                     'extraction plate')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagent reservoir')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    sample_racks = [
        protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                              '10', 'samples 1-24'),
        protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                              '7', 'samples 25-48'),
    ]
    tips200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in ['2', '3', '9']]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    # ----------------------------------------------------------------- pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=tips1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips200)

    # ----------------------------------------------------------------- reagents
    beads = reservoir.columns()[1][0]            # column 2
    elution_buffer = reservoir.columns()[3][0]   # column 4
    isopropanol = [reservoir.columns()[5][0], reservoir.columns()[6][0]]   # columns 6-7
    ethanol = [reservoir.columns()[i][0] for i in range(8, 12)]            # columns 9-12
    # 6 sample columns: the first 3 draw from the first trough, the last 3 from the second
    isopropanol_for_col = [isopropanol[0]] * 3 + [isopropanol[1]] * 3
    ethanol_for_col = {
        1: [ethanol[0]] * 3 + [ethanol[1]] * 3,   # wash 1: columns 9 and 10
        2: [ethanol[2]] * 3 + [ethanol[3]] * 3,   # wash 2: columns 11 and 12
    }

    # ----------------------------------------------------------------- wells
    sample_cols = [mag_plate.columns()[i] for i in SAMPLE_COLUMNS]       # lists of 8 wells
    sample_col_tops = [col[0] for col in sample_cols]                    # A-row well per column
    waste_col_tops = [waste_plate.columns()[i][0] for i in SAMPLE_COLUMNS]
    elution_col_tops = [elution_plate.columns()[i][0] for i in SAMPLE_COLUMNS]
    sample_wells = [well for col in sample_cols for well in col]         # 48 wells, column-wise
    sample_tubes = (sample_racks[0].wells() + sample_racks[1].wells())[:NUM_SAMPLES]

    # Flow rates: gentle aspiration when removing liquid from pelleted beads
    DEFAULT_M300_ASP = m300.flow_rate.aspirate
    DEFAULT_M300_DISP = m300.flow_rate.dispense
    SLOW_ASP = 25
    SLOW_DISP = 50

    def comment(msg):
        protocol.comment('--- ' + msg)

    # --------------------------------------------------------------- helpers
    def remove_supernatant(volume, destinations, label):
        """Aspirate `volume` from each pelleted sample column (magnet engaged) and
        discard it in the matching column of `destinations`. New tips per column.
        Aspiration is slow, from just above the well bottom, offset away from the pellet."""
        comment('Removing %d uL of %s from each column to the waste plate' % (volume, label))
        m300.flow_rate.aspirate = SLOW_ASP
        m300.flow_rate.dispense = SLOW_DISP
        for src, dest in zip(sample_col_tops, destinations):
            m300.pick_up_tip()
            for vol in split_volume(volume):
                # GEN1 magnets pull the beads to one side of the well; aspirate from
                # the opposite side, just above the bottom.
                m300.aspirate(vol, src.bottom(1.0).move(Point(x=-1.5)))
                m300.air_gap(10)
                m300.dispense(vol + 10, dest.top(-5))
                m300.blow_out(dest.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = DEFAULT_M300_ASP
        m300.flow_rate.dispense = DEFAULT_M300_DISP

    def add_reagent_from_top(volume, source_per_col, label, delay_after_each=None):
        """Dispense `volume` of a reagent into every sample column from above the
        liquid (no contact), using a single set of tips for the whole reagent."""
        comment('Adding %d uL of %s to each sample column' % (volume, label))
        m300.pick_up_tip()
        for src, dest in zip(source_per_col, sample_col_tops):
            for vol in split_volume(volume):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dest.top(-2))
                m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ======================================================================
    # Setup: elution plate at 4 C, magnet disengaged
    # ======================================================================
    comment('Setting the temperature module to %d C for the elution plate' % TEMP_MODULE_C)
    temp_mod.set_temperature(TEMP_MODULE_C)
    mag_mod.disengage()

    # ======================================================================
    # Step 1 -- beads + isopropanol + sample, mix 5x, incubate 5 min RT
    # ======================================================================
    comment('STEP 1: dispensing %d uL magnetic beads per well' % BEADS_VOL)
    m300.pick_up_tip()
    for i, dest in enumerate(sample_col_tops):
        # keep the beads homogeneous: resuspend in the reservoir before each aspiration
        m300.mix(5, 150, beads.bottom(2))
        m300.aspirate(BEADS_VOL, beads.bottom(2))
        m300.dispense(BEADS_VOL, dest.bottom(5))
        m300.blow_out(dest.top(-2))
    m300.drop_tip()

    add_reagent_from_top(ISOPROPANOL_VOL, isopropanol_for_col, 'isopropanol')

    comment('STEP 1: transferring %d uL of each inactivated sample and mixing %d times'
            % (SAMPLE_VOL, BINDING_MIX_REPS))
    for tube, well in zip(sample_tubes, sample_wells):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        # "Mix by pipetting five times" -- mix most of the 540 uL binding mixture
        p1000.mix(BINDING_MIX_REPS, 400, well.bottom(3))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    comment('STEP 1: incubating %d min at room temperature (binding)' % BINDING_INCUBATION_MIN)
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ======================================================================
    # Step 2 -- magnet 4 min
    # ======================================================================
    comment('STEP 2: engaging the GEN1 magnetic module for %d min' % MAGNET_PULL_MIN)
    mag_mod.engage()
    protocol.delay(minutes=MAGNET_PULL_MIN)

    # ======================================================================
    # Step 3 -- collect supernatant and discard
    # ======================================================================
    comment('STEP 3: collecting the binding supernatant')
    remove_supernatant(SUPERNATANT_VOL, waste_col_tops, 'binding supernatant')

    # ======================================================================
    # Steps 4 and 5 -- two washes with 500 uL ethanol 70 % (beads kept on the magnet)
    # ======================================================================
    for wash in (1, 2):
        comment('STEP %d: wash %d with %d uL ethanol 70 %%' % (3 + wash, wash, ETHANOL_VOL))
        add_reagent_from_top(ETHANOL_VOL, ethanol_for_col[wash], 'ethanol 70 %% (wash %d)' % wash)
        remove_supernatant(ETHANOL_VOL, waste_col_tops, 'ethanol 70 %% (wash %d)' % wash)

    # ======================================================================
    # Step 6 -- air dry 4 min
    # ======================================================================
    comment('STEP 6: air drying the beads for %d min' % AIR_DRY_MIN)
    protocol.delay(minutes=AIR_DRY_MIN)

    # ======================================================================
    # Step 7 -- magnet off, add 100 uL elution buffer and resuspend the beads
    # ======================================================================
    comment('STEP 7: disengaging the magnet and adding %d uL elution buffer' % ELUTION_VOL)
    mag_mod.disengage()
    for dest in sample_col_tops:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        # dispense on the pellet side so the beads are washed off the wall
        m300.dispense(ELUTION_VOL, dest.bottom(2).move(Point(x=1.5)))
        m300.mix(10, 80, dest.bottom(1.5))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()

    # ======================================================================
    # Step 8 -- after 30 s, magnet on
    # ======================================================================
    comment('STEP 8: waiting %d s, then engaging the magnet' % ELUTION_RESUSPEND_SEC)
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()

    # ======================================================================
    # Step 9 -- after 90 s, collect the eluate into the elution plate (4 C)
    # ======================================================================
    comment('STEP 9: waiting %d s on the magnet, then collecting the eluates' % ELUTION_MAGNET_SEC)
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    m300.flow_rate.aspirate = SLOW_ASP
    m300.flow_rate.dispense = SLOW_DISP
    for src, dest in zip(sample_col_tops, elution_col_tops):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.8).move(Point(x=-1.5)))
        m300.dispense(ELUTION_VOL, dest.bottom(2))
        m300.blow_out(dest.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = DEFAULT_M300_ASP
    m300.flow_rate.dispense = DEFAULT_M300_DISP

    mag_mod.disengage()
    comment('Extraction finished: %d eluates (%d uL) in the odd columns of the elution '
            'plate on the temperature module at %d C. Beads remain in the extraction plate.'
            % (NUM_SAMPLES, ELUTION_VOL, TEMP_MODULE_C))
