"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow on the Opentrons OT-2 (Synth. Biol. 2022,
doi:10.1093/synbio/ysac032).  Seven fragments (2, 5, 6 = backbone / KanR parts;
1, 3, 4, 7 = chromoprotein parts) are amplified by gradient PCR from linearized
template plasmids, DpnI-digested, cleaned and concentrated, combined in volumes
proportional to fragment length with BsaI-HFv2 + T4 DNA ligase, cycled, cleaned
and transformed into chemically competent E. coli TOP10.

Manual / off-robot steps (thermocycling, incubations, column cleanups, plating)
cannot be simulated and are recorded with protocol.comment().
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 x 4-fragment chromoprotein plasmids',
    'author': 'Automated from AssemblyTron (Synth. Biol. 2022, ysac032)',
    'description': ('Gradient PCR of 7 fragments, DpnI digestion, Golden Gate '
                    'assembly of 4 chromoprotein expression plasmids and '
                    'transformation into E. coli TOP10.'),
    'apiLevel': '2.13',
}


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
    pcr_mm = tubes_1_5ml_1['D1']        # PCR master mix (made below)
    rcutsmart = tubes_1_5ml_1['A2']     # rCutSmart Buffer
    dpni = tubes_1_5ml_1['B2']          # DpnI
    t4_buffer = tubes_1_5ml_1['C2']     # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']     # Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase)
    lb_dextrose = tubes_15ml_1['A1']    # LB + 0.2% (w/v) dextrose

    # Fragments 1-7 live in column 1 of the PCR / fragment plate.
    frag = {i + 1: pcr_plate.wells()[i] for i in range(7)}       # A1..G1
    fwd_primer = {i + 1: primer_plate.wells()[i] for i in range(7)}   # A1..G1
    rev_primer = {i + 1: primer_plate.wells()[8 + i] for i in range(7)}  # A2..G2

    pcr_wells = [frag[i] for i in range(1, 8)]
    assemblies = [assembly_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]
    cells = [cells_plate[w] for w in ('A1', 'B1', 'C1', 'D1')]

    # Each PCR uses the template carrying the part being amplified.
    # tsPurple (A1), YukonOFP (B1), aeBlue (C1), fuGFP (D1).
    templates = [template_plate[w] for w in
                 ('A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1')]

    # ------------------------------------------------------------------
    # Tip bookkeeping: tips are unlimited, so recycle a rack once it is spent.
    # ------------------------------------------------------------------
    used = {'left': 0, 'right': 0}

    def tip_on(pip):
        mount = 'left' if pip is p20 else 'right'
        if used[mount] >= 96:
            pip.reset_tipracks()
            used[mount] = 0
        pip.pick_up_tip()
        used[mount] += 1

    def tip_off(pip):
        pip.drop_tip()

    def pip_for(volume):
        """20 uL pipette handles 1-20 uL, 300 uL pipette handles 20-300 uL."""
        return p20 if volume < 20 else p300

    def move(volume, source, dests, mix_after=None):
        """One fresh tip per destination; no tip is ever returned to a shared
        stock after it has entered a reaction well."""
        if not isinstance(dests, (list, tuple)):
            dests = [dests]
        pip = pip_for(volume)
        for dest in dests:
            tip_on(pip)
            pip.aspirate(volume, source)
            pip.dispense(volume, dest)
            if mix_after is not None:
                pip.mix(mix_after[0], mix_after[1], dest)
            pip.blow_out(dest.top())
            tip_off(pip)

    def move_paired(volume, sources, dests, mix_after=None):
        """Source i -> destination i, fresh tip for every pair."""
        pip = pip_for(volume)
        for source, dest in zip(sources, dests):
            tip_on(pip)
            pip.aspirate(volume, source)
            pip.dispense(volume, dest)
            if mix_after is not None:
                pip.mix(mix_after[0], mix_after[1], dest)
            pip.blow_out(dest.top())
            tip_off(pip)

    def mix_wells(reps, volume, wells):
        pip = pip_for(volume)
        for well in wells:
            tip_on(pip)
            pip.mix(reps, volume, well)
            pip.blow_out(well.top())
            tip_off(pip)

    # ==================================================================
    # PCR setup: 7 fragments, 25 uL each, 0.1 uM primers, 0.5 ng template
    # ==================================================================
    protocol.comment('--- PCR master mix for 8 reactions (7 fragments + overage) ---')

    # Step 1: nuclease-free water into the master-mix tube.
    move(106, water, pcr_mm)

    # Step 2: 5X Q5 reaction buffer.
    move(40, q5_buffer, pcr_mm)

    # Step 3: 10 mM dNTPs.
    move(4, dntp, pcr_mm)

    # Step 4: Q5 High-Fidelity DNA Polymerase.
    move(2, q5_pol, pcr_mm)

    # Step 5: homogenize the 152 uL master mix.
    mix_wells(5, 100, [pcr_mm])

    protocol.comment('--- Distributing PCR master mix, primers and templates ---')

    # Step 6: 19 uL master mix into each of the 7 PCRs.
    move(19, pcr_mm, pcr_wells)

    # Step 7: 2.5 uL forward primer (1 uM stock -> 0.1 uM final).
    move_paired(2.5, [fwd_primer[i] for i in range(1, 8)], pcr_wells)

    # Step 8: 2.5 uL reverse primer (1 uM stock -> 0.1 uM final).
    move_paired(2.5, [rev_primer[i] for i in range(1, 8)], pcr_wells)

    # Step 9: 1 uL linearized template (0.5 ng/uL -> 0.5 ng per reaction).
    move_paired(1, templates, pcr_wells)

    # Step 10: mix each 25 uL reaction.
    mix_wells(3, 15, pcr_wells)

    # Step 11: off-robot gradient PCR.
    protocol.comment(
        'MANUAL STEP: Seal pcr_plate (or move the PCR tubes) and transfer manually '
        'to the Bio-Rad C100 gradient thermocycler. Run: 98 C 30 s; 34 cycles of '
        '98 C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient '
        'temperature for each fragment, 72 C extension at the time set by '
        'AssemblyTron (about 20-30 s/kb); final extension 72 C 5 min; hold 4 C. '
        'Take a sample of each reaction for gel electrophoresis, then return to '
        'the OT-2.')

    # ==================================================================
    # DpnI digestion of residual methylated plasmid template
    # ==================================================================
    protocol.comment('--- DpnI digestion of residual template (50 uL reactions) ---')

    # Step 12: top each PCR up with water.
    move(19, water, pcr_wells)

    # Step 13: rCutSmart Buffer.
    move(5, rcutsmart, pcr_wells)

    # Step 14: DpnI.
    move(1, dpni, pcr_wells)

    # Step 15: mix each 50 uL digest.
    mix_wells(3, 30, pcr_wells)

    # Step 16: off-robot incubation.
    protocol.comment(
        'MANUAL STEP: Incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for '
        '20 min (DpnI inactivation) on the thermocycler block.')

    # Step 17: column cleanup of each fragment (removes polymerase, which would
    # otherwise fill in the BsaI overhangs).
    protocol.comment(
        'MANUAL STEP: Pause the protocol. Clean and concentrate each of the 7 '
        'fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding '
        'Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA Wash '
        'Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature '
        '(30 s spin). Return the eluted fragments to their original positions '
        'pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')
    protocol.pause('Clean and concentrate fragments 1-7, return them to '
                   'pcr_plate A1:G1, then resume.')

    # ==================================================================
    # Golden Gate assembly: 20 uL reactions, fragment volume ~ fragment length
    # ==================================================================
    protocol.comment('--- Golden Gate assembly of 4 four-fragment plasmids ---')

    # Step 18: nuclease-free water.
    move(7, water, assemblies)

    # Step 19: 10X T4 DNA Ligase Buffer.
    move(2, t4_buffer, assemblies)

    # Step 20: fragment 2 (backbone), shared by all four assemblies.
    move(3, frag[2], assemblies)

    # Step 21: fragment 5 (backbone / KanR), shared by all four assemblies.
    move(2, frag[5], assemblies)

    # Step 22: fragment 6 (backbone), shared by all four assemblies.
    move(3, frag[6], assemblies)

    # Step 23: the four chromoprotein fragments, one per assembly.
    # A1 <- fragment 1 (tsPurple), B1 <- fragment 3 (YukonOFP),
    # C1 <- fragment 4 (aeBlue),   D1 <- fragment 7 (fuGFP).
    move_paired(2, [frag[1], frag[3], frag[4], frag[7]], assemblies)

    # Step 24: Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase), then mix.
    move(1, gg_enzyme, assemblies, mix_after=(5, 10))

    # Step 25: thermocycler assembly program.
    protocol.comment(
        'MANUAL STEP: Run Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; then 60 C '
        '5 min; hold at 4 C. Lid about 85 C. If no module is available, pause and '
        'move reactions to another thermocycler.')

    # Step 26: cleanup of the assemblies.
    protocol.comment(
        'MANUAL STEP: Clean and concentrate each assembly with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in '
        '10 uL molecular grade water; return the eluates to assembly_plate A1:D1.')
    protocol.pause('Clean and concentrate the 4 assemblies, return the 10 uL '
                   'eluates to assembly_plate A1:D1, then resume.')

    # ==================================================================
    # Transformation into chemically competent E. coli TOP10
    # ==================================================================
    protocol.comment('--- Transformation into E. coli TOP10 ---')

    # Step 27: 5 uL of each purified assembly into 50 uL of competent cells.
    move_paired(5, assemblies, cells)

    # Step 28: quantify the retained half of each eluate.
    protocol.comment(
        'MANUAL STEP: Measure DNA concentration of the remaining 5 uL of each '
        'eluate with a NanoDrop-2000c for CFU/ug calculation.')

    # Step 29: heat-shock transformation.
    protocol.comment(
        'MANUAL STEP: Incubate cells_plate A1:D1 for 30 min on ice, heat shock at '
        '42 C for 60 s, then return to ice for about 2 min.')
    protocol.pause('Perform the ice / 42 C 60 s heat shock / ice incubation on '
                   'cells_plate A1:D1, then resume.')

    # Step 30: outgrowth medium (LB + 0.2% dextrose for catabolite repression).
    move(250, lb_dextrose, cells)

    # Step 31: recovery.
    protocol.comment(
        'MANUAL STEP: Recover cells at 37 C for 60 min with shaking '
        '(about 250 rpm).')

    # Step 32: plating.
    protocol.comment(
        'MANUAL STEP: Plate 50-200 uL of each recovery (neat or a 10x dilution, '
        'depending on predicted efficiency) onto separate LB agar plates '
        'containing kanamycin 50 ug/mL; incubate at 37 C overnight.')

    # Step 33: scoring.
    protocol.comment(
        'MANUAL STEP: Manually count colonies per plate and score the fraction '
        'showing the expected chromoprotein colour (purple, orange, blue, green); '
        'report CFU/ug of DNA plated.')
