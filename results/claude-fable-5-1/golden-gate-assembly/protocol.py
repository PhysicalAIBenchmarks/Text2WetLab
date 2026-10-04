"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow on the Opentrons OT-2:
  * build a Q5 PCR master mix for 8 reactions
  * set up 7 fragment PCRs (j5-designed primers at 0.1 uM final, 0.5 ng linearized template)
  * gradient PCR off deck, then DpnI digestion of residual template
  * column clean-and-concentrate of the fragments
  * Golden Gate reactions (BsaI-HFv2 + T4 DNA ligase), volumes proportional to fragment length
  * clean up the assemblies and transform chemically competent E. coli TOP10
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Golden Gate assembly of four chromoprotein expression plasmids',
    'author': 'AssemblyTron',
    'description': (
        'Four four-fragment Golden Gate assemblies (tsPurple, YukonOFP, aeBlue, fuGFP) '
        'from seven PCR fragments, with DpnI digestion, cleanup and transformation.'
    ),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------ deck
    tubes_50ml_1 = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes_15ml_1 = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # --------------------------------------------------------------- reagents
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']
    lb_dextrose = tubes_15ml_1['A1']

    fragment_wells = [pcr_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    fwd_primers = [primer_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    rev_primers = [primer_plate[w] for w in ('A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2')]
    # fragments 1-7 are amplified off these linearized templates
    templates = [template_plate[w] for w in ('A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1')]
    assembly_wells = [assembly_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]
    cell_wells = [cells_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]

    # ---------------------------------------------------------------- helpers
    def pick_up(pipette):
        """Pick up a tip, recycling the rack when it runs out (tips are unlimited)."""
        try:
            pipette.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    def one_to_many(volume, source, destinations, new_tip_each=False, mix_after=None):
        """Dispense `volume` from one source into each destination."""
        pipette = pipette_for(volume)
        if not new_tip_each:
            pick_up(pipette)
        for destination in destinations:
            if new_tip_each:
                pick_up(pipette)
            pipette.aspirate(volume, source)
            pipette.dispense(volume, destination)
            if mix_after is not None:
                pipette.mix(mix_after[0], mix_after[1], destination)
            pipette.blow_out(destination.top())
            if new_tip_each:
                pipette.drop_tip()
        if not new_tip_each:
            pipette.drop_tip()

    def paired(volume, sources, destinations):
        """Dispense `volume` source[i] -> destination[i], fresh tip per pair."""
        pipette = pipette_for(volume)
        for source, destination in zip(sources, destinations):
            pick_up(pipette)
            pipette.aspirate(volume, source)
            pipette.dispense(volume, destination)
            pipette.blow_out(destination.top())
            pipette.drop_tip()

    def mix_wells(wells, repetitions, volume):
        pipette = pipette_for(volume)
        for well in wells:
            pick_up(pipette)
            pipette.mix(repetitions, volume, well)
            pipette.blow_out(well.top())
            pipette.drop_tip()

    # ================================================== 1-5  PCR master mix
    protocol.comment('Building Q5 PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')
    one_to_many(106, water, [pcr_mm])          # step 1
    one_to_many(40, q5_buffer, [pcr_mm])       # step 2
    one_to_many(4, dntp, [pcr_mm])             # step 3
    one_to_many(2, q5_pol, [pcr_mm])           # step 4
    mix_wells([pcr_mm], 5, 100)                # step 5

    # ============================================== 6-10  PCR reaction setup
    protocol.comment('Setting up 7 fragment PCRs in pcr_plate A1:G1 (25 uL each).')
    one_to_many(19, pcr_mm, fragment_wells)                  # step 6
    paired(2.5, fwd_primers, fragment_wells)                 # step 7
    paired(2.5, rev_primers, fragment_wells)                 # step 8
    paired(1, templates, fragment_wells)                     # step 9
    mix_wells(fragment_wells, 3, 15)                         # step 10

    # ------------------------------------------------------ 11  gradient PCR
    protocol.comment(
        'MANUAL STEP: seal pcr_plate (or cap the PCR tubes) and move it to the Bio-Rad C1000 '
        'gradient thermocycler. Run 98 C 30 s; 34 cycles of 98 C 10 s, 30 s annealing at the '
        'AssemblyTron/j5 optimal gradient temperature for each fragment, 72 C extension at the '
        'AssemblyTron-calculated time (about 20-30 s/kb); final extension 72 C 5 min; hold 4 C. '
        'Take a sample of each reaction for gel electrophoresis, then return the plate to the OT-2.')

    # ============================================== 12-15  DpnI digestion
    protocol.comment('DpnI digestion of residual methylated template (50 uL reactions).')
    one_to_many(19, water, fragment_wells)        # step 12
    one_to_many(5, rcutsmart, fragment_wells)     # step 13
    one_to_many(1, dpni, fragment_wells)          # step 14
    mix_wells(fragment_wells, 3, 30)              # step 15

    # ------------------------------------------- 16  digestion / inactivation
    protocol.comment(
        'MANUAL STEP: incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for 20 min to '
        'heat-inactivate the DpnI, on the thermocycler block.')

    # -------------------------------------------------- 17  fragment cleanup
    protocol.comment(
        'PAUSE: clean and concentrate each of the 7 fragments on a Zymo DNA Clean & '
        'Concentrator-5 column. Add 5:1 DNA Binding Buffer to sample (250 uL per 50 uL), spin '
        '30 s, wash twice with 200 uL DNA Wash Buffer (30 s spins), stand 1 min at room '
        'temperature and elute in 20 uL water (30 s spin). Return the eluates to their original '
        'positions pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')
    protocol.pause('Clean and concentrate fragments 1-7, return 20 uL eluates to pcr_plate A1:G1.')

    # ============================================ 18-24  Golden Gate reactions
    protocol.comment(
        'Assembling four Golden Gate reactions (20 uL each) in assembly_plate A1:D1; fragment '
        'volumes are proportional to fragment length.')
    one_to_many(7, water, assembly_wells)                      # step 18
    one_to_many(2, t4_buffer, assembly_wells)                  # step 19
    one_to_many(3, pcr_plate['B1'], assembly_wells)            # step 20: fragment 2 backbone
    one_to_many(2, pcr_plate['E1'], assembly_wells)            # step 21: fragment 5 backbone/KanR
    one_to_many(3, pcr_plate['F1'], assembly_wells)            # step 22: fragment 6 backbone
    # step 23: chromoprotein fragments 1, 3, 4, 7 -> assemblies A1, B1, C1, D1
    paired(2, [pcr_plate[w] for w in ('A1', 'C1', 'D1', 'G1')], assembly_wells)
    # step 24: Golden Gate enzyme mix, mixing after each dispense
    one_to_many(1, gg_enzyme, assembly_wells, new_tip_each=True, mix_after=(5, 15))

    # ------------------------------------------------- 25  Golden Gate cycling
    protocol.comment(
        'MANUAL STEP: run the Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; 60 C 5 min; hold at 4 C, '
        'lid about 85 C. If no module is available, pause and move the reactions to another '
        'thermocycler.')

    # ------------------------------------------------- 26  assembly cleanup
    protocol.comment(
        'PAUSE: clean and concentrate each assembly on a Zymo DNA Clean & Concentrator-5 column '
        '(5:1 binding buffer, two 200 uL washes) and elute in 10 uL molecular grade water. '
        'Return the eluates to assembly_plate A1:D1.')
    protocol.pause('Clean up the four assemblies, return 10 uL eluates to assembly_plate A1:D1.')

    # ================================================= 27-30  transformation
    protocol.comment('Adding 5 uL of each purified assembly to 50 uL TOP10 competent cells.')
    paired(5, assembly_wells, cell_wells)                      # step 27

    protocol.comment(
        'MANUAL STEP: measure the DNA concentration of the remaining 5 uL of each eluate on a '
        'NanoDrop-2000c for the CFU/ug calculation.')
    protocol.comment(
        'MANUAL STEP: incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42 C for 60 s, '
        'then return to ice for about 2 min.')

    one_to_many(250, lb_dextrose, cell_wells, new_tip_each=True)   # step 30

    # ------------------------------------------------ 31-33  recovery, plating
    protocol.comment(
        'MANUAL STEP: recover the cells at 37 C for 60 min with shaking at about 250 rpm.')
    protocol.comment(
        'MANUAL STEP: plate 50-200 uL of each recovery (neat or a 10x dilution, depending on the '
        'predicted efficiency) onto separate LB agar plates containing 50 ug/mL kanamycin; '
        'incubate at 37 C overnight.')
    protocol.comment(
        'MANUAL STEP: count the colonies on each plate, score the fraction showing the expected '
        'chromoprotein colour (purple, orange, blue, green) and report CFU/ug of DNA plated.')
