"""
Golden Gate assembly of four four-fragment chromoprotein expression plasmids
on the Opentrons OT-2, after the AssemblyTron workflow.

Reference: "AssemblyTron: flexible automation of DNA assembly with Opentrons
OT-2 lab robots", Synth. Biol. 2022, doi:10.1093/synbio/ysac032 (CC BY).

Workflow
--------
1.  Build a Q5 PCR master mix for 8 reactions (7 fragments + overage).
2.  Set up 7 x 25 uL PCRs: 19 uL master mix, 2.5 uL each j5-designed forward
    and reverse primer (1 uM -> 0.1 uM final), 1 uL linearized template
    (0.5 ng/uL -> 0.5 ng per reaction).
3.  OFF DECK: gradient PCR on a Bio-Rad C100 (the OT-2 thermocycler module has
    no gradient capability), then back to the OT-2.
4.  DpnI digestion of residual template, then DpnI heat inactivation.
5.  OFF DECK: Zymo DNA Clean & Concentrator-5 cleanup of each fragment
    (removes polymerase, which otherwise fills in the BsaI sticky ends).
6.  Golden Gate reactions: fragment volumes proportional to fragment length
    (approximately equimolar, assuming equal PCR efficiency) plus T4 ligase
    buffer and BsaI-HFv2 / T4 ligase enzyme mix, 20 uL total per assembly.
7.  Thermocycler Golden Gate program, cleanup, and transformation of 5 uL of
    each assembly into 50 uL chemically competent E. coli TOP10, followed by
    outgrowth in LB + 0.2% (w/v) dextrose.

Fragment map (Figure 3 of the paper):
    Fragments 2, 5, 6 = shared backbone / KanR parts (in every assembly)
    Fragments 1, 3, 4, 7 = the four chromoproteins
        1 -> tsPurple (purple)   3 -> aeBlue (blue)
        4 -> fuGFP (green)       7 -> YukonOFP (orange)
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 x 4-fragment chromoprotein plasmids',
    'author': 'Automated from AssemblyTron (Synth. Biol. 2022, ysac032)',
    'description': (
        'PCR setup, DpnI digestion, Golden Gate assembly with BsaI-HFv2 + T4 '
        'ligase, and transformation into E. coli TOP10 for four four-fragment '
        'chromoprotein expression plasmids.'
    ),
    'apiLevel': '2.13',
}

# Number of tips in a full single-channel rack; used to recycle racks.
TIPS_PER_RACK = 96


def run(protocol):
    # ------------------------------------------------------------------
    # Labware
    # ------------------------------------------------------------------
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tubes_50ml_1 = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
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

    # ------------------------------------------------------------------
    # Reagent positions
    # ------------------------------------------------------------------
    water = tubes_50ml_1['A1']          # nuclease-free water
    q5_buffer = tubes_1_5ml_1['A1']     # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1['B1']          # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1['C1']        # Q5 High-Fidelity DNA Polymerase
    pcr_mm = tubes_1_5ml_1['D1']        # PCR master mix (built in this run)
    rcutsmart = tubes_1_5ml_1['A2']     # rCutSmart Buffer
    dpni = tubes_1_5ml_1['B2']          # DpnI
    t4_buffer = tubes_1_5ml_1['C2']     # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']     # BsaI-HFv2 + T4 DNA ligase mix
    lb_dextrose = tubes_15ml_1['A1']    # LB + 0.2% (w/v) dextrose

    # Fragments 1-7 occupy column 1 of the PCR / fragment plate.
    frag_wells = [pcr_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    fwd_primers = [primer_plate[w] for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    rev_primers = [primer_plate[w] for w in ('A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2')]
    # Template for each fragment 1-7 (tsPurple, YukonOFP, aeBlue, fuGFP plasmids).
    templates = [template_plate[w] for w in ('A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1')]

    assembly_wells = [assembly_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]
    cell_wells = [cells_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]

    # ------------------------------------------------------------------
    # Tip handling: racks are reused once exhausted, and every tip that is
    # picked up is dropped again, so the run never ends holding a tip.
    # ------------------------------------------------------------------
    tips_used = {'left': 0, 'right': 0}

    def pick_up(pipette):
        mount = pipette.mount
        if tips_used[mount] >= TIPS_PER_RACK:
            pipette.reset_tipracks()
            tips_used[mount] = 0
        pipette.pick_up_tip()
        tips_used[mount] += 1

    def pipette_for(volume):
        """p20 handles 1-20 uL, p300 handles 20-300 uL."""
        return p20 if volume <= 20 else p300

    def move(volume, source, dest, mix_after=None):
        """One aspirate/dispense pair with a fresh tip."""
        pipette = pipette_for(volume)
        pick_up(pipette)
        pipette.aspirate(volume, source)
        pipette.dispense(volume, dest)
        if mix_after is not None:
            reps, mix_vol = mix_after
            pipette.mix(reps, mix_vol, dest)
        pipette.blow_out(dest.top())
        pipette.drop_tip()

    def distribute_one_tip(volume, source, dests):
        """Serial transfers from a single source with one tip."""
        pipette = pipette_for(volume)
        pick_up(pipette)
        for dest in dests:
            pipette.aspirate(volume, source)
            pipette.dispense(volume, dest)
            pipette.blow_out(dest.top())
        pipette.drop_tip()

    def mix_wells(reps, volume, wells):
        """Mix each well with its own fresh tip."""
        pipette = pipette_for(volume)
        for well in wells:
            pick_up(pipette)
            pipette.mix(reps, volume, well)
            pipette.blow_out(well.top())
            pipette.drop_tip()

    # ==================================================================
    # Part 1 - PCR master mix for 8 reactions (7 fragments + overage)
    # ==================================================================
    protocol.comment('--- Part 1: Q5 PCR master mix (8 reactions) in tubes_1_5ml_1 D1 ---')

    # Step 1: 106 uL nuclease-free water.
    protocol.comment('Step 1: 106 uL nuclease-free water -> pcr_mm (tubes_1_5ml_1 D1).')
    move(106, water, pcr_mm)

    # Step 2: 40 uL 5X Q5 reaction buffer (1X final in 8 x 25 uL).
    protocol.comment('Step 2: 40 uL 5X Q5 reaction buffer -> pcr_mm.')
    move(40, q5_buffer, pcr_mm)

    # Step 3: 4 uL 10 mM dNTPs (200 uM final).
    protocol.comment('Step 3: 4 uL 10 mM dNTPs -> pcr_mm.')
    move(4, dntp, pcr_mm)

    # Step 4: 2 uL Q5 High-Fidelity DNA Polymerase.
    protocol.comment('Step 4: 2 uL Q5 High-Fidelity DNA Polymerase -> pcr_mm.')
    move(2, q5_pol, pcr_mm)

    # Step 5: homogenise the 152 uL master mix.
    protocol.comment('Step 5: mix pcr_mm 5 times at 100 uL.')
    mix_wells(5, 100, [pcr_mm])

    # ==================================================================
    # Part 2 - PCR setup, 7 x 25 uL reactions
    # ==================================================================
    protocol.comment('--- Part 2: PCR setup for fragments 1-7 in pcr_plate A1:G1 ---')

    # Step 6: 19 uL master mix per reaction.
    protocol.comment('Step 6: 19 uL PCR master mix -> pcr_plate A1:G1.')
    distribute_one_tip(19, pcr_mm, frag_wells)

    # Step 7: 2.5 uL forward primer (1 uM stock -> 0.1 uM final in 25 uL).
    protocol.comment('Step 7: 2.5 uL forward primer (1 uM) -> matching pcr_plate well.')
    for primer, dest in zip(fwd_primers, frag_wells):
        move(2.5, primer, dest)

    # Step 8: 2.5 uL reverse primer.
    protocol.comment('Step 8: 2.5 uL reverse primer (1 uM) -> matching pcr_plate well.')
    for primer, dest in zip(rev_primers, frag_wells):
        move(2.5, primer, dest)

    # Step 9: 1 uL linearized template at 0.5 ng/uL = 0.5 ng per reaction.
    protocol.comment('Step 9: 1 uL linearized template (0.5 ng/uL) -> matching pcr_plate well.')
    for template, dest in zip(templates, frag_wells):
        move(1, template, dest)

    # Step 10: homogenise each 25 uL reaction.
    protocol.comment('Step 10: mix pcr_plate A1:G1 3 times at 15 uL.')
    mix_wells(3, 15, frag_wells)

    # Step 11: off-deck gradient PCR (not simulated).
    protocol.comment(
        'Step 11 (manual): Seal pcr_plate (or move the PCR tubes) and transfer manually '
        'to the Bio-Rad C100 gradient thermocycler. Run: 98 C 30 s; 34 cycles of '
        '98 C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature '
        'for each fragment, 72 C extension at the time set by AssemblyTron '
        '(about 20-30 s/kb); final extension 72 C 5 min; hold 4 C. Take a sample of '
        'each reaction for gel electrophoresis, then return to the OT-2.')
    protocol.pause(
        'Run the gradient PCR off deck on the Bio-Rad C100, then return pcr_plate to '
        'slot 5 and resume.')

    # ==================================================================
    # Part 3 - DpnI digestion of residual plasmid template
    # ==================================================================
    protocol.comment('--- Part 3: DpnI digestion (50 uL per fragment) ---')

    # Step 12: 19 uL water into each PCR.
    protocol.comment('Step 12: 19 uL nuclease-free water -> pcr_plate A1:G1.')
    distribute_one_tip(19, water, frag_wells)

    # Step 13: 5 uL rCutSmart Buffer.
    protocol.comment('Step 13: 5 uL rCutSmart Buffer -> pcr_plate A1:G1.')
    distribute_one_tip(5, rcutsmart, frag_wells)

    # Step 14: 1 uL DpnI.
    protocol.comment('Step 14: 1 uL DpnI -> pcr_plate A1:G1.')
    distribute_one_tip(1, dpni, frag_wells)

    # Step 15: homogenise each 50 uL digest.
    protocol.comment('Step 15: mix pcr_plate A1:G1 3 times at 30 uL.')
    mix_wells(3, 30, frag_wells)

    # Step 16: digestion and heat inactivation (not simulated).
    protocol.comment(
        'Step 16 (manual): Incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for '
        '20 min (DpnI inactivation) on the thermocycler block.')

    # Step 17: column cleanup of each fragment (not simulated).
    protocol.comment(
        'Step 17 (manual): Pause the protocol. Clean and concentrate each of the 7 '
        'fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding '
        'Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA Wash '
        'Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature '
        '(30 s spin). Return the eluted fragments to their original positions '
        'pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')
    protocol.pause(
        'Clean and concentrate fragments 1-7, elute each in 20 uL water, return them '
        'to pcr_plate A1:G1 and resume.')

    # ==================================================================
    # Part 4 - Golden Gate assembly, 20 uL per reaction
    # Fragment volumes are proportional to fragment length, giving a roughly
    # equimolar mix: 3 uL frag 2, 2 uL frag 5, 3 uL frag 6 (shared backbone)
    # plus 2 uL of one chromoprotein fragment per assembly.
    # ==================================================================
    protocol.comment('--- Part 4: Golden Gate assemblies in assembly_plate A1:D1 ---')

    # Step 18: 7 uL water per reaction.
    protocol.comment('Step 18: 7 uL nuclease-free water -> assembly_plate A1:D1.')
    distribute_one_tip(7, water, assembly_wells)

    # Step 19: 2 uL 10X T4 DNA Ligase Buffer (1X in 20 uL).
    protocol.comment('Step 19: 2 uL 10X T4 DNA Ligase Buffer -> assembly_plate A1:D1.')
    distribute_one_tip(2, t4_buffer, assembly_wells)

    # Step 20: fragment 2 (backbone) into all four assemblies.
    protocol.comment('Step 20: 3 uL fragment 2 (backbone, pcr_plate B1) -> assembly_plate A1:D1.')
    for dest in assembly_wells:
        move(3, pcr_plate['B1'], dest)

    # Step 21: fragment 5 (backbone / KanR) into all four assemblies.
    protocol.comment('Step 21: 2 uL fragment 5 (backbone/KanR, pcr_plate E1) -> assembly_plate A1:D1.')
    for dest in assembly_wells:
        move(2, pcr_plate['E1'], dest)

    # Step 22: fragment 6 (backbone) into all four assemblies.
    protocol.comment('Step 22: 3 uL fragment 6 (backbone, pcr_plate F1) -> assembly_plate A1:D1.')
    for dest in assembly_wells:
        move(3, pcr_plate['F1'], dest)

    # Step 23: one chromoprotein fragment per assembly.
    #   fragment 1 (A1) -> assembly A1, fragment 3 (C1) -> assembly B1,
    #   fragment 4 (D1) -> assembly C1, fragment 7 (G1) -> assembly D1.
    protocol.comment(
        'Step 23: 2 uL chromoprotein fragments 1, 3, 4, 7 (pcr_plate A1, C1, D1, G1) '
        '-> assembly_plate A1, B1, C1, D1.')
    chromo_wells = [pcr_plate[w] for w in ('A1', 'C1', 'D1', 'G1')]
    for source, dest in zip(chromo_wells, assembly_wells):
        move(2, source, dest)

    # Step 24: 1 uL BsaI-HFv2 + T4 ligase mix, mixed in after dispensing.
    protocol.comment(
        'Step 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase) -> '
        'assembly_plate A1:D1, mixing 5 times after each dispense.')
    for dest in assembly_wells:
        move(1, gg_enzyme, dest, mix_after=(5, 10))

    # Step 25: Golden Gate thermocycling (not simulated).
    protocol.comment(
        'Step 25 (manual): Run Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; then 60 C 5 min; '
        'hold at 4 C. Lid about 85 C. If no module is available, pause and move '
        'reactions to another thermocycler.')

    # Step 26: cleanup of each assembly (not simulated).
    protocol.comment(
        'Step 26 (manual): Clean and concentrate each assembly with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in 10 uL '
        'molecular grade water; return the eluates to assembly_plate A1:D1.')
    protocol.pause(
        'Run the Golden Gate program, clean and concentrate each assembly, elute in '
        '10 uL water, return the eluates to assembly_plate A1:D1 and resume.')

    # ==================================================================
    # Part 5 - Transformation into chemically competent E. coli TOP10
    # ==================================================================
    protocol.comment('--- Part 5: transformation into E. coli TOP10 ---')

    # Step 27: 5 uL of each purified assembly into 50 uL of competent cells.
    protocol.comment(
        'Step 27: 5 uL purified Golden Gate assembly -> matching cells_plate well '
        '(50 uL TOP10 competent cells).')
    for source, dest in zip(assembly_wells, cell_wells):
        move(5, source, dest)

    # Step 28: quantify the retained eluate (not simulated).
    protocol.comment(
        'Step 28 (manual): Measure DNA concentration of the remaining 5 uL of each '
        'eluate with a NanoDrop-2000c for CFU/ug calculation.')

    # Step 29: heat shock (not simulated).
    protocol.comment(
        'Step 29 (manual): Incubate cells_plate A1:D1 for 30 min on ice, heat shock at '
        '42 C for 60 s, then return to ice for about 2 min.')
    protocol.pause(
        'Ice 30 min, heat shock 42 C for 60 s, ice about 2 min, then return cells_plate '
        'to slot 7 and resume.')

    # Step 30: 250 uL LB + 0.2% dextrose for catabolite-repressed outgrowth.
    protocol.comment('Step 30: 250 uL LB + 0.2% (w/v) dextrose -> cells_plate A1:D1.')
    distribute_one_tip(250, lb_dextrose, cell_wells)

    # Step 31: recovery (not simulated).
    protocol.comment(
        'Step 31 (manual): Recover cells at 37 C for 60 min with shaking '
        '(about 250 rpm).')

    # Step 32: plating (not simulated).
    protocol.comment(
        'Step 32 (manual): Plate 50-200 uL of each recovery (neat or a 10x dilution, '
        'depending on predicted efficiency) onto separate LB agar plates containing '
        'kanamycin 50 ug/mL; incubate at 37 C overnight.')

    # Step 33: scoring (not simulated).
    protocol.comment(
        'Step 33 (manual): Manually count colonies per plate and score the fraction '
        'showing the expected chromoprotein colour (purple, orange, blue, green); '
        'report CFU/ug of DNA plated.')

    protocol.comment('Protocol complete.')
