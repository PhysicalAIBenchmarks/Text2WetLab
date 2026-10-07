from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate assembly of four chromoprotein '
                    'expression plasmids (4 fragments each)',
    'author': 'Claude',
    'description': 'Golden Gate assembly on the OT-2: Q5 PCR of fragments 1-7, '
                   'DpnI digest of template, fragment cleanup, Golden Gate '
                   'assembly (BsaI-HFv2 + T4 ligase), cleanup and '
                   'transformation into E. coli TOP10.',
    'apiLevel': '2.13'
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

    # ------------------------------------------------------------------
    # Pipettes and tips
    # ------------------------------------------------------------------
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']          # empty at start -> PCR master mix
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']
    lb_dextrose = tubes_15ml_1['A1']

    # PCR wells (column 1): fragments 1-7 in A1:G1
    frag_names = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pcr_wells = [pcr_plate[w] for w in frag_names]

    fwd_primers = [primer_plate[w] for w in frag_names]
    rev_primers = [primer_plate['%s2' % r] for r in 'ABCDEFG']

    # Template for each fragment 1-7 (template_plate wells)
    # frag1=tsPurple(A1), frag2=backbone(A1), frag3=YukonOFP(B1),
    # frag4=aeBlue(C1), frag5=backbone/KanR(A1), frag6=backbone(A1),
    # frag7=fuGFP(D1)
    template_wells = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    templates = [template_plate[w] for w in template_wells]

    assembly_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cells_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # ==================================================================
    # PCR master mix (for 8 reactions of 19 uL: water 106, 5X Q5 buffer
    # 40, 10 mM dNTPs 4, Q5 polymerase 2 = 152 uL)
    # ==================================================================
    protocol.comment('Step 1: Adding 106 uL nuclease-free water to the PCR '
                     'master mix tube (tubes_1_5ml_1 D1).')
    p300.transfer(106, water, pcr_mm, new_tip='always')

    protocol.comment('Step 2: Adding 40 uL 5X Q5 reaction buffer to the PCR '
                     'master mix tube.')
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='always')

    protocol.comment('Step 3: Adding 4 uL 10 mM dNTPs to the PCR master mix '
                     'tube.')
    p20.transfer(4, dntp, pcr_mm, new_tip='always')

    protocol.comment('Step 4: Adding 2 uL Q5 High-Fidelity DNA Polymerase to '
                     'the PCR master mix tube.')
    p20.transfer(2, q5_pol, pcr_mm, new_tip='always')

    protocol.comment('Step 5: Mixing the PCR master mix (5x at 100 uL).')
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # ==================================================================
    # PCR setup in pcr_plate A1:G1 (25 uL each)
    # ==================================================================
    protocol.comment('Step 6: Distributing 19 uL PCR master mix to pcr_plate '
                     'A1:G1 (fragments 1-7).')
    p20.distribute(19, pcr_mm, pcr_wells)

    protocol.comment('Step 7: Adding 2.5 uL of each forward primer (1 uM) to '
                     'the corresponding PCR well.')
    for src, dst in zip(fwd_primers, pcr_wells):
        p20.transfer(2.5, src, dst, new_tip='always')

    protocol.comment('Step 8: Adding 2.5 uL of each reverse primer (1 uM) to '
                     'the corresponding PCR well.')
    for src, dst in zip(rev_primers, pcr_wells):
        p20.transfer(2.5, src, dst, new_tip='always')

    protocol.comment('Step 9: Adding 1 uL of each linearized template '
                     '(0.5 ng/uL, 0.5 ng) to the corresponding PCR well.')
    for src, dst in zip(templates, pcr_wells):
        p20.transfer(1, src, dst, new_tip='always')

    protocol.comment('Step 10: Mixing each PCR (3x at 15 uL).')
    for well in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15, well)
        p20.drop_tip()

    # ------------------------------------------------------------------
    # Gradient PCR (manual, off-robot)
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 11 (manual): Seal pcr_plate (or move the PCR tubes) and '
        'transfer to the Bio-Rad C100 gradient thermocycler. Run: 98C 30 s; '
        '34 cycles of [98C 10 s, annealing 30 s at the AssemblyTron/j5 '
        'optimal-gradient temperature for each fragment, 72C extension at '
        'the time set by AssemblyTron (~20-30 s/kb)]; final extension 72C '
        '5 min; hold 4C. Take a sample of each reaction for gel '
        'electrophoresis, then return the reactions to the OT-2.')

    # ==================================================================
    # DpnI digestion of residual template (50 uL total per reaction)
    # ==================================================================
    protocol.comment('Step 12: Adding 19 uL nuclease-free water to each PCR '
                     '(A1:G1) for DpnI digestion.')
    p20.distribute(19, water, pcr_wells)

    protocol.comment('Step 13: Adding 5 uL rCutSmart Buffer to each PCR.')
    p20.distribute(5, rcutsmart, pcr_wells)

    protocol.comment('Step 14: Adding 1 uL DpnI to each PCR.')
    p20.distribute(1, dpni, pcr_wells)

    protocol.comment('Step 15: Mixing each DpnI digestion (3x at 30 uL).')
    for well in pcr_wells:
        p300.pick_up_tip()
        p300.mix(3, 30, well)
        p300.drop_tip()

    protocol.comment(
        'Step 16 (manual): Incubate pcr_plate A1:G1 at 37C for 30 min, then '
        '65C for 20 min (DpnI inactivation) on the thermocycler block.')

    # ------------------------------------------------------------------
    # Fragment clean-up (manual)
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 17 (manual): PAUSE. Clean and concentrate each of the 7 '
        'fragments with a Zymo DNA Clean & Concentrator-5 column: add 5:1 '
        'DNA Binding Buffer to sample (250 uL per 50 uL), spin 30 s, wash '
        '2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL water '
        'after 1 min at room temperature (30 s spin). Return the eluted '
        'fragments (20 uL each) to pcr_plate A1:G1 (fragments 1-7) and '
        'resume the protocol.')

    # ==================================================================
    # Golden Gate assembly setup in assembly_plate A1:D1 (20 uL each)
    # Assemblies: A1 = tsPurple (purple), B1 = YukonOFP (orange),
    #             C1 = aeBlue (blue),   D1 = fuGFP (green)
    # Each = fragment 2 (backbone) + fragment 5 (backbone/KanR) +
    #        fragment 6 (backbone) + one chromoprotein fragment (1,3,4,7)
    # ==================================================================
    protocol.comment('Step 18: Adding 7 uL nuclease-free water to '
                     'assembly_plate A1:D1.')
    p20.distribute(7, water, assembly_wells)

    protocol.comment('Step 19: Adding 2 uL 10X T4 DNA Ligase Buffer to each '
                     'assembly.')
    p20.distribute(2, t4_buffer, assembly_wells)

    protocol.comment('Step 20: Adding 3 uL of fragment 2 (backbone) to each '
                     'assembly.')
    p20.distribute(3, pcr_plate['B1'], assembly_wells)

    protocol.comment('Step 21: Adding 2 uL of fragment 5 (backbone/KanR) to '
                     'each assembly.')
    p20.distribute(2, pcr_plate['E1'], assembly_wells)

    protocol.comment('Step 22: Adding 3 uL of fragment 6 (backbone) to each '
                     'assembly.')
    p20.distribute(3, pcr_plate['F1'], assembly_wells)

    protocol.comment('Step 23: Adding 2 uL of each chromoprotein fragment '
                     '(1=tsPurple->A1, 3=YukonOFP->B1, 4=aeBlue->C1, '
                     '7=fuGFP->D1) to the corresponding assembly.')
    chromo_sources = [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']]
    for src, dst in zip(chromo_sources, assembly_wells):
        p20.transfer(2, src, dst, new_tip='always')

    protocol.comment('Step 24: Adding 1 uL Golden Gate Enzyme Mix '
                     '(BsaI-HFv2 + T4 ligase) to each assembly and mixing '
                     '5x.')
    for dst in assembly_wells:
        p20.transfer(1, gg_enzyme, dst, mix_after=(5, 15), new_tip='always')

    # ------------------------------------------------------------------
    # Golden Gate thermocycling (manual / Opentrons thermocycler module)
    # ------------------------------------------------------------------
    protocol.comment(
        'Step 25 (manual): Run the Golden Gate program on assembly_plate in '
        'the Opentrons thermocycler module: 30 cycles of 37C 5 min then 16C '
        '5 min; then 60C 5 min; hold at 4C. Lid about 85C. If no module is '
        'available, pause and move the reactions to another thermocycler.')

    protocol.comment(
        'Step 26 (manual): Clean and concentrate each assembly with a Zymo '
        'DNA Clean & Concentrator-5 column (5:1 DNA Binding Buffer to '
        'sample, wash 2 x 200 uL DNA Wash Buffer) and elute in 10 uL '
        'molecular grade water. Return the eluates (10 uL each) to '
        'assembly_plate A1:D1.')

    # ==================================================================
    # Transformation into E. coli TOP10
    # ==================================================================
    protocol.comment('Step 27: Adding 5 uL of each purified Golden Gate '
                     'assembly to the corresponding well of competent '
                     'TOP10 cells (cells_plate A1:D1).')
    for src, dst in zip(assembly_wells, cells_wells):
        p20.transfer(5, src, dst, new_tip='always')

    protocol.comment(
        'Step 28 (manual): Measure DNA concentration of the remaining 5 uL '
        'of each eluate with a NanoDrop-2000c for CFU/ug calculation.')

    protocol.comment(
        'Step 29 (manual): Incubate cells_plate A1:D1 for 30 min on ice, '
        'heat shock at 42C for 60 s, then return to ice for about 2 min.')

    protocol.comment('Step 30: Adding 250 uL LB + 0.2% (w/v) dextrose to '
                     'each transformation for outgrowth.')
    p300.distribute(250, lb_dextrose, cells_wells)

    protocol.comment(
        'Step 31 (manual): Recover the cells at 37C for 60 min with shaking '
        '(about 250 rpm).')

    protocol.comment(
        'Step 32 (manual): Plate 50-200 uL of each recovery (neat or a 10x '
        'dilution, depending on predicted efficiency) onto separate LB agar '
        'plates containing kanamycin 50 ug/mL; incubate at 37C overnight.')

    protocol.comment(
        'Step 33 (manual): Count colonies per plate and score the fraction '
        'showing the expected chromoprotein colour (A1 purple, B1 orange, '
        'C1 blue, D1 green); report CFU/ug of DNA plated.')
