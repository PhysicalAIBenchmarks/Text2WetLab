# Golden Gate assembly of four four-fragment chromoprotein expression plasmids
# with AssemblyTron on the OT-2 (Synth. Biol. 2022, doi:10.1093/synbio/ysac032).
#
# Steps 1-33 of the task: PCR master mix, primer/template addition, gradient PCR
# (manual comment), DpnI digestion, cleanup (manual comment), Golden Gate
# assembly, thermocycling (manual comment), cleanup (manual comment), and
# transformation of E. coli TOP10.

metadata = {'apiLevel': '2.13'}


def run(protocol):
    # Tip racks
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    # Pipettes
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # Labware
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

    # Reagent sources
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

    # PCR reactions for fragments 1-7 in pcr_plate column 1
    pcr_wells = [pcr_plate[w] for w in
                 ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    fwd_primers = [primer_plate[w] for w in
                   ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    rev_primers = [primer_plate[w] for w in
                   ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    templates = [template_plate[w] for w in
                 ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]

    # Golden Gate assemblies A1:D1 and transformation destinations
    asm_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cells_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # --- PCR master mix (8 reactions) ---
    # Step 1: 106 uL water -> pcr_mm tube
    p300.reset_tipracks()
    p300.transfer(106, water, pcr_mm, new_tip='once')
    # Step 2: 40 uL 5X Q5 reaction buffer -> pcr_mm tube
    p300.reset_tipracks()
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='once')
    # Step 3: 4 uL 10 mM dNTPs -> pcr_mm tube
    p20.reset_tipracks()
    p20.transfer(4, dntp, pcr_mm, new_tip='once')
    # Step 4: 2 uL Q5 polymerase -> pcr_mm tube
    p20.reset_tipracks()
    p20.transfer(2, q5_pol, pcr_mm, new_tip='once')
    # Step 5: mix master mix, 5 cycles at 100 uL
    p300.reset_tipracks()
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # --- PCR setup ---
    # Step 6: 19 uL master mix to each PCR well
    p20.reset_tipracks()
    p20.transfer(19, pcr_mm, pcr_wells, new_tip='always')
    # Step 7: 2.5 uL forward primer to each PCR well
    p20.reset_tipracks()
    p20.transfer(2.5, fwd_primers, pcr_wells, new_tip='always')
    # Step 8: 2.5 uL reverse primer to each PCR well
    p20.reset_tipracks()
    p20.transfer(2.5, rev_primers, pcr_wells, new_tip='always')
    # Step 9: 1 uL linearized template (0.5 ng/uL) to each PCR well
    p20.reset_tipracks()
    p20.transfer(1, templates, pcr_wells, new_tip='always')
    # Step 10: mix each PCR, 3 cycles at 15 uL
    p20.reset_tipracks()
    for w in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15, w)
        p20.drop_tip()

    # Step 11: gradient PCR (manual)
    protocol.comment(
        'Seal pcr_plate (or move the PCR tubes) and transfer manually to the '
        'Bio-Rad C100 gradient thermocycler. Run: 98C 30 s; 34 cycles of '
        '98C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient '
        'temperature for each fragment, 72C extension at the time set by '
        'AssemblyTron (about 20-30 s/kb); final extension 72C 5 min; hold '
        '4C. Take a sample of each reaction for gel electrophoresis, then '
        'return to the OT-2.')

    # --- DpnI digestion of residual template ---
    # Step 12: 19 uL water to each PCR well
    p20.reset_tipracks()
    p20.transfer(19, water, pcr_wells, new_tip='once')
    # Step 13: 5 uL rCutSmart Buffer to each PCR well
    p20.reset_tipracks()
    p20.transfer(5, rcutsmart, pcr_wells, new_tip='once')
    # Step 14: 1 uL DpnI to each PCR well
    p20.reset_tipracks()
    p20.transfer(1, dpni, pcr_wells, new_tip='once')
    # Step 15: mix each PCR well, 3 cycles at 30 uL
    p300.reset_tipracks()
    for w in pcr_wells:
        p300.pick_up_tip()
        p300.mix(3, 30, w)
        p300.drop_tip()

    # Step 16: DpnI incubation (manual)
    protocol.comment(
        'Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min '
        '(DpnI inactivation) on the thermocycler block.')

    # Step 17: fragment cleanup (manual)
    protocol.comment(
        'Pause the protocol. Clean and concentrate each of the 7 fragments '
        'with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding '
        'Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA '
        'Wash Buffer (30 s spins), elute in 20 uL water after 1 min at room '
        'temperature (30 s spin). Return the eluted fragments to their '
        'original positions pcr_plate A1:G1 (fragments 1-7) and resume the '
        'protocol.')

    # --- Golden Gate assembly (20 uL reactions, assembly_plate A1:D1) ---
    # Step 18: 7 uL water to each assembly well
    p20.reset_tipracks()
    p20.transfer(7, water, asm_wells, new_tip='once')
    # Step 19: 2 uL 10X T4 DNA Ligase Buffer to each assembly well
    p20.reset_tipracks()
    p20.transfer(2, t4_buffer, asm_wells, new_tip='once')
    # Step 20: 3 uL fragment 2 (backbone) to each assembly well
    p20.reset_tipracks()
    p20.transfer(3, pcr_plate['B1'], asm_wells, new_tip='once')
    # Step 21: 2 uL fragment 5 (backbone/KanR) to each assembly well
    p20.reset_tipracks()
    p20.transfer(2, pcr_plate['E1'], asm_wells, new_tip='once')
    # Step 22: 3 uL fragment 6 (backbone) to each assembly well
    p20.reset_tipracks()
    p20.transfer(3, pcr_plate['F1'], asm_wells, new_tip='once')
    # Step 23: 2 uL chromoprotein fragments 1, 3, 4, 7 (A1, C1, D1, G1) to
    # assembly wells A1, B1, C1, D1 respectively
    p20.reset_tipracks()
    p20.transfer(2, [pcr_plate['A1'], pcr_plate['C1'],
                     pcr_plate['D1'], pcr_plate['G1']],
                 asm_wells, new_tip='always')
    # Step 24: 1 uL Golden Gate Enzyme Mix to each assembly well, mix after
    p20.reset_tipracks()
    p20.transfer(1, gg_enzyme, asm_wells, new_tip='once', mix_after=(5, 15))

    # Step 25: Golden Gate thermocycling (manual)
    protocol.comment(
        'Run Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37C 5 min then 16C 5 min; then '
        '60C 5 min; hold at 4C. Lid about 85C. If no module is available, '
        'pause and move reactions to another thermocycler.')

    # Step 26: assembly cleanup (manual)
    protocol.comment(
        'Clean and concentrate each assembly with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and '
        'elute in 10 uL molecular grade water; return the eluates to '
        'assembly_plate A1:D1.')

    # --- Transformation into E. coli TOP10 ---
    # Step 27: 5 uL purified assembly to each cells well
    p20.reset_tipracks()
    p20.transfer(5, asm_wells, cells_wells, new_tip='always')

    # Step 28: NanoDrop quantification (manual)
    protocol.comment(
        'Measure DNA concentration of the remaining 5 uL of each eluate with '
        'a NanoDrop-2000c for CFU/ug calculation.')

    # Step 29: heat shock (manual)
    protocol.comment(
        'Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42C for '
        '60 s, then return to ice for about 2 min.')

    # Step 30: 250 uL LB + 0.2% dextrose to each cells well
    p300.reset_tipracks()
    p300.transfer(250, lb_dextrose, cells_wells, new_tip='once')

    # Step 31: recovery (manual)
    protocol.comment(
        'Recover cells at 37C for 60 min with shaking (about 250 rpm).')

    # Step 32: plating (manual)
    protocol.comment(
        'Plate 50-200 uL of each recovery (neat or a 10x dilution, depending '
        'on predicted efficiency) onto separate LB agar plates containing '
        'kanamycin 50 ug/mL; incubate at 37C overnight.')

    # Step 33: colony scoring (manual)
    protocol.comment(
        'Manually count colonies per plate and score the fraction showing '
        'the expected chromoprotein colour (purple, orange, blue, green); '
        'report CFU/ug of DNA plated.')
