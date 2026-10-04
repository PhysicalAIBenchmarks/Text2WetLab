"""
APEX Protocol 1 - Automated heat shock transformation on the Opentrons OT-2.

Reference
---------
Kasprzyk, Herrera and Stracquadanio, "APEX: Automated Protein EXpression in
Escherichia coli", bioRxiv 2024, doi:10.1101/2024.08.13.607171

Method parameters taken from the paper
--------------------------------------
Thermal programme (Results > Protocol 1 - Heat shock transformations):
    "By default, DNA is incubated at 4 C for 30 minutes, heat shocked at 42 C
     for 30 seconds, and recovered with SOC medium at 37 C for 1 hour."
  All three temperature steps are executed on the Thermocycler Module, which the
  paper selected over the Temperature Module because its warm-up / cool-down
  rates are fast enough for a true heat shock.

Transformation volumes - "Low Volume" (LV) configuration:
  Table 1 lists the HV / MV / LV configurations; the LV numbers are stated in the
  Figure 4 legend: "The automated method used miniaturised volumes with 10 ul of
  cells and 50 ul of SOC media as per [...] Low Volume (LV) configuration", with
  "Each transformation was carried out with 1 ul of DNA at 1.5 x 10-4 pmol".
  LV was "selected for all subsequent experiments" because it gave the highest
  transformation efficiency for pEX05 (Results > Optimisation of transformation
  volume), so LV is what this protocol implements:
      DNA   :  1 ul   (1.5 x 10-4 pmol/ul -> 1.5 x 10-4 pmol per transformation)
      cells : 10 ul   (pre-loaded by the operator)
      SOC   : 50 ul
  Final volume per well = 61 ul, well within the 200 ul PCR plate the paper
  specifies for the thermocycler.

Scope: 8 transformations, plasmids pEX01-pEX08 (the plasmid-size panel of
Figure 4), transformation n uses plasmid well n and cell well n. Everything
downstream of the SOC recovery (spotting, Protocol 2) is out of scope.

Choices the paper leaves open are marked "CHOICE:" in the comments below.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'APEX Protocol 1 - Heat shock transformation (LV, 8 plasmids)',
    'author': 'Generated for APEX (doi:10.1101/2024.08.13.607171)',
    'description': (
        'Automated heat shock transformation of E. coli DH5-alpha with plasmids '
        'pEX01-pEX08 using the APEX Low Volume configuration (1 ul DNA, 10 ul '
        'cells, 50 ul SOC) and the OT-2 Thermocycler Module.'
    ),
    'apiLevel': '2.15',
}

# ---------------------------------------------------------------------------
# Method parameters (all from the paper)
# ---------------------------------------------------------------------------
NUM_TRANSFORMATIONS = 8          # pEX01 - pEX08
DNA_VOLUME = 1.0                 # ul, LV configuration
CELL_VOLUME = 10.0               # ul, LV configuration (pre-loaded on deck)
SOC_VOLUME = 50.0                # ul, LV configuration

INCUBATION_TEMP = 4              # degC
INCUBATION_MINUTES = 30
HEAT_SHOCK_TEMP = 42             # degC
HEAT_SHOCK_SECONDS = 30
RECOVERY_TEMP = 37               # degC
RECOVERY_MINUTES = 60

# CHOICE: the paper does not state a post-shock return to ice. Returning the
# block to 4 degC for 2 min before adding SOC is universal in the Hanahan-style
# manual protocols that APEX miniaturises (and is what the supplier protocol the
# paper benchmarks against prescribes), so it is included here. The thermocycler
# would in any case have to ramp off 42 degC before SOC is added.
POST_SHOCK_MINUTES = 2

# Volume of the deepest liquid in the block, used by the thermocycler to decide
# when the *sample* (not just the block) has reached temperature.
VOLUME_BEFORE_SOC = DNA_VOLUME + CELL_VOLUME          # 11 ul
VOLUME_AFTER_SOC = VOLUME_BEFORE_SOC + SOC_VOLUME     # 61 ul

# CHOICE: the paper does not specify a lid temperature. The thermocycler lid is
# left unheated for the cold steps (heating it would warm the 4 degC samples) and
# set to 37 degC - the module's minimum - for the 1 h recovery, which matches the
# block and so suppresses condensation without over-heating the outgrowth.
RECOVERY_LID_TEMP = 37


def run(protocol: protocol_api.ProtocolContext):

    # -----------------------------------------------------------------------
    # Deck
    # -----------------------------------------------------------------------
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    # Thermocycler Module GEN1 - occupies slots 7, 8, 10 and 11.
    tc = protocol.load_module('thermocycler')
    transformation_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Competent cells are fragile and the DNA volume is at the p20's 1 ul floor,
    # so both pipettes are slowed down for gentle, accurate handling.
    p20.flow_rate.aspirate = 3
    p20.flow_rate.dispense = 3
    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 50

    def pick_up(pipette):
        """Pick up a tip, recycling the rack when it runs out (tips are unlimited)."""
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    # Source and destination wells, paired A1->A1 ... H1->H1.
    plasmid_wells = plasmid_plate.columns()[0][:NUM_TRANSFORMATIONS]
    cell_wells = transformation_plate.columns()[0][:NUM_TRANSFORMATIONS]
    soc = soc_reservoir.wells_by_name()['A1']
    plasmid_names = ['pEX%02d' % (i + 1) for i in range(NUM_TRANSFORMATIONS)]

    # -----------------------------------------------------------------------
    # Step 0 - pre-chill the block
    # -----------------------------------------------------------------------
    # The operator loaded the competent cells onto a pre-chilled block, so the
    # block is driven to 4 degC (and the lid opened for pipetting) before any
    # liquid is moved. set_block_temperature blocks until the target is reached.
    tc.open_lid()
    tc.set_block_temperature(INCUBATION_TEMP)
    protocol.comment(
        'Block held at %d C. Adding DNA to competent cells (LV: %g ul DNA into '
        '%g ul cells).' % (INCUBATION_TEMP, DNA_VOLUME, CELL_VOLUME))

    # -----------------------------------------------------------------------
    # Step 1 - add 1 ul plasmid DNA to each 10 ul aliquot of competent cells
    # -----------------------------------------------------------------------
    for name, src, dest in zip(plasmid_names, plasmid_wells, cell_wells):
        protocol.comment('Transformation %s: %g ul DNA -> %s'
                         % (name, DNA_VOLUME, dest))
        # A fresh tip per plasmid - the eight plasmids must not cross-contaminate.
        pick_up(p20)
        # Aspirate just off the bottom of the 10 ul DNA well so the tip stays
        # submerged but does not seal against the conical bottom.
        p20.aspirate(DNA_VOLUME, src.bottom(z=1))
        p20.dispense(DNA_VOLUME, dest.bottom(z=1))
        # CHOICE: the paper does not mention mixing. 1 ul dispensed into 10 ul
        # needs homogenising, so the DNA/cell mix is pipetted gently 3 x 5 ul -
        # well below the 20 ul pipette capacity and the 11 ul in the well.
        p20.mix(3, 5, dest.bottom(z=1))
        # Blow out inside the destination so the full 1 ul is delivered.
        p20.blow_out(dest.top(z=-2))
        p20.drop_tip()

    # -----------------------------------------------------------------------
    # Step 2 - 4 degC for 30 min, then 42 degC heat shock for 30 s
    # -----------------------------------------------------------------------
    tc.close_lid()

    protocol.comment('Incubating DNA with cells at %d C for %d minutes.'
                     % (INCUBATION_TEMP, INCUBATION_MINUTES))
    tc.set_block_temperature(
        INCUBATION_TEMP,
        hold_time_minutes=INCUBATION_MINUTES,
        block_max_volume=VOLUME_BEFORE_SOC)

    protocol.comment('Heat shock at %d C for %d seconds.'
                     % (HEAT_SHOCK_TEMP, HEAT_SHOCK_SECONDS))
    tc.set_block_temperature(
        HEAT_SHOCK_TEMP,
        hold_time_seconds=HEAT_SHOCK_SECONDS,
        block_max_volume=VOLUME_BEFORE_SOC)

    protocol.comment('Returning to %d C for %d minutes after the heat shock.'
                     % (INCUBATION_TEMP, POST_SHOCK_MINUTES))
    tc.set_block_temperature(
        INCUBATION_TEMP,
        hold_time_minutes=POST_SHOCK_MINUTES,
        block_max_volume=VOLUME_BEFORE_SOC)

    # -----------------------------------------------------------------------
    # Step 3 - add 50 ul SOC to each transformation
    # -----------------------------------------------------------------------
    tc.open_lid()
    protocol.comment('Adding %g ul SOC medium to each transformation.' % SOC_VOLUME)

    for name, dest in zip(plasmid_names, cell_wells):
        # A fresh tip per well again: the tip enters eight different cultures, so
        # reusing it would carry plasmid between transformations.
        pick_up(p300)
        p300.aspirate(SOC_VOLUME, soc.bottom(z=2))
        # Dispense above the 11 ul already in the well to avoid splashing it out.
        p300.dispense(SOC_VOLUME, dest.bottom(z=5))
        # Gentle resuspension in the 61 ul final volume.
        p300.mix(3, 40, dest.bottom(z=2))
        p300.blow_out(dest.top(z=-2))
        p300.drop_tip()
        protocol.comment('Transformation %s recovered in %g ul SOC.'
                         % (name, SOC_VOLUME))

    # -----------------------------------------------------------------------
    # Step 4 - recover at 37 degC for 1 hour
    # -----------------------------------------------------------------------
    tc.close_lid()
    tc.set_lid_temperature(RECOVERY_LID_TEMP)
    protocol.comment('Recovering at %d C for %d minutes.'
                     % (RECOVERY_TEMP, RECOVERY_MINUTES))
    tc.set_block_temperature(
        RECOVERY_TEMP,
        hold_time_minutes=RECOVERY_MINUTES,
        block_max_volume=VOLUME_AFTER_SOC)

    # -----------------------------------------------------------------------
    # Step 5 - park the outgrowths
    # -----------------------------------------------------------------------
    # CHOICE: the paper hands the recovered outgrowth straight to Protocol 2
    # (spotting), which is out of scope here. The block is dropped to 4 degC and
    # the lid opened so the 8 outgrowths are held cold and accessible for the
    # operator rather than sitting at 37 degC after the protocol ends.
    tc.deactivate_lid()
    tc.set_block_temperature(INCUBATION_TEMP)
    tc.open_lid()
    protocol.comment(
        'Done: %d transformations recovered and held at %d C. Proceed to APEX '
        'Protocol 2 (spotting on selective agar).'
        % (NUM_TRANSFORMATIONS, INCUBATION_TEMP))
