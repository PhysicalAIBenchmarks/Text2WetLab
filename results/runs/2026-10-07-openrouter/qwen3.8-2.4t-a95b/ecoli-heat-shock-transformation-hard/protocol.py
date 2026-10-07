"""APEX Protocol 1 - Automated heat shock transformation on the OT-2 thermocycler.

Implements the heat shock transformation of Kasprzyk, Herrera & Stracquadanio,
"APEX: Automated Protein EXpression in Escherichia coli" (bioRxiv 2024,
doi:10.1101/2024.08.13.607171), Protocol 1, for 8 plasmids (pEX01-pEX08).

Parameters taken from the paper:
  * Volumes: the Low Volume (LV) configuration, which the paper selected for
    all subsequent automated experiments - 1 uL plasmid DNA, 10 uL competent
    cells, 50 uL SOC medium (Results > Optimisation of transformation volume;
    Fig. 4 caption).
  * Temperatures/times (Protocol 1 defaults): incubate DNA + cells at 4 degC
    for 30 min, heat shock at 42 degC for 30 s, recover with SOC at 37 degC
    for 1 h, all on the thermocycler module for rapid temperature changes.

Choices where the paper leaves details open are flagged with comments below.
Steps after recovery (spotting on agar, Protocol 2) are out of scope.
"""

metadata = {
    'protocolName': 'APEX Protocol 1 - Heat shock transformation (LV, 8 plasmids)',
    'author': 'generated from doi:10.1101/2024.08.13.607171',
    'description': 'Automated heat shock transformation of 8 plasmids '
                   '(pEX01-pEX08) into DH5alpha on the OT-2 thermocycler '
                   'using the APEX Low Volume configuration.',
}

requirements = {'robotType': 'OT-2', 'apiLevel': '2.15'}


def run(protocol):
    # ------------------------------------------------------------------
    # Labware and instruments (fixed deck layout)
    # ------------------------------------------------------------------
    plasmid_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware(
        'nest_12_reservoir_15ml', 2, label='soc_reservoir')

    tc = protocol.load_module('thermocycler')
    transformation_plate = tc.load_labware(
        'biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # ------------------------------------------------------------------
    # Volumes - APEX Low Volume (LV) configuration selected in the paper
    # ------------------------------------------------------------------
    DNA_VOL = 1.0   # uL plasmid (LV); cells are 10 uL, pre-loaded by operator
    SOC_VOL = 50.0  # uL SOC medium (LV)

    # Transformation n uses plasmid well n and cell well n (A1..H1, col 1)
    well_names = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']
    dna_wells = [plasmid_plate[w] for w in well_names]
    cell_wells = [transformation_plate[w] for w in well_names]
    soc = soc_reservoir['A1']

    # ------------------------------------------------------------------
    # Step 1: add plasmid DNA to the pre-chilled competent cells on the
    # thermocycler block (kept at 4 degC, as in the paper's ice-cold
    # CaCl2 pre-incubation). One fresh tip per plasmid to avoid
    # cross-contamination.
    # ------------------------------------------------------------------
    tc.open_lid()
    # Ensure the block is at the 4 degC incubation temperature (the cells
    # were loaded by the operator onto the pre-chilled block).
    tc.set_block_temperature(4)

    for src, dst in zip(dna_wells, cell_wells):
        p20.pick_up_tip()
        p20.aspirate(DNA_VOL, src)
        p20.dispense(DNA_VOL, dst)
        # The paper does not specify mixing after DNA addition; mix 3x 5 uL
        # (well holds 11 uL total) to homogenise the 1 uL DNA in the cells,
        # then blow out any remaining droplets.
        p20.mix(3, 5, dst)
        p20.blow_out(dst.top())
        p20.drop_tip()

    # Reset the 20 uL rack so a full rack is available if this protocol is
    # re-run/appended; tips are unlimited per the task setup.
    p20.reset_tipracks()

    # ------------------------------------------------------------------
    # Step 2: 4 degC for 30 min incubation, lid closed to limit evaporation.
    # (The paper does not mention heating the lid, so no lid temperature is
    # set; the closed lid is the sound choice for these small volumes.)
    # ------------------------------------------------------------------
    tc.close_lid()
    tc.set_block_temperature(4, hold_time_minutes=30)

    # ------------------------------------------------------------------
    # Step 3: heat shock - 42 degC for 30 s. Default (maximum) ramp rate is
    # used, since the paper stresses the need for rapid temperature shifts.
    # ------------------------------------------------------------------
    tc.set_block_temperature(42, hold_time_seconds=30)

    # Cool the block back to 4 degC before opening the lid (standard heat
    # shock practice: return cells to ice-cold immediately after the shock;
    # the paper does not state this explicitly, so it is a sound choice).
    tc.set_block_temperature(4)

    # ------------------------------------------------------------------
    # Step 4: add 50 uL SOC (LV volume) to each transformation and mix.
    # One tip per well; fresh tips for the cell/SOC mixture.
    # ------------------------------------------------------------------
    tc.open_lid()
    for dst in cell_wells:
        p300.pick_up_tip()
        p300.aspirate(SOC_VOL, soc)
        p300.dispense(SOC_VOL, dst)
        # Mix below the total well volume (10 + 1 + 50 = 61 uL) to avoid
        # spilling; the paper does not specify a mixing volume.
        p300.mix(3, 40, dst)
        p300.blow_out(dst.top())
        p300.drop_tip()
    p300.reset_tipracks()

    # ------------------------------------------------------------------
    # Step 5: recovery - 37 degC for 1 h with SOC, lid closed.
    # ------------------------------------------------------------------
    tc.close_lid()
    tc.set_block_temperature(37, hold_time_minutes=60)

    # ------------------------------------------------------------------
    # End of Protocol 1: open the lid and deactivate the block. The
    # recovered outgrowths are handled by Protocol 2 (spotting), which is
    # out of scope here.
    # ------------------------------------------------------------------
    tc.open_lid()
    tc.deactivate_block()
