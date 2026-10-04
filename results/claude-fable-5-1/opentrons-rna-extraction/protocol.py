"""
SARS-CoV-2 viral RNA extraction with magnetic beads on an Opentrons OT-2
(48 samples per run).

Implementation of the "OT-2 in-house" protocol described in:
    Lazaro-Perona F, Rodriguez-Antolin C, et al. (2021)
    "Evaluation of two automated low-cost RNA extraction protocols for
    SARS-CoV-2 detection". PLoS ONE 16(2): e0246302.
    doi:10.1371/journal.pone.0246302

Protocol as written in the paper (Methods, "OT-2 in-house protocol" and
Table 1), per sample well:
    1. 40 uL magnetic beads + 250 uL isopropanol + 250 uL inactivated
       sample; mix by pipetting five times; incubate 5 min at RT.
    2. Engage the GEN1 magnetic module, 4 min.
    3. Collect and discard the supernatant.
    4. Add 500 uL 70 % ethanol, collect and discard.
    5. Add 500 uL 70 % ethanol, collect and discard.
    6. Air dry 4 min.
    7. Disengage the magnet and add 100 uL elution buffer.
    8. After 30 s engage the magnet.
    9. After 90 s collect the eluate and transfer it to a 96-well plate.

Deck layout (fixed):
    1   waste deep-well plate            usascientific_96_wellplate_2.4ml_deep
    2,3,9  200 uL filter tips (p300 multi)
    4   Magnetic Module GEN1 + extraction plate (usascientific 2.4 mL deep well)
    5   12-column reservoir               nest_12_reservoir_15ml
          col 2  magnetic beads        col 4  elution buffer
          col 6-7 isopropanol          col 9-12 70 % ethanol
    6   Temperature Module GEN1 + elution plate (thermo_96_wellplate_200ul), 4 C
    7   samples 25-48 (2 mL tubes)        opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
    10  samples 1-24  (2 mL tubes)        opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap
    11  1000 uL filter tips (p1000 single)
    12  fixed trash

Samples go to the odd columns (1, 3, 5, 7, 9, 11) of the magnetic-module
plate.  Eluates are recovered into the same well position of the elution
plate on the temperature module.
"""

from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'SARS-CoV-2 magnetic-bead RNA extraction (OT-2 in-house, 48 samples)',
    'author': 'Implemented from Lazaro-Perona et al. 2021, PLoS ONE 16(2):e0246302',
    'description': 'Isopropanol/magnetic-bead binding, two 70 % ethanol washes, '
                   'air drying and 100 uL elution for 48 inactivated samples.',
    'apiLevel': '2.9',
}

# --------------------------------------------------------------------------
# Protocol parameters (from the paper)
# --------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_COLUMNS = [1, 3, 5, 7, 9, 11]        # odd columns of the extraction plate

BEADS_VOL = 40            # uL magnetic beads per sample
ISOPROPANOL_VOL = 250     # uL isopropanol per sample
SAMPLE_VOL = 250          # uL inactivated sample per sample
BINDING_VOL = BEADS_VOL + ISOPROPANOL_VOL + SAMPLE_VOL    # 540 uL supernatant
ETHANOL_VOL = 500         # uL 70 % ethanol per wash
ELUTION_VOL = 100         # uL elution buffer
ELUATE_VOL = 90           # uL recovered (10 uL left behind to avoid carrying beads)

MIX_REPETITIONS = 5       # "mix by pipetting five times"
BINDING_INCUBATION_MIN = 5
MAGNET_MIN = 4
DRYING_MIN = 4
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90
ELUTION_TEMP_C = 4

# Multichannel tips are 200 uL filter tips; keep an air gap for volatile
# solvents so the tips do not drip while travelling over the deck.
AIR_GAP = 20
MAX_TIP_VOL = 200 - AIR_GAP


