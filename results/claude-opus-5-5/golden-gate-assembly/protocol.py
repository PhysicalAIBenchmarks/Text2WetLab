"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow (Synth. Biol. 2022, doi:10.1093/synbio/ysac032) run on an
Opentrons OT-2:

  * build a Q5 PCR master mix and distribute it over 7 fragment reactions
  * add j5-designed primer pairs (0.1 uM final) and 0.5 ng linearized template
  * gradient PCR off-deck (Bio-Rad C1000)
  * DpnI digestion of residual methylated template, then column clean-up
  * Golden Gate assembly of 4 plasmids, each from 4 fragments, with volumes
    proportional to fragment length (BsaI-HFv2 + T4 DNA ligase)
  * clean-up and transformation into chemically competent E. coli TOP10

Fragment map (pcr_plate column 1):
  A1 = fragment 1 (tsPurple)        E1 = fragment 5 (backbone / KanR)
  B1 = fragment 2 (backbone)        F1 = fragment 6 (backbone)
  C1 = fragment 3 (YukonOFP)        G1 = fragment 7 (fuGFP)
  D1 = fragment 4 (aeBlue)

Assembly map (assembly_plate column 1): A1 = tsPurple, B1 = YukonOFP,
C1 = aeBlue, D1 = fuGFP; each with the shared backbone fragments 2, 5 and 6.
"""

metadata = {
    'protocolName': 'AssemblyTron: Golden Gate assembly of 4 chromoprotein plasmids',
    'author': 'AssemblyTron port',
    'description': (
        'Four four-fragment Golden Gate assemblies: PCR set-up, DpnI digest, '
        'assembly and transformation into E. coli TOP10.'
    ),
    'apiLevel': '2.13',
}


def run(protocol):
    # ------------------------------------------------------------------ labware
    tubes_50ml_1 = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2,
        label='tubes_1_5ml_1')
    primer_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes_15ml_1 = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # ------------------------------------------------------------------ reagents
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

    frag_wells = [pcr_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    fwd_primers = [primer_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    rev_primers = [primer_plate[w] for w in ('A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2')]
    # fragments 1-7 are amplified off tsPurple, tsPurple, YukonOFP, aeBlue,
    # tsPurple, tsPurple and fuGFP plasmid respectively
    templates = [template_plate[w] for w in ('A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1')]
    assemblies = [assembly_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]
    cells = [cells_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]

    def pip(volume):
        """Pick the pipette that can handle this volume (p20: 1-20, p300: 20-300)."""
        return p20 if volume < 20 else p300

    def one_to_many(volume, source, dests, mix_after=None, new_tip='once'):
        """Dispense the same reagent from one source into several wells."""
        pipette = pip(volume)
        pipette.transfer(volume, source, dests, new_tip=new_tip, mix_after=mix_after)

    def paired(volume, sources, dests):
        """Transfer source[i] -> dest[i] with a fresh tip per pair."""
        pipette = pip(volume)
        pipette.transfer(volume, sources, dests, new_tip='always')

    def mix_wells(volume, wells, reps):
        pipette = pip(volume)
        for well in wells:
            pipette.pick_up_tip()
            pipette.mix(reps, volume, well)
            pipette.drop_tip()

    # =====================================================================
    # 1-5. Q5 PCR master mix for 8 reactions (7 fragments + 1 excess)
    # =====================================================================
    protocol.comment('Building Q5 PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')
    p300.transfer(106, water, pcr_mm, new_tip='once')          # 1. water
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='once')       # 2. 5X Q5 buffer
    p20.transfer(4, dntp, pcr_mm, new_tip='once')              # 3. 10 mM dNTPs
    p20.transfer(2, q5_pol, pcr_mm, new_tip='once')            # 4. Q5 polymerase

    p300.pick_up_tip()                                          # 5. homogenise
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # =====================================================================
    # 6-10. 25 uL PCR reactions: 19 uL mix + 2.5 uL each primer + 1 uL template
    # =====================================================================
    protocol.comment('Distributing 19 uL PCR master mix to pcr_plate A1:G1.')
    one_to_many(19, pcr_mm, frag_wells)                         # 6.

    protocol.comment('Adding j5-designed primers to 0.1 uM final (2.5 uL of 1 uM).')
    paired(2.5, fwd_primers, frag_wells)                        # 7.
    paired(2.5, rev_primers, frag_wells)                        # 8.

    protocol.comment('Adding 1 uL (0.5 ng) linearized template plasmid per reaction.')
    paired(1, templates, frag_wells)                            # 9.

    p20.reset_tipracks()
    mix_wells(15, frag_wells, 3)                                # 10.
    p20.reset_tipracks()

    # =====================================================================
    # 11. Off-deck gradient PCR
    # =====================================================================
    protocol.comment(
        'MANUAL STEP: seal pcr_plate (or transfer the 100 uL PCR tubes) and move it '
        'to the Bio-Rad C1000 gradient thermocycler. Run 98 C 30 s; 34 cycles of '
        '98 C 10 s, 30 s annealing at the AssemblyTron/j5 optimal gradient '
        'temperature for each fragment, 72 C extension for the AssemblyTron-set time '
        '(~20-30 s/kb); final extension 72 C 5 min; hold 4 C. Take a sample of each '
        'reaction for gel electrophoresis, then return the plate to OT-2 slot 5.')
    protocol.pause('Run gradient PCR off-deck, then return pcr_plate to slot 5.')

    # =====================================================================
    # 12-16. DpnI digestion of residual methylated template (50 uL reactions)
    # =====================================================================
    protocol.comment('Setting up DpnI digests to remove residual plasmid template.')
    one_to_many(19, water, frag_wells)                          # 12.
    one_to_many(5, rcutsmart, frag_wells)                       # 13.
    one_to_many(1, dpni, frag_wells)                            # 14.

    p20.reset_tipracks()
    mix_wells(30, frag_wells, 3)                                # 15.

    protocol.comment(
        'MANUAL STEP: incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for '
        '20 min to heat-inactivate DpnI.')                      # 16.

    # =====================================================================
    # 17. Fragment clean-up and concentration
    # =====================================================================
    protocol.comment(
        'MANUAL STEP: clean and concentrate each of the 7 fragments on a Zymo DNA '
        'Clean & Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 uL per '
        '50 uL), 30 s spin, wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute in '
        '20 uL nuclease-free water after 1 min at room temperature (30 s spin). '
        'Return the eluted fragments 1-7 to their original wells pcr_plate A1:G1.')
    protocol.pause('Clean and concentrate fragments, return eluates to pcr_plate A1:G1.')

    # =====================================================================
    # 18-24. Golden Gate assemblies (20 uL), fragment volumes ~ fragment length
    # =====================================================================
    protocol.comment('Assembling four 20 uL Golden Gate reactions in assembly_plate A1:D1.')
    one_to_many(7, water, assemblies)                           # 18.
    one_to_many(2, t4_buffer, assemblies)                       # 19.

    protocol.comment('Adding the shared backbone fragments 2, 5 and 6.')
    one_to_many(3, pcr_plate['B1'], assemblies)                 # 20. fragment 2
    one_to_many(2, pcr_plate['E1'], assemblies)                 # 21. fragment 5 (KanR)
    one_to_many(3, pcr_plate['F1'], assemblies)                 # 22. fragment 6

    protocol.comment('Adding one chromoprotein fragment per assembly (1, 3, 4, 7).')
    paired(2, [pcr_plate[w] for w in ('A1', 'C1', 'D1', 'G1')], assemblies)   # 23.

    protocol.comment('Adding BsaI-HFv2 + T4 DNA ligase Golden Gate Enzyme Mix.')
    p20.transfer(1, gg_enzyme, assemblies, new_tip='once',
                 mix_after=(5, 10))                             # 24.

    # =====================================================================
    # 25-26. Golden Gate cycling and clean-up
    # =====================================================================
    protocol.comment(
        'MANUAL STEP: run the Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; 60 C 5 min; '
        'hold 4 C; lid ~85 C. If no module is available, pause and move the reactions '
        'to another thermocycler.')                             # 25.
    protocol.pause('Run the Golden Gate thermocycler program on assembly_plate A1:D1.')

    protocol.comment(
        'MANUAL STEP: clean and concentrate each assembly on a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in '
        '10 uL molecular grade water; return the eluates to assembly_plate A1:D1.')
    protocol.pause('Clean up assemblies, return 10 uL eluates to assembly_plate A1:D1.')

    # =====================================================================
    # 27-33. Transformation of E. coli TOP10
    # =====================================================================
    protocol.comment('Adding 5 uL of each purified assembly to 50 uL competent TOP10 cells.')
    paired(5, assemblies, cells)                                # 27.

    protocol.comment(
        'MANUAL STEP: measure the DNA concentration of the remaining 5 uL of each '
        'eluate on a NanoDrop-2000c for the CFU/ug calculation.')   # 28.

    protocol.comment(
        'MANUAL STEP: incubate cells_plate A1:D1 on ice for 30 min, heat shock at '
        '42 C for 60 s, then return to ice for ~2 min.')        # 29.
    protocol.pause('Ice 30 min, heat shock 42 C 60 s, back on ice ~2 min.')

    protocol.comment('Adding 250 uL LB + 0.2% dextrose to each transformation.')
    one_to_many(250, lb_dextrose, cells)                        # 30.

    protocol.comment(
        'MANUAL STEP: recover the cells at 37 C for 60 min with shaking (~250 rpm).')  # 31.
    protocol.comment(
        'MANUAL STEP: plate 50-200 uL of each recovery (neat or a 10x dilution, '
        'depending on predicted efficiency) onto separate LB agar plates containing '
        '50 ug/mL kanamycin; incubate at 37 C overnight.')      # 32.
    protocol.comment(
        'MANUAL STEP: count colonies per plate and score the fraction showing the '
        'expected chromoprotein colour (purple = tsPurple, orange = YukonOFP, '
        'blue = aeBlue, green = fuGFP); report CFU/ug of DNA plated.')  # 33.
