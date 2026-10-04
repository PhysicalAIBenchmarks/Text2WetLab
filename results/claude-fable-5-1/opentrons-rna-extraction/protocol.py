"""
In-house magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2.

Implements the "OT-2 in-house" protocol of Lazaro-Perona et al.,
"Evaluation of two automated low-cost RNA extraction protocols for
SARS-CoV-2 detection", PLOS ONE 16(2): e0246302 (2021),
doi:10.1371/journal.pone.0246302, for 48 inactivated samples.

Paper steps (Methods, "OT-2 in-house protocol" + Table 1):
 1. Deep-well plate: 40 uL magnetic beads + 250 uL isopropanol + 250 uL
    sample per well. Mix by pipetting five times, incubate 5 min at RT.
 2. Engage GEN1 magnetic module, 4 min.
 3. Collect supernatant and discard.
 4. Add 500 uL ethanol 70 %, collect and discard.
 5. Add 500 uL ethanol 70 %, collect and discard.
 6. Air dry 4 min.
 7. Disengage magnet, add 100 uL elution buffer.
 8. After 30 s engage the magnet.
 9. After 90 s collect the supernatant (eluate) into a 96-well plate.

Deck layout (fixed by the operator):
  1   waste deep-well plate (removed supernatant / washes)
  2,3,9  200 uL filter tips (p300 multi)
  4   Magnetic Module GEN1 + USA Scientific 2.4 mL deep-well plate (samples)
  5   NEST 12-well 15 mL reservoir
        col 2  magnetic beads        col 4  elution buffer
        col 6-7 isopropanol          col 9-12 ethanol 70 %
  6   Temperature Module GEN1 + thermo_96_wellplate_200ul (eluates, 4 C)
  10  samples 1-24 (2 mL tubes)      7  samples 25-48 (2 mL tubes)
  11  1000 uL filter tips (p1000 single)
Samples occupy the odd columns (1,3,5,7,9,11) of the magnetic-module plate;
eluates go to the same well positions of the elution plate.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 viral RNA extraction (magnetic beads, 48 samples)',
    'author': 'Implementation of Lazaro-Perona et al. 2021 OT-2 in-house protocol',
    'description': 'Mag-Bind TotalPure NGS beads / isopropanol / 70 % ethanol / '
                   'elution buffer, 48 samples in odd columns, GEN1 magnet + tempdeck',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Protocol parameters (from the paper)
# ---------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = ['1', '3', '5', '7', '9', '11']   # odd columns of the plate

BEAD_VOL = 40           # uL magnetic beads per well
ISO_VOL = 250           # uL isopropanol per well
SAMPLE_VOL = 250        # uL inactivated sample per well
BINDING_VOL = BEAD_VOL + ISO_VOL + SAMPLE_VOL   # 540 uL supernatant to remove
MIX_REPS = 5            # "mix by pipetting five times"
MIX_VOL = 300           # uL mixing volume with the p1000
ETOH_VOL = 500          # uL 70 % ethanol per wash
ELUTION_VOL = 100       # uL elution buffer

BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
AIR_DRY_MIN = 4
ELUTION_SOAK_SEC = 30
ELUTION_MAGNET_SEC = 90

ELUTION_TEMP_C = 4

# p300 multi with 200 uL filter tips: usable volume per stroke
MAX_MULTI_VOL = 180
# Supernatant is aspirated at the well bottom, offset away from the bead
# pellet. On the GEN1 module the beads of the odd (1-based) columns collect
# on the +x side of the well, so the tip is moved to -x.
PELLET_X_OFFSET = -2.0


def split_volume(total, max_vol=MAX_MULTI_VOL):
    """Split `total` uL into the fewest equal strokes of <= max_vol uL."""
    n = int(-(-total // max_vol))          # ceiling division
    return [round(total / n, 2)] * n


def run(protocol: protocol_api.ProtocolContext):

    # -----------------------------------------------------------------------
    # Labware, modules and pipettes
    # -----------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')

    tips200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['2', '3', '9']
    ]
    tips1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    rack_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    rack_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'left', tip_racks=tips1000)
    m300 = protocol.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tips200)

    # -----------------------------------------------------------------------
    # Reagents
    # -----------------------------------------------------------------------
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    isopropanol = [reservoir['A6'], reservoir['A7']]      # 6 mL each
    ethanol_wash1 = [reservoir['A9'], reservoir['A10']]   # 12 mL each
    ethanol_wash2 = [reservoir['A11'], reservoir['A12']]  # 12 mL each

    def reagent_for(column_index, wells):
        """First half of the sample columns use wells[0], the rest wells[1]."""
        half = len(SAMPLE_COLUMNS) // 2
        return wells[0] if column_index < half else wells[1]

    # -----------------------------------------------------------------------
    # Well lists
    # -----------------------------------------------------------------------
    # Multi-channel targets: top well (row A) of each sample column
    mag_cols = [mag_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]
    waste_cols = [waste_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]
    elution_cols = [elution_plate.columns_by_name()[c][0] for c in SAMPLE_COLUMNS]

    # Single-channel sample mapping: tube rack wells are ordered down the
    # columns (A1, B1, C1, D1, A2, ...). Samples 1-24 from slot 10,
    # samples 25-48 from slot 7, filling the odd plate columns top to bottom.
    sample_tubes = rack_1_24.wells() + rack_25_48.wells()
    sample_wells = []
    for c in SAMPLE_COLUMNS:
        sample_wells += mag_plate.columns_by_name()[c]
    sample_tubes = sample_tubes[:NUM_SAMPLES]
    sample_wells = sample_wells[:NUM_SAMPLES]

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def remove_supernatant(volume, destinations, description):
        """Aspirate `volume` uL from every sample column (magnet engaged) and
        discard it in the waste plate. One fresh tip per column."""
        protocol.comment('--- {}: remove {} uL from each well to the waste plate'
                         .format(description, volume))
        m300.flow_rate.aspirate = 40      # slow, keeps the pellet in place
        m300.flow_rate.dispense = 150
        for src, dst in zip(mag_cols, destinations):
            m300.pick_up_tip()
            aspirate_loc = src.bottom(0.5).move(Point(x=PELLET_X_OFFSET))
            for vol in split_volume(volume):
                m300.aspirate(vol, aspirate_loc)
                m300.dispense(vol, dst.top(-5))
                m300.blow_out(dst.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94      # p300 multi GEN2 defaults
        m300.flow_rate.dispense = 94

    def add_ethanol(sources, description):
        """Dispense 500 uL 70 % ethanol onto the pelleted beads of each column
        (magnet engaged, dispensing from above the liquid -> one tip)."""
        protocol.comment('--- {}: add {} uL 70 % ethanol to each well'
                         .format(description, ETOH_VOL))
        m300.pick_up_tip()
        for i, dst in enumerate(mag_cols):
            src = reagent_for(i, sources)
            for vol in split_volume(ETOH_VOL):
                m300.aspirate(vol, src.bottom(2))
                m300.dispense(vol, dst.top(-5))
                m300.blow_out(dst.top(-5))
        m300.drop_tip()

    # -----------------------------------------------------------------------
    # Set-up
    # -----------------------------------------------------------------------
    protocol.comment('Start-up: magnet off, cooling the elution plate to {} C'
                     .format(ELUTION_TEMP_C))
    mag_mod.disengage()
    temp_mod.start_set_temperature(ELUTION_TEMP_C)

    # -----------------------------------------------------------------------
    # Step 1a: 40 uL magnetic beads per well
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 1a: {} uL magnetic beads per well'.format(BEAD_VOL))
    m300.pick_up_tip()
    m300.mix(10, 150, beads.bottom(2))            # resuspend the beads
    for i, dst in enumerate(mag_cols):
        if i > 0:
            m300.mix(3, 150, beads.bottom(2))     # keep beads homogeneous
        m300.aspirate(BEAD_VOL, beads.bottom(2))
        m300.dispense(BEAD_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-5))
    m300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 1b: 250 uL isopropanol per well
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 1b: {} uL isopropanol per well'.format(ISO_VOL))
    m300.pick_up_tip()
    for i, dst in enumerate(mag_cols):
        src = reagent_for(i, isopropanol)
        for vol in split_volume(ISO_VOL):
            m300.aspirate(vol, src.bottom(2))
            m300.dispense(vol, dst.top(-5))
            m300.blow_out(dst.top(-5))
    m300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 1c: 250 uL inactivated sample per well, mix 5x
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 1c: {} uL inactivated sample per well, '
                     'mix by pipetting {} times'.format(SAMPLE_VOL, MIX_REPS))
    for n, (tube, well) in enumerate(zip(sample_tubes, sample_wells), start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        p1000.mix(MIX_REPS, MIX_VOL, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-5)
        p1000.drop_tip()

    # -----------------------------------------------------------------------
    # Step 1d: 5 min binding incubation at room temperature
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 1d: incubate {} min at room temperature'
                     .format(BINDING_INCUBATION_MIN))
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # -----------------------------------------------------------------------
    # Step 2: engage the GEN1 magnetic module, 4 min
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 2: engage magnet, {} min'.format(MAGNET_BINDING_MIN))
    mag_mod.engage()                      # labware default height for GEN1
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # -----------------------------------------------------------------------
    # Step 3: collect and discard the supernatant (540 uL)
    # -----------------------------------------------------------------------
    remove_supernatant(BINDING_VOL, waste_cols, 'Step 3')

    # -----------------------------------------------------------------------
    # Steps 4 and 5: two washes with 500 uL 70 % ethanol (magnet engaged)
    # -----------------------------------------------------------------------
    add_ethanol(ethanol_wash1, 'Step 4 (wash 1)')
    remove_supernatant(ETOH_VOL, waste_cols, 'Step 4 (wash 1)')

    add_ethanol(ethanol_wash2, 'Step 5 (wash 2)')
    remove_supernatant(ETOH_VOL, waste_cols, 'Step 5 (wash 2)')

    # -----------------------------------------------------------------------
    # Step 6: air dry the beads 4 min
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 6: air dry beads {} min'.format(AIR_DRY_MIN))
    protocol.delay(minutes=AIR_DRY_MIN)

    # -----------------------------------------------------------------------
    # Step 7: magnet off, add 100 uL elution buffer and resuspend the beads
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 7: disengage magnet, add {} uL elution buffer per well'
                     .format(ELUTION_VOL))
    mag_mod.disengage()
    for dst in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(10, 80, dst.bottom(1))          # resuspend the bead pellet
        m300.blow_out(dst.top(-5))
        m300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 8: 30 s, then engage the magnet
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 8: wait {} s, then engage magnet'.format(ELUTION_SOAK_SEC))
    protocol.delay(seconds=ELUTION_SOAK_SEC)
    mag_mod.engage()

    # -----------------------------------------------------------------------
    # Step 9: 90 s, then transfer the eluate to the cooled elution plate
    # -----------------------------------------------------------------------
    protocol.comment('--- Step 9: wait {} s, then collect {} uL eluate per well'
                     .format(ELUTION_MAGNET_SEC, ELUTION_VOL))
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    temp_mod.await_temperature(ELUTION_TEMP_C)   # elution plate at 4 C

    m300.flow_rate.aspirate = 30
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(0.5).move(Point(x=PELLET_X_OFFSET)))
        m300.dispense(ELUTION_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    # -----------------------------------------------------------------------
    # End: magnet off, keep the eluates at 4 C on the temperature module
    # -----------------------------------------------------------------------
    mag_mod.disengage()
    protocol.comment('Extraction finished: {} eluates ({} uL) in columns {} of the '
                     'elution plate, held at {} C.'
                     .format(NUM_SAMPLES, ELUTION_VOL, ', '.join(SAMPLE_COLUMNS),
                             ELUTION_TEMP_C))
