"""
Golden Gate assembly of four four-fragment chromoprotein expression plasmids
on the Opentrons OT-2, after AssemblyTron.

Reference
---------
AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab
robots. Synthetic Biology (2022), doi:10.1093/synbio/ysac032 (CC BY 4.0).

Overview
--------
Seven fragments are amplified by PCR from four linearized chromoprotein
template plasmids (tsPurple, YukonOFP, aeBlue, fuGFP).  Fragments 2, 5 and 6
are the shared plasmid-backbone / kanamycin-resistance parts; fragments 1, 3,
4 and 7 are the four different chromoprotein coding parts.  After a gradient
PCR, residual methylated template is removed with DpnI, the fragments are
cleaned and concentrated (residual polymerase fills in Golden Gate sticky
ends, so this clean-up is required), and the parts are combined in volumes
proportional to fragment length, which gives a roughly equimolar mix assuming
comparable PCR yields.  The Golden Gate reactions (BsaI-HFv2 + T4 DNA ligase)
are cycled, cleaned up and transformed into chemically competent E. coli
TOP10 cells.

Non-pipetting steps (thermocycling, incubations, heat shock, column
clean-ups, plating, colony counting) cannot be simulated; they are recorded in
the run log with protocol.comment().
"""

from opentrons import protocol_api

