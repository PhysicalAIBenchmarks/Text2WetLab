"""APEX Protocol 1: automated heat shock transformation on the OT-2 thermocycler.

Implements the heat shock transformation module of APEX (Kasprzyk, Herrera &
Stracquadanio, "APEX: Automated Protein EXpression in Escherichia coli",
bioRxiv 2024, doi:10.1101/2024.08.13.607171) for 8 plasmids (pEX01-pEX08).

Parameters taken from the paper:
  - Low Volume (LV) transformation configuration, selected by the authors for
    all subsequent automated experiments (Results > Optimisation of
    transformation volume). Per the Figure 4 caption, the LV/automated run
    uses 1 uL of DNA (1.5e-4 pmol), 10 uL of cells and 50 uL of SOC medium.
  - Temperature program (Results > Protocol 1): DNA incubated at 4 C for
    30 minutes, heat shock at 42 C for 30 seconds, recovery with SOC at 37 C
    for 1 hour. All steps run on the thermocycler module, which the paper
    chose over a temperature module for its rapid temperature changes.

Choices made where the paper leaves things open (documented here as required):
  - The paper does not mention a post-shock ice step; after the 42 C shock the
    block is set back to 4 C while SOC is added, keeping cells cold.
  - The paper does not specify mixing; a gentle pipette mix after adding DNA
    and after adding SOC is performed to homogenise each transformation.
  - A heated lid (105 C, the thermocycler default used to prevent
    evaporation/condensation during closed-lid incubations) is kept on for
    every closed-lid step, matching the paper's rationale for using the
    thermocycler instead of the temperature module.
  - One fresh tip per plasmid to avoid cross-contamination.

Deck setup (fixed by the operator):
  slot 1: biorad_96_wellplate_200ul_pcr 'plasmid_plate'
          A1..H1: plasmids pEX01..pEX08, 10 uL each (1.5e-4 pmol/uL)
  slot 2: nest_12_reservoir_15ml 'soc_reservoir', A1: SOC medium
  slots 7/8/10/11: Thermocycler Module GEN1 holding
          biorad_96_wellplate_200ul_pcr 'transformation_plate'
          A1..H1: competent E. coli DH5a, 10 uL each (pre-chilled block)
  slot 4: opentrons_96_tiprack_20ul, slot 5: opentrons_96_tiprack_300ul
  left: p20_single_gen2 (1-20 uL), right: p300_single_gen2 (20-300 uL)
"""

metadata = {
    'protocolName': 'APEX Protocol 1: heat shock transformation (LV configuration)',
    'author': 'Generated from Kasprzyk et al., bioRxiv 2024, doi:10.1101/2024.08.13.607171',
    'apiLevel': '2.15',
}

# LV configuration volumes (paper: 1 uL DNA + 10 uL cells + 50 uL SOC).
DNA_VOLUME = 1          # uL, plasmid DNA (1.5e-4 pmol per transformation)
CELL_VOLUME = 10        # uL, competent cells already in the plate
SOC_VOLUME = 50         # uL, SOC recovery medium
SHOCK_VOLUME = DNA_VOLUME + CELL_VOLUME            # 11 uL during incubation/shock
RECOVERY_VOLUME = SHOCK_VOLUME + SOC_VOLUME        # 61 uL during recovery

# Temperature program (paper's Protocol 1 defaults).
INCUBATION_TEMP = 4     # C
INCUBATION_MIN = 30
SHOCK_TEMP = 42         # C
SHOCK_SEC = 30
RECOVERY_TEMP = 37      # C
RECOVERY_MIN = 60

PLASMID_WELLS = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']


def run(protocol):
    # --- Labware and instruments (fixed deck layout) ---------------------
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')

    tc = protocol.load_module('thermocycler')
    transformation_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    # 1 uL DNA -> p20 (1-20 uL); 50 uL SOC -> p300 (20-300 uL).
    p20 = protocol.load_instrument('p20_single_gen2', 'left',
                                   tip_racks=[tips_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips_300])

    cell_wells = transformation_plate.rows()[0]  # A1..H1
    soc = soc_reservoir['A1']

    # --- Setup: keep the pre-chilled block cold while pipetting ----------
    tc.open_lid()
    tc.set_block_temperature(INCUBATION_TEMP)
    protocol.comment('Block chilled to 4 C; adding DNA to competent cells.')

    # --- Add DNA: transformation n gets plasmid well n -> cell well n ----
    # Fresh tip per plasmid to avoid cross-contamination; gentle mix after
    # dispensing (choice: paper does not specify mixing).
    for i, well_name in enumerate(PLASMID_WELLS):
        p20.pick_up_tip()
        p20.aspirate(DNA_VOLUME, plasmid_plate[well_name])
        p20.dispense(DNA_VOLUME, cell_wells[i])
        p20.mix(3, 5, cell_wells[i])
        p20.drop_tip()

    # --- Closed-lid temperature program: incubation + heat shock ---------
    tc.set_lid_temperature(105)  # heated lid prevents evaporation/condensation
    tc.close_lid()

    protocol.comment('Incubating DNA + cells: 30 min at 4 C.')
    tc.set_block_temperature(INCUBATION_TEMP,
                             hold_time_minutes=INCUBATION_MIN,
                             block_max_volume=SHOCK_VOLUME)

    protocol.comment('Heat shock: 30 s at 42 C.')
    tc.set_block_temperature(SHOCK_TEMP,
                             hold_time_seconds=SHOCK_SEC,
                             block_max_volume=SHOCK_VOLUME)

    # Back to 4 C while SOC is added (choice: paper specifies no explicit
    # post-shock ice step; this keeps the cells cold during handling).
    tc.set_block_temperature(INCUBATION_TEMP, block_max_volume=SHOCK_VOLUME)
    tc.open_lid()

    # --- Add SOC recovery medium ------------------------------------------
    for i, well_name in enumerate(PLASMID_WELLS):
        p300.pick_up_tip()
        p300.aspirate(SOC_VOLUME, soc)
        p300.dispense(SOC_VOLUME, cell_wells[i])
        p300.mix(3, 40, cell_wells[i])  # homogenise 61 uL recovery mix
        p300.drop_tip()

    # --- Recovery: 1 h at 37 C --------------------------------------------
    tc.close_lid()
    protocol.comment('Recovery: 60 min at 37 C with SOC.')
    tc.set_block_temperature(RECOVERY_TEMP,
                             hold_time_minutes=RECOVERY_MIN,
                             block_max_volume=RECOVERY_VOLUME)

    # --- End state: cells held cold until Protocol 2 (spotting) ----------
    tc.open_lid()
    tc.deactivate_lid()
    tc.set_block_temperature(INCUBATION_TEMP)
    protocol.comment('Transformation complete: recovered cultures held at '
                     '4 C. Proceed to APEX Protocol 2 (spotting on agar).')