def run(protocol: protocol_api.ProtocolContext):

    # ----------------------------------------------------------------------
    # Labware, modules and pipettes
    # ----------------------------------------------------------------------
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')

    tipracks_200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', slot,
                              '200 uL filter tips')
        for slot in ['2', '3', '9']]

    mag_mod = protocol.load_module('magnetic module', '4')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')

    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagents')

    temp_mod = protocol.load_module('tempdeck', '6')
    elution_plate = temp_mod.load_labware(
        'thermo_96_wellplate_200ul', 'elution plate')

    tuberack_1_24 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10',
        'samples 1-24')
    tuberack_25_48 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7',
        'samples 25-48')

    tiprack_1000 = protocol.load_labware(
        'opentrons_96_filtertiprack_1000ul', '11', '1000 uL filter tips')

    p1000 = protocol.load_instrument('p1000_single_gen2', 'left',
                                     tip_racks=[tiprack_1000])
    m300 = protocol.load_instrument('p300_multi_gen2', 'right',
                                    tip_racks=tipracks_200)

    # ----------------------------------------------------------------------
    # Reagent map (reservoir columns), well lists
    # ----------------------------------------------------------------------
    beads = reservoir['A2']
    elution_buffer = reservoir['A4']
    # Two reservoir columns per reagent: first three sample columns from the
    # first reservoir column, last three from the second one.
    isopropanol = {1: reservoir['A6'], 3: reservoir['A6'], 5: reservoir['A6'],
                   7: reservoir['A7'], 9: reservoir['A7'], 11: reservoir['A7']}
    ethanol_wash1 = {1: reservoir['A9'], 3: reservoir['A9'], 5: reservoir['A9'],
                     7: reservoir['A10'], 9: reservoir['A10'], 11: reservoir['A10']}
    ethanol_wash2 = {1: reservoir['A11'], 3: reservoir['A11'], 5: reservoir['A11'],
                     7: reservoir['A12'], 9: reservoir['A12'], 11: reservoir['A12']}

    # Multichannel "column" targets (row A well of each column).
    mag_cols = {c: mag_plate['A' + str(c)] for c in SAMPLE_COLUMNS}
    elution_cols = {c: elution_plate['A' + str(c)] for c in SAMPLE_COLUMNS}
    # Supernatant goes to the odd waste columns, both ethanol washes to the
    # neighbouring even column (540 uL and 1000 uL respectively; 2.4 mL wells).
    waste_supernatant = {c: waste_plate['A' + str(c)] for c in SAMPLE_COLUMNS}
    waste_ethanol = {c: waste_plate['A' + str(c + 1)] for c in SAMPLE_COLUMNS}

    # Sample tubes: 1-24 in slot 10, 25-48 in slot 7 (column-major order),
    # placed one per well in the odd columns of the extraction plate.
    sample_tubes = tuberack_1_24.wells() + tuberack_25_48.wells()
    sample_wells = []
    for c in SAMPLE_COLUMNS:
        sample_wells += mag_plate.columns_by_name()[str(c)]
    sample_tubes = sample_tubes[:NUM_SAMPLES]
    sample_wells = sample_wells[:NUM_SAMPLES]

    # On the GEN1 module the bead pellet forms on one side of the well; keep
    # the tip on the opposite side when aspirating over the pellet.
    PELLET_SIDE_OFFSET = -1.5   # mm in x, away from the pellet

    def pellet_safe_bottom(well, z=0.5):
        return well.bottom(z).move(Point(x=PELLET_SIDE_OFFSET))

    def split_volume(total):
        """Split a volume into equal aliquots that fit in a 200 uL tip."""
        n = -(-int(total) // MAX_TIP_VOL)
        return [total / n] * n

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    def add_reagent(source_for_col, volume, air_gap=AIR_GAP, mix_source=None):
        """Dispense `volume` uL of a reagent into every sample column with a
        single multichannel tip, dispensing from above the liquid so the tip
        never touches the sample wells."""
        m300.pick_up_tip()
        if mix_source is not None:
            reps, mix_vol = mix_source
            m300.mix(reps, mix_vol, source_for_col[SAMPLE_COLUMNS[0]].bottom(2))
        for c in SAMPLE_COLUMNS:
            src = source_for_col[c]
            for v in split_volume(volume):
                m300.aspirate(v, src.bottom(2))
                if air_gap:
                    m300.air_gap(air_gap)
                m300.dispense(v + air_gap, mag_cols[c].top(-5))
                m300.blow_out(mag_cols[c].top(-5))
        m300.drop_tip()

    def remove_to_waste(volume, waste_for_col):
        """Aspirate `volume` uL from each sample column (magnet engaged) and
        discard it in the waste plate, one fresh tip per column."""
        for c in SAMPLE_COLUMNS:
            m300.pick_up_tip()
            for v in split_volume(volume):
                m300.aspirate(v, pellet_safe_bottom(mag_cols[c]))
                m300.air_gap(AIR_GAP)
                m300.dispense(v + AIR_GAP, waste_for_col[c].top(-5))
                m300.blow_out(waste_for_col[c].top(-5))
            m300.drop_tip()

    # ----------------------------------------------------------------------
    # Set-up
    # ----------------------------------------------------------------------
    protocol.comment('Setting the temperature module to {} C for the '
                     'elution plate'.format(ELUTION_TEMP_C))
    temp_mod.set_temperature(ELUTION_TEMP_C)
    mag_mod.disengage()

    # Slow flow rates for bead work with the multichannel.
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 150

    # ----------------------------------------------------------------------
    # Step 1: 40 uL beads + 250 uL isopropanol + 250 uL sample, mix 5x,
    #         incubate 5 min at room temperature
    # ----------------------------------------------------------------------
    protocol.comment('Step 1a: {} uL magnetic beads per well'.format(BEADS_VOL))
    # Resuspend the beads in the reservoir before the first aspiration.
    add_reagent({c: beads for c in SAMPLE_COLUMNS}, BEADS_VOL,
                air_gap=0, mix_source=(10, 150))

    protocol.comment('Step 1b: {} uL isopropanol per well'.format(ISOPROPANOL_VOL))
    add_reagent(isopropanol, ISOPROPANOL_VOL)

    protocol.comment('Step 1c: {} uL inactivated sample per well, mixed {} '
                     'times by pipetting'.format(SAMPLE_VOL, MIX_REPETITIONS))
    p1000.flow_rate.aspirate = 300
    p1000.flow_rate.dispense = 300
    for i, (tube, well) in enumerate(zip(sample_tubes, sample_wells)):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(2))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        # Mix beads + isopropanol + sample (540 uL) five times.
        p1000.mix(MIX_REPETITIONS, 400, well.bottom(3))
        p1000.blow_out(well.top(-5))
        p1000.touch_tip(well, v_offset=-5)
        p1000.drop_tip()

    protocol.comment('Step 1d: {} min binding incubation at room '
                     'temperature'.format(BINDING_INCUBATION_MIN))
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # ----------------------------------------------------------------------
    # Step 2: engage the magnet for 4 min
    # ----------------------------------------------------------------------
    protocol.comment('Step 2: engage the magnetic module, {} min'.format(MAGNET_MIN))
    mag_mod.engage()
    protocol.delay(minutes=MAGNET_MIN)

    # ----------------------------------------------------------------------
    # Step 3: collect and discard the supernatant (540 uL)
    # ----------------------------------------------------------------------
    protocol.comment('Step 3: remove {} uL supernatant to the waste '
                     'plate'.format(BINDING_VOL))
    remove_to_waste(BINDING_VOL, waste_supernatant)

    # ----------------------------------------------------------------------
    # Steps 4 and 5: two washes with 500 uL 70 % ethanol (magnet engaged)
    # ----------------------------------------------------------------------
    for wash_no, ethanol in ((1, ethanol_wash1), (2, ethanol_wash2)):
        protocol.comment('Step {}: wash {} - add {} uL 70 % ethanol'.format(
            3 + wash_no, wash_no, ETHANOL_VOL))
        add_reagent(ethanol, ETHANOL_VOL)
        protocol.comment('Step {}: wash {} - collect and discard the '
                         'ethanol'.format(3 + wash_no, wash_no))
        remove_to_waste(ETHANOL_VOL, waste_ethanol)

    # ----------------------------------------------------------------------
    # Step 6: air dry the beads for 4 min
    # ----------------------------------------------------------------------
    protocol.comment('Step 6: air dry the beads, {} min'.format(DRYING_MIN))
    protocol.delay(minutes=DRYING_MIN)

    # ----------------------------------------------------------------------
    # Step 7: disengage the magnet and add 100 uL elution buffer
    # ----------------------------------------------------------------------
    protocol.comment('Step 7: disengage the magnet and add {} uL elution '
                     'buffer, resuspending the beads'.format(ELUTION_VOL))
    mag_mod.disengage()
    m300.flow_rate.aspirate = 100
    m300.flow_rate.dispense = 200
    for c in SAMPLE_COLUMNS:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer.bottom(2))
        m300.dispense(ELUTION_VOL, mag_cols[c].bottom(2))
        # Resuspend the dried bead pellet in the elution buffer.
        m300.mix(10, 80, mag_cols[c].bottom(1))
        m300.blow_out(mag_cols[c].top(-5))
        m300.drop_tip()

    # ----------------------------------------------------------------------
    # Step 8: after 30 s engage the magnet
    # ----------------------------------------------------------------------
    protocol.comment('Step 8: {} s elution, then engage the '
                     'magnet'.format(ELUTION_RESUSPEND_SEC))
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()

    # ----------------------------------------------------------------------
    # Step 9: after 90 s transfer the eluate to the elution plate (4 C)
    # ----------------------------------------------------------------------
    protocol.comment('Step 9: {} s on the magnet, then transfer the eluate '
                     'to the elution plate on the temperature '
                     'module'.format(ELUTION_MAGNET_SEC))
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    m300.flow_rate.aspirate = 25
    m300.flow_rate.dispense = 100
    for c in SAMPLE_COLUMNS:
        m300.pick_up_tip()
        m300.aspirate(ELUATE_VOL, pellet_safe_bottom(mag_cols[c], z=0.5))
        m300.dispense(ELUATE_VOL, elution_cols[c].bottom(1))
        m300.blow_out(elution_cols[c].top(-2))
        m300.touch_tip(elution_cols[c], v_offset=-2)
        m300.drop_tip()

    mag_mod.disengage()
    protocol.comment('Extraction finished: {} eluates ({} uL each) are in the '
                     'odd columns of the elution plate, held at {} C.'.format(
                         NUM_SAMPLES, ELUATE_VOL, ELUTION_TEMP_C))
