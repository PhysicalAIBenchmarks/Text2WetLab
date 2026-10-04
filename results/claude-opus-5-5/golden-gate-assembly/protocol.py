"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow on the Opentrons OT-2 (Synth. Biol. 2022,
doi:10.1093/synbio/ysac032):

  1. build a Q5 PCR master mix and set up 7 fragment PCRs (j5-designed primers
     at 0.1 uM final, 0.5 ng linearized template, 25 uL reactions)
  2. gradient PCR off-deck (optimal annealing temperature per fragment)
  3. DpnI digestion of residual methylated template
  4. column clean-up / concentration of the 7 fragments
  5. Golden Gate assembly of 4 plasmids, fragment volumes proportional to
     fragment length, with BsaI-HFv2 + T4 DNA ligase
  6. clean-up of the assemblies and transformation into E. coli TOP10
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 chromoprotein plasmids, 4 fragments each',
    'author': 'AssemblyTron-style automation',
    'description': 'PCR setup, DpnI digest, Golden Gate assembly and transformation '
                   'of four four-fragment chromoprotein expression plasmids.',
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------ deck
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

    # --------------------------------------------------------------- reagents
    water = tubes_50ml_1['A1']            # nuclease-free water
    q5_buffer = tubes_1_5ml_1['A1']       # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1['B1']            # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1['C1']          # Q5 High-Fidelity DNA Polymerase
    pcr_mm = tubes_1_5ml_1['D1']          # PCR master mix (made below)
    rcutsmart = tubes_1_5ml_1['A2']       # rCutSmart Buffer
    dpni = tubes_1_5ml_1['B2']            # DpnI
    t4_buffer = tubes_1_5ml_1['C2']       # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']       # BsaI-HFv2 + T4 DNA ligase
    lb_dextrose = tubes_15ml_1['A1']      # LB + 0.2% (w/v) dextrose

    # 7 PCR fragments live in column 1 of pcr_plate
    frag_wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    fragments = [pcr_plate[w] for w in frag_wells]

    fwd_primers = [primer_plate[w] for w in frag_wells]
    rev_primers = [primer_plate[w] for w in
                   ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    # template per fragment: tsPurple(A1), YukonOFP(B1), aeBlue(C1), fuGFP(D1);
    # the three shared backbone fragments are amplified off the tsPurple plasmid
    templates = [template_plate[w] for w in
                 ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]

    assemblies = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]

    def pick(pip):
        """Pick up a tip, recycling the rack if it has been used up."""
        if pip.tip_racks[0].next_tip(pip.channels) is None:
            pip.reset_tipracks()
        pip.pick_up_tip()

    def one_to_many(pip, vol, source, dests, new_tip_each=False,
                    mix_after=None):
        """Dispense `vol` from one source into each destination well."""
        if not new_tip_each:
            pick(pip)
        for dest in dests:
            if new_tip_each:
                pick(pip)
            pip.aspirate(vol, source.bottom(z=2))
            pip.dispense(vol, dest.bottom(z=2))
            if mix_after:
                pip.mix(mix_after[0], mix_after[1], dest.bottom(z=2))
            pip.blow_out(dest.top(z=-2))
            if new_tip_each:
                pip.drop_tip()
        if not new_tip_each:
            pip.drop_tip()

    def paired(pip, vol, sources, dests, mix_after=None):
        """Transfer `vol` source[i] -> dest[i] with a fresh tip each time."""
        for source, dest in zip(sources, dests):
            pick(pip)
            pip.aspirate(vol, source.bottom(z=2))
            pip.dispense(vol, dest.bottom(z=2))
            if mix_after:
                pip.mix(mix_after[0], mix_after[1], dest.bottom(z=2))
            pip.blow_out(dest.top(z=-2))
            pip.drop_tip()

    def mix_wells(pip, reps, vol, wells):
        for well in wells:
            pick(pip)
            pip.mix(reps, vol, well.bottom(z=2))
            pip.blow_out(well.top(z=-2))
            pip.drop_tip()

    # ================================================================ PCR mix
    # 8-reaction master mix: 106 uL water + 40 uL 5X Q5 + 4 uL dNTPs + 2 uL pol
    protocol.comment('Building PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')

    # 1. water
    pick(p300)
    p300.aspirate(106, water.bottom(z=5))
    p300.dispense(106, pcr_mm.bottom(z=5))
    p300.blow_out(pcr_mm.top(z=-2))
    p300.drop_tip()

    # 2. 5X Q5 reaction buffer
    pick(p300)
    p300.aspirate(40, q5_buffer.bottom(z=2))
    p300.dispense(40, pcr_mm.bottom(z=5))
    p300.blow_out(pcr_mm.top(z=-2))
    p300.drop_tip()

    # 3. 10 mM dNTPs
    one_to_many(p20, 4, dntp, [pcr_mm])

    # 4. Q5 High-Fidelity DNA Polymerase
    one_to_many(p20, 2, q5_pol, [pcr_mm])

    # 5. homogenise the master mix
    pick(p300)
    p300.mix(5, 100, pcr_mm.bottom(z=4))
    p300.blow_out(pcr_mm.top(z=-2))
    p300.drop_tip()

    # ========================================================== PCR setup (7)
    protocol.comment('Setting up 7 fragment PCRs (25 uL each) in pcr_plate A1:G1.')

    # 6. 19 uL master mix per reaction
    for dest in fragments:
        one_to_many(p20, 19, pcr_mm, [dest])

    # 7. forward primers, 2.5 uL of 1 uM stock -> 0.1 uM final
    paired(p20, 2.5, fwd_primers, fragments)

    # 8. reverse primers, 2.5 uL of 1 uM stock -> 0.1 uM final
    paired(p20, 2.5, rev_primers, fragments)

    # 9. 1 uL linearized template at 0.5 ng/uL -> 0.5 ng per reaction
    paired(p20, 1, templates, fragments)

    # 10. mix each reaction
    mix_wells(p20, 3, 15, fragments)

    # 11. off-deck gradient PCR
    protocol.comment(
        'MANUAL STEP (not simulated): seal pcr_plate (or move the PCR tubes) and '
        'transfer manually to the Bio-Rad C100 gradient thermocycler. Run: 98 C '
        '30 s; 34 cycles of 98 C 10 s, annealing 30 s at the AssemblyTron/j5 '
        'optimal-gradient temperature for each fragment, 72 C extension at the '
        'time set by AssemblyTron (about 20-30 s/kb); final extension 72 C 5 min; '
        'hold 4 C. Take a sample of each reaction for gel electrophoresis, then '
        'return the plate to the OT-2.')

    # ========================================================= DpnI digestion
    protocol.comment('DpnI digestion of residual methylated template (50 uL total).')

    # 12. water
    one_to_many(p20, 19, water, fragments, new_tip_each=True)

    # 13. rCutSmart Buffer
    one_to_many(p20, 5, rcutsmart, fragments, new_tip_each=True)

    # 14. DpnI
    one_to_many(p20, 1, dpni, fragments, new_tip_each=True)

    # 15. mix each digest
    mix_wells(p300, 3, 30, fragments)

    # 16. incubation
    protocol.comment(
        'MANUAL STEP (not simulated): incubate pcr_plate A1:G1 at 37 C for 30 min, '
        'then 65 C for 20 min to inactivate DpnI, on the thermocycler block.')

    # 17. column clean-up and concentration of the fragments
    protocol.comment(
        'PAUSE / MANUAL STEP (not simulated): clean and concentrate each of the 7 '
        'fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding '
        'Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA Wash '
        'Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature '
        '(30 s spin). Return the eluted fragments to their original positions '
        'pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')
    protocol.pause('Clean and concentrate fragments; return eluates to pcr_plate '
                   'A1:G1, then resume.')

    # ================================================= Golden Gate assemblies
    # 20 uL reactions; fragment volumes are proportional to fragment length
    protocol.comment('Assembling 4 Golden Gate reactions (20 uL) in assembly_plate '
                     'A1:D1; fragment volumes proportional to fragment length.')

    # 18. water
    one_to_many(p20, 7, water, assemblies, new_tip_each=True)

    # 19. 10X T4 DNA Ligase Buffer
    one_to_many(p20, 2, t4_buffer, assemblies, new_tip_each=True)

    # 20. fragment 2 (backbone)
    one_to_many(p20, 3, pcr_plate['B1'], assemblies, new_tip_each=True)

    # 21. fragment 5 (backbone / KanR)
    one_to_many(p20, 2, pcr_plate['E1'], assemblies, new_tip_each=True)

    # 22. fragment 6 (backbone)
    one_to_many(p20, 3, pcr_plate['F1'], assemblies, new_tip_each=True)

    # 23. chromoprotein fragments 1, 3, 4, 7 -> one per assembly
    #     tsPurple, aeBlue, fuGFP, YukonOFP inserts
    paired(p20, 2, [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']], assemblies)

    # 24. Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase), then mix
    one_to_many(p20, 1, gg_enzyme, assemblies, new_tip_each=True,
                mix_after=(5, 10))

    # 25. thermocycler assembly program
    protocol.comment(
        'MANUAL STEP (not simulated): run the Golden Gate program on assembly_plate '
        'in the Opentrons thermocycler module: 30 cycles of 37 C 5 min then 16 C '
        '5 min; then 60 C 5 min; hold at 4 C. Lid about 85 C. If no module is '
        'available, pause and move the reactions to another thermocycler.')

    # 26. clean-up of the assemblies
    protocol.comment(
        'MANUAL STEP (not simulated): clean and concentrate each assembly with a '
        'Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 uL '
        'wash) and elute in 10 uL molecular grade water; return the eluates to '
        'assembly_plate A1:D1.')
    protocol.pause('Clean and concentrate assemblies; return 10 uL eluates to '
                   'assembly_plate A1:D1, then resume.')

    # ========================================================= transformation
    # 27. 5 uL purified assembly into 50 uL competent TOP10 cells
    protocol.comment('Transforming 5 uL of each purified assembly into 50 uL '
                     'chemically competent E. coli TOP10.')
    paired(p20, 5, assemblies, cells)

    # 28. quantify the remaining eluate
    protocol.comment(
        'MANUAL STEP (not simulated): measure the DNA concentration of the '
        'remaining 5 uL of each eluate with a NanoDrop-2000c for the CFU/ug '
        'calculation.')

    # 29. heat-shock transformation
    protocol.comment(
        'MANUAL STEP (not simulated): incubate cells_plate A1:D1 for 30 min on ice, '
        'heat shock at 42 C for 60 s, then return to ice for about 2 min.')

    # 30. recovery medium
    for dest in cells:
        pick(p300)
        p300.aspirate(250, lb_dextrose.bottom(z=5))
        p300.dispense(250, dest.bottom(z=3))
        p300.blow_out(dest.top(z=-2))
        p300.drop_tip()

    # 31-33. outgrowth, plating and scoring
    protocol.comment(
        'MANUAL STEP (not simulated): recover the cells at 37 C for 60 min with '
        'shaking (about 250 rpm).')
    protocol.comment(
        'MANUAL STEP (not simulated): plate 50-200 uL of each recovery (neat or a '
        '10x dilution, depending on predicted efficiency) onto separate LB agar '
        'plates containing kanamycin 50 ug/mL; incubate at 37 C overnight.')
    protocol.comment(
        'MANUAL STEP (not simulated): manually count colonies per plate and score '
        'the fraction showing the expected chromoprotein colour (purple, orange, '
        'blue, green); report CFU/ug of DNA plated.')
