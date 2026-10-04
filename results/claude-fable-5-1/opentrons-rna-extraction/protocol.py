"""
Magnetic-bead SARS-CoV-2 RNA extraction on the Opentrons OT-2 (48 samples).

Implementation of the "OT-2 in-house" protocol described in:
  Automated low-cost SARS-CoV-2 RNA extraction protocols.
  PLOS ONE (2021), doi:10.1371/journal.pone.0246302

Paper protocol (OT-2 in-house), reproduced step by step:
  1. Dispense in a deep-well plate 40 uL magnetic beads, 250 uL isopropanol
     and 250 uL sample per well. Mix by pipetting five times and incubate
     5 min at room temperature.
  2. Activate the GEN1 magnetic module 4 min.
  3. Collect the supernatant and discard.
  4. Add 500 uL ethanol 70 %, collect and discard.
  5. Add 500 uL ethanol 70 %, collect and discard.
  6. Air dry for 4 min.
  7. Turn off the GEN1 magnetic module and add 100 uL elution buffer.
  8. After 30 s turn on the GEN1 magnetic module.
  9. After 90 s collect the supernatant and transfer to a 96-well plate.

Deck layout (fixed by the operator):
  1      waste deep-well plate (supernatant / washes)
  2,3,9  200 uL filter tips (p300 multi)
  4      Magnetic Module GEN1 + sample/extraction deep-well plate
  5      12-column reservoir: col 2 beads, col 4 elution buffer,
         cols 6-7 isopropanol, cols 9-12 70 % ethanol
  6      Temperature Module GEN1 (4 C) + elution plate (thermo_96_wellplate_200ul)
  7      samples 25-48 (2 mL tubes)      10  samples 1-24 (2 mL tubes)
  11     1000 uL filter tips (p1000 single)
Samples occupy the odd columns (1, 3, 5, 7, 9, 11) of the magnetic-module
plate; each eluate goes to the same well position of the elution plate.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'OT-2 in-house magnetic-bead SARS-CoV-2 RNA extraction (48 samples)',
    'author': 'Automated from PLOS ONE 2021, doi:10.1371/journal.pone.0246302',
    'description': 'Beads/isopropanol binding, 2x 70% ethanol washes, elution in 100 uL',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Protocol parameters (from the paper)
# ---------------------------------------------------------------------------
NUM_SAMPLES = 48
SAMPLE_VOL = 250          # uL inactivated sample
ISOPROPANOL_VOL = 250     # uL
BEADS_VOL = 40            # uL Mag-Bind TotalPure NGS beads
BINDING_MIX_REPS = 5      # "mix by pipetting five times"
BINDING_INCUBATION_MIN = 5
MAGNET_BINDING_MIN = 4
ETHANOL_VOL = 500         # uL 70 % ethanol per wash
NUM_WASHES = 2
AIR_DRY_MIN = 4
ELUTION_VOL = 100         # uL elution buffer
ELUTION_RESUSPEND_SEC = 30
ELUTION_MAGNET_SEC = 90
TEMP_MODULE_C = 4

# Liquid-handling details not fixed by the paper
MULTI_MAX_VOL = 200       # 200 uL filter tips on the p300 multi
BINDING_TOTAL_VOL = SAMPLE_VOL + ISOPROPANOL_VOL + BEADS_VOL   # 540 uL
SUPERNATANT_REMOVAL_VOL = BINDING_TOTAL_VOL                    # 540 uL
WASH_REMOVAL_VOL = ETHANOL_VOL + 10     # slight over-draw to leave the pellet dry
ASPIRATE_Z = 0.8          # mm above the well bottom when removing liquid from pelleted beads
SLOW_ASPIRATE_RATE = 40   # uL/s for supernatant removal over the bead pellet (p300 default is 94)

# Sample columns on the magnetic-module plate (0-based indices of odd columns)
SAMPLE_COLUMN_IDX = [0, 2, 4, 6, 8, 10]


def split_volume(volume, max_vol):
    """Split *volume* into full *max_vol* aliquots plus one remainder aliquot."""
    chunks = []
    remaining = volume
    while remaining > 0:
        vol = min(max_vol, remaining)
        chunks.append(vol)
        remaining -= vol
    return chunks


def run(protocol: protocol_api.ProtocolContext):

    # ---------------------------------------------------------------- modules
    mag_mod = protocol.load_module('magnetic module', '4')
    temp_mod = protocol.load_module('tempdeck', '6')

    # ---------------------------------------------------------------- labware
    waste_plate = protocol.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'waste plate')
    mag_plate = mag_mod.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', 'extraction plate')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '5', 'reagent reservoir')
    elution_plate = temp_mod.load_labware('thermo_96_wellplate_200ul', 'elution plate')
    sample_rack_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10', 'samples 1-24')
    sample_rack_2 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7', 'samples 25-48')

    tips_200 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', s)
                for s in ['2', '3', '9']]
    tips_1000 = [protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')]

    # --------------------------------------------------------------- pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=tips_1000)
    m300 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips_200)

    # --------------------------------------------------------------- reagents
    beads = reservoir.columns()[1][0]                      # column 2
    elution_buffer = reservoir.columns()[3][0]             # column 4
    isopropanol = [reservoir.columns()[i][0] for i in (5, 6)]      # columns 6-7
    ethanol = [reservoir.columns()[i][0] for i in (8, 9, 10, 11)]  # columns 9-12
    # 3 plate columns (24 wells) are served by each reservoir column:
    #   isopropanol: 24 x 250 uL = 6 mL per reservoir column
    #   ethanol:     24 x 500 uL = 12 mL per reservoir column, 2 columns per wash
    ethanol_per_wash = [ethanol[0:2], ethanol[2:4]]

    # ------------------------------------------------------------ well lists
    # Multi-channel "A" wells of the 6 sample columns on each plate
    mag_cols = [mag_plate.columns()[i][0] for i in SAMPLE_COLUMN_IDX]
    waste_cols = [waste_plate.columns()[i][0] for i in SAMPLE_COLUMN_IDX]
    elution_cols = [elution_plate.columns()[i][0] for i in SAMPLE_COLUMN_IDX]

    # Single-channel sample mapping: sample n -> tube -> extraction well
    sample_tubes = sample_rack_1.wells()[:24] + sample_rack_2.wells()[:24]
    sample_wells = [well for i in SAMPLE_COLUMN_IDX for well in mag_plate.columns()[i]]
    assert len(sample_tubes) == len(sample_wells) == NUM_SAMPLES

    # ------------------------------------------------------------- helpers
    def remove_to_waste(volume, comment):
        """Aspirate *volume* from every sample column (beads on magnet) into the
        waste plate, one fresh tip per column, slow aspiration near the bottom."""
        protocol.comment(comment)
        m300.flow_rate.aspirate = SLOW_ASPIRATE_RATE
        for src, dst in zip(mag_cols, waste_cols):
            m300.pick_up_tip()
            for vol in split_volume(volume, MULTI_MAX_VOL - 20):
                m300.aspirate(vol, src.bottom(ASPIRATE_Z))
                m300.air_gap(20)
                m300.dispense(vol + 20, dst.top(-5))
                m300.blow_out(dst.top(-5))
            m300.drop_tip()
        m300.flow_rate.aspirate = 94  # p300 multi GEN2 default

    def add_reagent(volume, sources, comment, dispense_loc='top'):
        """Dispense *volume* of a reagent into every sample column with a single
        tip (reagent only, dispensed from above the liquid so the tip stays clean).
        *sources* is a list of reservoir wells; 3 plate columns per reservoir well."""
        protocol.comment(comment)
        m300.pick_up_tip()
        for i, dst in enumerate(mag_cols):
            src = sources[i // 3] if len(sources) > 1 else sources[0]
            for vol in split_volume(volume, MULTI_MAX_VOL):
                m300.aspirate(vol, src)
                if dispense_loc == 'top':
                    m300.dispense(vol, dst.top(-2))
                else:
                    m300.dispense(vol, dst.bottom(5))
                m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # =======================================================================
    # Set-up: keep the elution plate cold
    # =======================================================================
    temp_mod.set_temperature(TEMP_MODULE_C)
    mag_mod.disengage()

    # =======================================================================
    # Step 1 - Reagent mix: 40 uL beads + 250 uL isopropanol + 250 uL sample,
    #          mix 5 times, incubate 5 min at room temperature
    # =======================================================================
    # Resuspend the bead stock before use, then dispense 40 uL per well.
    protocol.comment('Step 1a: dispensing %d uL of magnetic beads per well' % BEADS_VOL)
    m300.pick_up_tip()
    m300.mix(10, 150, beads)
    for dst in mag_cols:
        m300.aspirate(BEADS_VOL, beads)
        m300.dispense(BEADS_VOL, dst.bottom(5))
        m300.blow_out(dst.top(-2))
    m300.drop_tip()

    add_reagent(ISOPROPANOL_VOL, isopropanol,
                'Step 1b: dispensing %d uL of isopropanol per well' % ISOPROPANOL_VOL)

    protocol.comment('Step 1c: transferring %d uL of each inactivated sample, mixing %d times'
                     % (SAMPLE_VOL, BINDING_MIX_REPS))
    p1000.flow_rate.aspirate = 150   # gentle handling of viscous inactivated samples
    p1000.flow_rate.dispense = 150
    for n, (tube, well) in enumerate(zip(sample_tubes, sample_wells), start=1):
        p1000.pick_up_tip()
        p1000.aspirate(SAMPLE_VOL, tube.bottom(3))
        p1000.dispense(SAMPLE_VOL, well.bottom(5))
        # "Mix by pipetting five times": 300 uL of the 540 uL binding mix
        p1000.mix(BINDING_MIX_REPS, 300, well.bottom(3))
        p1000.blow_out(well.top(-2))
        p1000.drop_tip()

    protocol.comment('Step 1d: incubating %d min at room temperature' % BINDING_INCUBATION_MIN)
    protocol.delay(minutes=BINDING_INCUBATION_MIN)

    # =======================================================================
    # Step 2 - Magnet on for 4 min
    # =======================================================================
    protocol.comment('Step 2: engaging the magnetic module for %d min' % MAGNET_BINDING_MIN)
    mag_mod.engage()
    protocol.delay(minutes=MAGNET_BINDING_MIN)

    # =======================================================================
    # Step 3 - Collect and discard the supernatant
    # =======================================================================
    remove_to_waste(SUPERNATANT_REMOVAL_VOL,
                    'Step 3: removing %d uL of supernatant to the waste plate'
                    % SUPERNATANT_REMOVAL_VOL)

    # =======================================================================
    # Steps 4 & 5 - Two washes with 500 uL 70 % ethanol (beads kept on magnet)
    # =======================================================================
    for w in range(NUM_WASHES):
        add_reagent(ETHANOL_VOL, ethanol_per_wash[w],
                    'Step %d: wash %d - adding %d uL of 70%% ethanol per well'
                    % (4 + w, w + 1, ETHANOL_VOL))
        remove_to_waste(WASH_REMOVAL_VOL,
                        'Step %d: wash %d - removing the ethanol to the waste plate'
                        % (4 + w, w + 1))

    # =======================================================================
    # Step 6 - Air dry 4 min
    # =======================================================================
    protocol.comment('Step 6: air drying the beads for %d min' % AIR_DRY_MIN)
    protocol.delay(minutes=AIR_DRY_MIN)

    # =======================================================================
    # Step 7 - Magnet off, add 100 uL elution buffer and resuspend the beads
    # =======================================================================
    protocol.comment('Step 7: disengaging the magnet and adding %d uL of elution buffer'
                     % ELUTION_VOL)
    mag_mod.disengage()
    for dst in mag_cols:
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, elution_buffer)
        m300.dispense(ELUTION_VOL, dst.bottom(1))
        m300.mix(10, 80, dst.bottom(1))       # resuspend the bead pellet
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    # =======================================================================
    # Step 8 - After 30 s, magnet on
    # =======================================================================
    protocol.comment('Step 8: %d s elution, then engaging the magnet' % ELUTION_RESUSPEND_SEC)
    protocol.delay(seconds=ELUTION_RESUSPEND_SEC)
    mag_mod.engage()

    # =======================================================================
    # Step 9 - After 90 s, transfer the eluate to the elution plate (4 C)
    # =======================================================================
    protocol.comment('Step 9: %d s on the magnet, then transferring %d uL of eluate'
                     % (ELUTION_MAGNET_SEC, ELUTION_VOL))
    protocol.delay(seconds=ELUTION_MAGNET_SEC)
    m300.flow_rate.aspirate = SLOW_ASPIRATE_RATE
    for src, dst in zip(mag_cols, elution_cols):
        m300.pick_up_tip()
        m300.aspirate(ELUTION_VOL, src.bottom(ASPIRATE_Z))
        m300.dispense(ELUTION_VOL, dst.bottom(2))
        m300.blow_out(dst.top(-2))
        m300.drop_tip()
    m300.flow_rate.aspirate = 94

    mag_mod.disengage()
    protocol.comment('Extraction finished: %d eluates (%d uL) in the elution plate '
                     'on the temperature module at %d C.' % (NUM_SAMPLES, ELUTION_VOL, TEMP_MODULE_C))
