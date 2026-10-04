"""
APEX Protocol 1 - Automated heat shock transformation on the Opentrons OT-2.

Reference
---------
Kasprzyk, Herrera and Stracquadanio (2024),
"APEX: Automated Protein EXpression in Escherichia coli",
bioRxiv, doi:10.1101/2024.08.13.607171

Method summary (from the paper)
-------------------------------
"By default, DNA is incubated at 4 C for 30 minutes, heat shocked at 42 C for
30 seconds, and recovered with SOC medium at 37 C for 1 hour."  All temperature
steps are performed on the Thermocycler Module, which the authors chose over the
Temperature Module because its heating/cooling rates are fast enough for a true
heat shock and its lid prevents evaporation without manual plate covers.

Volumes: the paper tested High/Medium/Low Volume configurations (Table 1) and
selected the Low Volume (LV) configuration "for all subsequent experiments".
The LV volumes are stated in the Figure 4 caption: "The automated method used
miniaturised volumes with 10 ul of cells and 50 ul of SOC media as per ...
Low Volume (LV) configuration.  Each transformation was carried out with 1 ul
of DNA at 1.5 x 10-4 pmol."  The deck here supplies plasmid at
1.5 x 10-4 pmol/ul, so 1 ul delivers exactly the 1.5 x 10-4 pmol dose used in
the paper's 8-plasmid panel (pEX01-pEX08, Figure 4).

This protocol runs the 8 transformations of that panel: plasmid well n is
combined with competent-cell well n (A1->A1, B1->B1, ... H1->H1).

Steps after recovery (spotting onto agar, APEX Protocol 2) are out of scope.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - Heat Shock Transformation (8 plasmids, LV)',
    'author': 'Generated from Kasprzyk et al. 2024 (doi:10.1101/2024.08.13.607171)',
    'description': (
        'Automated heat shock transformation of E. coli DH5-alpha with plasmids '
        'pEX01-pEX08 using the APEX Low Volume configuration '
        '(1 uL DNA + 10 uL cells + 50 uL SOC) on the OT-2 Thermocycler Module.'
    ),
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Protocol parameters (APEX Protocol 1 defaults)
# ---------------------------------------------------------------------------

NUM_TRANSFORMATIONS = 8          # pEX01-pEX08, one per row of column 1
DNA_VOLUME = 1                   # uL of plasmid per transformation (LV config)
CELL_VOLUME = 10                 # uL of competent cells, pre-loaded by operator
SOC_VOLUME = 50                  # uL of SOC recovery medium (LV config)

# Total liquid per well once SOC is added.  Passed to the thermocycler as
# block_max_volume so that hold times are counted from when the *liquid*
# (not just the block) has reached the target temperature.
VOLUME_DNA_CELLS = DNA_VOLUME + CELL_VOLUME          # 11 uL
VOLUME_FINAL = VOLUME_DNA_CELLS + SOC_VOLUME         # 61 uL, well under the
                                                     # 200 uL PCR plate limit

COLD_INCUBATION_TEMP = 4         # degC
COLD_INCUBATION_MINUTES = 30

HEAT_SHOCK_TEMP = 42             # degC
HEAT_SHOCK_SECONDS = 30

RECOVERY_TEMP = 37               # degC
RECOVERY_MINUTES = 60

# --- Choices made where the paper leaves the parameter open ----------------
#
# 1. POST-SHOCK COOLING.  The paper specifies the 42 C / 30 s shock and the
#    37 C / 1 h recovery but not what happens between them.  Returning the
#    cells to 4 C before adding SOC is the standard heat shock practice (it
#    stops the shock cleanly and improves viability), and the thermocycler
#    needs the lid opened for the SOC addition anyway.  A 2 minute hold is
#    used: long enough to chill 11 uL, short enough not to stall the run.
POST_SHOCK_TEMP = 4              # degC
POST_SHOCK_MINUTES = 2

# 2. LID TEMPERATURE.  The paper does not state a lid setpoint.  The GEN1
#    thermocycler lid has a 37 C minimum, so it is held at 37 C for the whole
#    run: that is the lowest available setting, it suppresses condensation on
#    the seal, and it will not warm a 4 C block step the way a 105 C PCR lid
#    would.
LID_TEMP = 37                    # degC

# 3. MIXING.  Chemically competent cells are damaged by vigorous handling, so
#    both mixing steps use a small number of slow strokes rather than the
#    pipette's default flow rates (see gentle_mix below).
MIX_REPETITIONS = 3
GENTLE_FLOW_MULTIPLIER = 0.5     # fraction of the default aspirate/dispense rate


def run(protocol: protocol_api.ProtocolContext):

    # -----------------------------------------------------------------------
    # Deck setup (fixed by the operator)
    # -----------------------------------------------------------------------
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    # Thermocycler Module GEN1 occupies slots 7, 8, 10 and 11.
    tc = protocol.load_module('thermocycler')
    transformation_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # -----------------------------------------------------------------------
    # Wells
    # -----------------------------------------------------------------------
    # Transformation n uses plasmid well n and cell well n (A1->A1, ...).
    plasmid_wells = plasmid_plate.columns()[0][:NUM_TRANSFORMATIONS]
    cell_wells = transformation_plate.columns()[0][:NUM_TRANSFORMATIONS]
    soc = soc_reservoir['A1']

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def pick_up(pipette):
        """Pick up a tip, recycling the rack when it is exhausted.

        Tips are unlimited on this deck: the operator replaces a spent rack,
        so resetting the tip tracker is the correct response to running out.
        """
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def gentle_mix(pipette, repetitions, volume, well):
        """Mix slowly so the competent cells are not sheared."""
        default_aspirate = pipette.flow_rate.aspirate
        default_dispense = pipette.flow_rate.dispense
        pipette.flow_rate.aspirate = default_aspirate * GENTLE_FLOW_MULTIPLIER
        pipette.flow_rate.dispense = default_dispense * GENTLE_FLOW_MULTIPLIER
        pipette.mix(repetitions, volume, well)
        pipette.flow_rate.aspirate = default_aspirate
        pipette.flow_rate.dispense = default_dispense

    # =======================================================================
    # Step 0 - Prepare the thermocycler
    # =======================================================================
    # The operator has already loaded the competent cells onto a pre-chilled
    # block.  Re-assert 4 C (no hold: this only starts the block cooling and
    # returns immediately) and open the lid so the plate can be pipetted into.
    tc.set_lid_temperature(LID_TEMP)
    tc.open_lid()
    tc.set_block_temperature(COLD_INCUBATION_TEMP)

    protocol.comment(
        'Thermocycler block at {} C with the lid open; '
        'adding plasmid DNA to the competent cells.'.format(
            COLD_INCUBATION_TEMP))

    # =======================================================================
    # Step 1 - Add 1 uL of each plasmid to its competent cell aliquot
    # =======================================================================
    # A fresh tip per transformation: carrying DNA between wells would
    # cross-contaminate the panel.
    for index, (plasmid, cells) in enumerate(zip(plasmid_wells, cell_wells), start=1):
        pick_up(p20)
        p20.aspirate(DNA_VOLUME, plasmid.bottom(z=1))
        p20.dispense(DNA_VOLUME, cells.bottom(z=1))
        gentle_mix(p20, MIX_REPETITIONS, VOLUME_DNA_CELLS / 2, cells.bottom(z=1))
        p20.blow_out(cells.top(z=-2))
        p20.drop_tip()
        protocol.comment(
            'Transformation {}: {} uL plasmid pEX0{} added to {} uL cells.'.format(
                index, DNA_VOLUME, index, CELL_VOLUME))

    # =======================================================================
    # Step 2 - Incubate the DNA with the cells at 4 C for 30 minutes
    # =======================================================================
    tc.close_lid()
    protocol.comment('Incubating DNA and cells at {} C for {} minutes.'.format(
        COLD_INCUBATION_TEMP, COLD_INCUBATION_MINUTES))
    tc.set_block_temperature(
        temperature=COLD_INCUBATION_TEMP,
        hold_time_minutes=COLD_INCUBATION_MINUTES,
        block_max_volume=VOLUME_DNA_CELLS)

    # =======================================================================
    # Step 3 - Heat shock at 42 C for 30 seconds
    # =======================================================================
    protocol.comment('Heat shock: {} C for {} seconds.'.format(
        HEAT_SHOCK_TEMP, HEAT_SHOCK_SECONDS))
    tc.set_block_temperature(
        temperature=HEAT_SHOCK_TEMP,
        hold_time_seconds=HEAT_SHOCK_SECONDS,
        block_max_volume=VOLUME_DNA_CELLS)

    # =======================================================================
    # Step 4 - Return to 4 C before adding SOC (see note 1 above)
    # =======================================================================
    protocol.comment('Cooling back to {} C for {} minutes after the shock.'.format(
        POST_SHOCK_TEMP, POST_SHOCK_MINUTES))
    tc.set_block_temperature(
        temperature=POST_SHOCK_TEMP,
        hold_time_minutes=POST_SHOCK_MINUTES,
        block_max_volume=VOLUME_DNA_CELLS)

    # =======================================================================
    # Step 5 - Add 50 uL of SOC medium to each transformation
    # =======================================================================
    tc.open_lid()
    # Pre-warm the block to the recovery temperature while SOC is dispensed, so
    # the outgrowth starts at 37 C as soon as the lid closes.
    tc.set_block_temperature(RECOVERY_TEMP)

    # 50 uL is in range for the P300 only (the P20 tops out at 20 uL).
    # A fresh tip per well again: the tip enters wells that already contain
    # transformed cells, so one shared tip would cross-contaminate them.
    for index, cells in enumerate(cell_wells, start=1):
        pick_up(p300)
        p300.aspirate(SOC_VOLUME, soc)
        p300.dispense(SOC_VOLUME, cells.bottom(z=2))
        gentle_mix(p300, MIX_REPETITIONS, SOC_VOLUME / 2, cells.bottom(z=2))
        p300.blow_out(cells.top(z=-2))
        p300.drop_tip()
        protocol.comment(
            'Transformation {}: {} uL SOC added (total {} uL).'.format(
                index, SOC_VOLUME, VOLUME_FINAL))

    # =======================================================================
    # Step 6 - Recover at 37 C for 1 hour
    # =======================================================================
    tc.close_lid()
    protocol.comment('Recovery outgrowth: {} C for {} minutes.'.format(
        RECOVERY_TEMP, RECOVERY_MINUTES))
    tc.set_block_temperature(
        temperature=RECOVERY_TEMP,
        hold_time_minutes=RECOVERY_MINUTES,
        block_max_volume=VOLUME_FINAL)

    # =======================================================================
    # Step 7 - Present the plate to the operator
    # =======================================================================
    # Deactivate the lid heater and open the lid so the recovered outgrowths
    # can be removed for APEX Protocol 2 (spotting on selective agar).
    # The block is held at 4 C rather than deactivated: if the plate is not
    # collected immediately, cold storage limits further outgrowth and
    # evaporation.
    tc.deactivate_lid()
    tc.set_block_temperature(4)
    tc.open_lid()

    protocol.comment(
        'APEX Protocol 1 complete: {} transformations recovered in {} uL. '
        'Block held at 4 C. Proceed to APEX Protocol 2 (spotting).'.format(
            NUM_TRANSFORMATIONS, VOLUME_FINAL))