metadata = {
    'protocolName': (
        'AssemblyTron Golden Gate: four four-fragment chromoprotein '
        'expression plasmids'
    ),
    'author': 'Automated port of AssemblyTron (doi:10.1093/synbio/ysac032)',
    'description': (
        'PCR set-up of 7 fragments, DpnI digestion, Golden Gate assembly of '
        '4 four-fragment chromoprotein plasmids and transformation into '
        'E. coli TOP10.'
    ),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------
    # Labware
    # ------------------------------------------------------------------
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

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # ------------------------------------------------------------------
    # Pipettes
    # ------------------------------------------------------------------
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # ------------------------------------------------------------------
    # Reagent positions
    # ------------------------------------------------------------------
    water = tubes_50ml_1.wells_by_name()['A1']        # nuclease-free water
    q5_buffer = tubes_1_5ml_1.wells_by_name()['A1']   # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1.wells_by_name()['B1']        # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1.wells_by_name()['C1']      # Q5 HiFi polymerase
    pcr_mm = tubes_1_5ml_1.wells_by_name()['D1']      # PCR master mix (built)
    rcutsmart = tubes_1_5ml_1.wells_by_name()['A2']   # rCutSmart buffer
    dpni = tubes_1_5ml_1.wells_by_name()['B2']        # DpnI
    t4_buffer = tubes_1_5ml_1.wells_by_name()['C2']   # 10X T4 ligase buffer
    gg_enzyme = tubes_1_5ml_1.wells_by_name()['D2']   # BsaI-HFv2 + T4 ligase
    lb_dextrose = tubes_15ml_1.wells_by_name()['A1']  # LB + 0.2% dextrose

    # Fragments 1-7 occupy column 1 of the PCR plate, in order.
    frag_wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pcr_wells = [pcr_plate.wells_by_name()[w] for w in frag_wells]
    fwd_primers = [primer_plate.wells_by_name()[w] for w in frag_wells]
    rev_primers = [primer_plate.wells_by_name()[w]
                   for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]

    # Template plasmid used to amplify each of fragments 1-7.
    #   A1 pIDMv5K-J23100-tsPurple-B1006    B1 ...-YukonOFP-...
    #   C1 ...-aeBlue-...                   D1 ...-fuGFP-...
    template_for_fragment = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    templates = [template_plate.wells_by_name()[w]
                 for w in template_for_fragment]

    # One Golden Gate reaction per chromoprotein.
    assembly_names = ['tsPurple', 'YukonOFP', 'aeBlue', 'fuGFP']
    assembly_wells = [assembly_plate.wells_by_name()[w]
                      for w in ['A1', 'B1', 'C1', 'D1']]
    cells_wells = [cells_plate.wells_by_name()[w]
                   for w in ['A1', 'B1', 'C1', 'D1']]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def pip_for(volume):
        """Pick the pipette whose working range covers this volume."""
        return p20 if volume <= 20 else p300

    def send(volume, sources, dests, new_tip='always', mix_after=None):
        """Transfer `volume` from source(s) to destination(s).

        A single source feeds every destination; otherwise sources and
        destinations are paired in order.
        """
        if not isinstance(sources, list):
            sources = [sources] * len(dests)
        pipette = pip_for(volume)
        if pipette.has_tip:
            pipette.drop_tip()
        if new_tip == 'once':
            pipette.pick_up_tip()
        for src, dest in zip(sources, dests):
            if new_tip == 'always':
                pipette.pick_up_tip()
            pipette.aspirate(volume, src)
            pipette.dispense(volume, dest)
            if mix_after is not None:
                pipette.mix(mix_after[0], mix_after[1], dest)
            pipette.blow_out(dest.top())
            if new_tip == 'always':
                pipette.drop_tip()
        if pipette.has_tip:
            pipette.drop_tip()

    def stir(wells, repetitions, volume):
        """Mix wells in place with a fresh tip for each well."""
        pipette = pip_for(volume)
        if pipette.has_tip:
            pipette.drop_tip()
        for well in wells:
            pipette.pick_up_tip()
            pipette.mix(repetitions, volume, well)
            pipette.blow_out(well.top())
            pipette.drop_tip()

    def fresh_tips():
        """Tips are unlimited: hand the operator a new rack."""
        p20.reset_tipracks()
        p300.reset_tipracks()

    # ==================================================================
    # Part 1 - PCR set-up for fragments 1-7
    # ==================================================================
    protocol.comment(
        'PART 1: building the PCR master mix for 8 reactions (7 fragments '
        'plus one reaction of overage) in tubes_1_5ml_1 D1.')

    # Step 1
    protocol.comment('Step 1: 106 uL nuclease-free water -> PCR master mix.')
    send(106, water, [pcr_mm], new_tip='once')

    # Step 2
    protocol.comment('Step 2: 40 uL 5X Q5 reaction buffer -> PCR master mix.')
    send(40, q5_buffer, [pcr_mm], new_tip='once')

    # Step 3
    protocol.comment('Step 3: 4 uL 10 mM dNTPs -> PCR master mix.')
    send(4, dntp, [pcr_mm], new_tip='once')

    # Step 4
    protocol.comment(
        'Step 4: 2 uL Q5 High-Fidelity DNA Polymerase -> PCR master mix.')
    send(2, q5_pol, [pcr_mm], new_tip='once')

    # Step 5
    protocol.comment('Step 5: mix the PCR master mix, 5 cycles at 100 uL.')
    stir([pcr_mm], 5, 100)

    # Step 6
    protocol.comment(
        'Step 6: 19 uL PCR master mix -> pcr_plate A1:G1 (fragments 1-7).')
    send(19, pcr_mm, pcr_wells, new_tip='once')

    # Step 7
    protocol.comment(
        'Step 7: 2.5 uL forward primer (1 uM) -> each fragment reaction, '
        'for a final primer concentration of 0.1 uM in 25 uL.')
    send(2.5, fwd_primers, pcr_wells)

    # Step 8
    protocol.comment(
        'Step 8: 2.5 uL reverse primer (1 uM) -> each fragment reaction.')
    send(2.5, rev_primers, pcr_wells)

    # Step 9
    protocol.comment(
        'Step 9: 1 uL linearized template plasmid (0.5 ng/uL, so 0.5 ng per '
        'reaction) -> each fragment reaction. Fragments 1, 2, 5 and 6 come '
        'from the tsPurple plasmid; fragment 3 from YukonOFP; fragment 4 '
        'from aeBlue; fragment 7 from fuGFP.')
    send(1, templates, pcr_wells)

    # Step 10
    protocol.comment(
        'Step 10: mix each 25 uL PCR, 3 cycles at 15 uL.')
    stir(pcr_wells, 3, 15)

    fresh_tips()

    # Step 11 - off-deck
    protocol.comment(
        'Step 11 (manual, not simulated): seal pcr_plate (or cap and move '
        'the 100 uL PCR tubes) and carry the reactions to the Bio-Rad C100 '
        'gradient thermocycler. Place each tube in the block position given '
        'by the AssemblyTron/j5 optimal annealing gradient. Run: 98 C for '
        '30 s; 34 cycles of 98 C 10 s, 30 s annealing at the optimal '
        'gradient temperature for that fragment, 72 C extension for the '
        'time set by AssemblyTron (about 20-30 s/kb); final extension 72 C '
        'for 5 min; hold at 4 C. Remove a sample of each reaction for '
        'agarose gel electrophoresis to confirm fragment length, then '
        'return the reactions to pcr_plate A1:G1 on the OT-2.')
    protocol.pause(
        'Run the gradient PCR, check the fragments on a gel, then return '
        'pcr_plate to slot 5 and resume.')

    # ==================================================================
    # Part 2 - DpnI digestion of residual template
    # ==================================================================
    protocol.comment(
        'PART 2: DpnI digestion to destroy the methylated plasmid template '
        'carried through the PCR.')

    # Step 12
    protocol.comment('Step 12: 19 uL nuclease-free water -> pcr_plate A1:G1.')
    send(19, water, pcr_wells)

    # Step 13
    protocol.comment('Step 13: 5 uL rCutSmart Buffer -> pcr_plate A1:G1.')
    send(5, rcutsmart, pcr_wells)

    # Step 14
    protocol.comment('Step 14: 1 uL DpnI -> pcr_plate A1:G1.')
    send(1, dpni, pcr_wells)

    # Step 15
    protocol.comment(
        'Step 15: mix each 50 uL digestion, 3 cycles at 30 uL.')
    stir(pcr_wells, 3, 30)

    fresh_tips()

    # Step 16 - off-deck
    protocol.comment(
        'Step 16 (manual, not simulated): incubate pcr_plate A1:G1 at 37 C '
        'for 30 min on the thermocycler block, then 65 C for 20 min to '
        'inactivate the DpnI.')

    # Step 17 - off-deck clean-up
    protocol.comment(
        'Step 17 (manual, not simulated): clean and concentrate each of the '
        '7 fragments on a Zymo DNA Clean & Concentrator-5 column. Residual '
        'polymerase fills in the BsaI overhangs and blocks ligation, so this '
        'step is required before Golden Gate. Add DNA Binding Buffer at 5:1 '
        'to sample (250 uL per 50 uL digestion), spin 30 s, wash twice with '
        '200 uL DNA Wash Buffer (30 s spins), add 20 uL water, stand 1 min '
        'at room temperature and elute with a 30 s spin. Return each eluate '
        'to its original position in pcr_plate A1:G1 (fragments 1-7).')
    protocol.pause(
        'Clean and concentrate fragments 1-7, elute in 20 uL water, return '
        'them to pcr_plate A1:G1 and resume.')

    # ==================================================================
    # Part 3 - Golden Gate assembly
    # ==================================================================
    protocol.comment(
        'PART 3: four 20 uL Golden Gate reactions. Each reaction receives '
        'the three shared backbone fragments (2, 5 and 6) plus one '
        'chromoprotein fragment. Fragment volumes are proportional to '
        'fragment length, which gives a roughly equimolar mix given '
        'comparable PCR yields.')

    # Step 18
    protocol.comment(
        'Step 18: 7 uL nuclease-free water -> assembly_plate A1:D1.')
    send(7, water, assembly_wells, new_tip='once')

    # Step 19
    protocol.comment(
        'Step 19: 2 uL 10X T4 DNA Ligase Buffer -> assembly_plate A1:D1.')
    send(2, t4_buffer, assembly_wells)

    # Step 20
    protocol.comment(
        'Step 20: 3 uL fragment 2 (backbone, pcr_plate B1) -> every '
        'assembly.')
    send(3, pcr_plate.wells_by_name()['B1'], assembly_wells)

    # Step 21
    protocol.comment(
        'Step 21: 2 uL fragment 5 (backbone/KanR, pcr_plate E1) -> every '
        'assembly.')
    send(2, pcr_plate.wells_by_name()['E1'], assembly_wells)

    # Step 22
    protocol.comment(
        'Step 22: 3 uL fragment 6 (backbone, pcr_plate F1) -> every '
        'assembly.')
    send(3, pcr_plate.wells_by_name()['F1'], assembly_wells)

    # Step 23
    protocol.comment(
        'Step 23: 2 uL of one chromoprotein fragment into each assembly - '
        'fragment 1 (A1) to ' + assembly_names[0] + ', fragment 3 (C1) to '
        + assembly_names[1] + ', fragment 4 (D1) to ' + assembly_names[2]
        + ', fragment 7 (G1) to ' + assembly_names[3] + '.')
    send(2,
         [pcr_plate.wells_by_name()[w] for w in ['A1', 'C1', 'D1', 'G1']],
         assembly_wells)

    # Step 24
    protocol.comment(
        'Step 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase) '
        '-> each assembly, then mix 5 times.')
    send(1, gg_enzyme, assembly_wells, mix_after=(5, 10))

    fresh_tips()

    # Step 25 - thermocycler
    protocol.comment(
        'Step 25 (not simulated): run the Golden Gate program on '
        'assembly_plate A1:D1 in the Opentrons thermocycler module - 30 '
        'cycles of 37 C for 5 min then 16 C for 5 min, followed by 60 C for '
        '5 min and a 4 C hold, with the lid at about 85 C. If no '
        'thermocycler module is installed, the protocol pauses so the '
        'reactions can be moved to a separate thermocycler and returned.')
    protocol.pause(
        'Run the Golden Gate cycling program, then return assembly_plate to '
        'slot 6 and resume.')

    # Step 26 - off-deck clean-up
    protocol.comment(
        'Step 26 (manual, not simulated): clean and concentrate each '
        'assembly on a Zymo DNA Clean & Concentrator-5 column (DNA Binding '
        'Buffer at 5:1, two 200 uL DNA Wash Buffer washes) and elute in '
        '10 uL molecular grade water. Return the four eluates to '
        'assembly_plate A1:D1.')
    protocol.pause(
        'Clean and concentrate the four assemblies, elute in 10 uL water, '
        'return them to assembly_plate A1:D1 and resume.')

    # ==================================================================
    # Part 4 - Transformation into E. coli TOP10
    # ==================================================================
    protocol.comment(
        'PART 4: transforming the assemblies into chemically competent '
        'E. coli TOP10 cells (Hanahan method).')

    # Step 27
    protocol.comment(
        'Step 27: 5 uL purified Golden Gate assembly -> 50 uL competent '
        'cells in cells_plate A1:D1, one assembly per well.')
    send(5, assembly_wells, cells_wells)

    # Step 28
    protocol.comment(
        'Step 28 (manual, not simulated): measure the DNA concentration of '
        'the remaining 5 uL of each eluate on a NanoDrop-2000c microvolume '
        'spectrophotometer. These readings give the mass of DNA transformed '
        'for the CFU/ug transformation-efficiency calculation.')

    # Step 29
    protocol.comment(
        'Step 29 (manual, not simulated): incubate cells_plate A1:D1 on ice '
        'for 30 min, heat shock at 42 C for 60 s, then return to ice for '
        'about 2 min.')
    protocol.pause(
        'Incubate on ice 30 min, heat shock 42 C for 60 s, return to ice '
        'for 2 min, then put cells_plate back in slot 7 and resume.')

    # Step 30
    protocol.comment(
        'Step 30: 250 uL LB + 0.2% (w/v) dextrose -> cells_plate A1:D1. '
        'Dextrose imposes catabolite repression during recovery.')
    send(250, lb_dextrose, cells_wells)

    # Step 31
    protocol.comment(
        'Step 31 (manual, not simulated): recover the transformations at '
        '37 C for 60 min with shaking at about 250 rpm.')

    # Step 32
    protocol.comment(
        'Step 32 (manual, not simulated): plate 50-200 uL of each recovery, '
        'neat or as a 10x dilution depending on the predicted assembly '
        'efficiency, onto separate LB agar plates containing kanamycin at '
        '50 ug/mL. Incubate at 37 C overnight.')

    # Step 33
    protocol.comment(
        'Step 33 (manual, not simulated): count the colonies on each plate '
        'and score the fraction showing the expected chromoprotein colour - '
        'purple for tsPurple, orange for YukonOFP, blue for aeBlue and '
        'green for fuGFP. Report transformation efficiency as CFU per ug of '
        'DNA plated.')

    protocol.comment(
        'Protocol complete: four four-fragment Golden Gate chromoprotein '
        'expression plasmids assembled and transformed.')
