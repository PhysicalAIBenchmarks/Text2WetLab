"""AssemblyTron Golden Gate assembly of four four-fragment chromoprotein plasmids.

Build four chromoprotein expression plasmids (tsPurple, YukonOFP, aeBlue,
fuGFP) starting from PCR amplification of seven fragments with j5-designed
primers, DpnI digestion, fragment clean-up, Golden Gate assembly with
BsaI-HFv2 + T4 DNA ligase, and transformation into E. coli TOP10.

Manual steps (thermocycling, column clean-ups, heat shock, recovery, plating)
cannot be simulated and are recorded with protocol.comment() at the point
they occur.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate Assembly of Chromoprotein Plasmids',
    'author': 'AssemblyTron',
    'description': 'Four four-fragment chromoprotein expression plasmids by Golden Gate assembly.',
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------ labware
    tubes_50ml = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml = protocol.load_labware(
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
    tubes_15ml = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # ---------------------------------------------------------------- reagents
    water = tubes_50ml['A1']
    q5_buffer = tubes_1_5ml['A1']
    dntp = tubes_1_5ml['B1']
    q5_pol = tubes_1_5ml['C1']
    pcr_mm = tubes_1_5ml['D1']        # PCR master mix prepared in situ
    rcutsmart = tubes_1_5ml['A2']
    dpni = tubes_1_5ml['B2']
    t4_buffer = tubes_1_5ml['C2']
    gg_enzyme = tubes_1_5ml['D2']     # BsaI-HFv2 + T4 ligase
    lb_dextrose = tubes_15ml['A1']

    fwd_primer_wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    rev_primer_wells = ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']
    pcr_wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    template_src = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    assembly_wells = ['A1', 'B1', 'C1', 'D1']
    cells_wells = ['A1', 'B1', 'C1', 'D1']

    pcr_dest = [pcr_plate[w] for w in pcr_wells]
    assembly_dest = [assembly_plate[w] for w in assembly_wells]
    cells_dest = [cells_plate[w] for w in cells_wells]

    # 1-4. Prepare the PCR master mix (buffer, dNTPs, polymerase, water) in D1.
    p300.transfer(106, water, pcr_mm, new_tip='once')            # 106 µL water
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='once')         # 40 µL 5X Q5 buffer
    p20.transfer(4, dntp, pcr_mm, new_tip='once')                # 4 µL 10 mM dNTPs
    p20.transfer(2, q5_pol, pcr_mm, new_tip='once')              # 2 µL Q5 polymerase

    # 5. Mix the master mix.
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # 6. Distribute master mix to the seven PCR wells.
    p20.transfer(19, pcr_mm, pcr_dest, new_tip='once')

    # 7. Forward primers (1 µM).
    p20.transfer(2.5, [primer_plate[w] for w in fwd_primer_wells],
                 pcr_dest, new_tip='always')

    # 8. Reverse primers (1 µM).
    p20.transfer(2.5, [primer_plate[w] for w in rev_primer_wells],
                 pcr_dest, new_tip='always')

    # 9. Linearized template plasmid (0.5 ng/µL), 1 µL per fragment.
    p20.transfer(1, [template_plate[w] for w in template_src],
                 pcr_dest, new_tip='always')

    # 10. Mix the PCR reactions.
    for w in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15, pcr_plate[w])
        p20.drop_tip()

    # 11. Manual: gradient PCR in the Bio-Rad C100 thermocycler.
    protocol.comment(
        'Seal pcr_plate (or move the PCR tubes) and transfer manually to the '
        'Bio-Rad C100 gradient thermocycler. Run: 98°C 30 s; 34 cycles of '
        '98°C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient '
        'temperature for each fragment, 72°C extension at the time set by '
        'AssemblyTron (about 20-30 s/kb); final extension 72°C 5 min; hold '
        '4°C. Take a sample of each reaction for gel electrophoresis, then '
        'return to the OT-2.')

    # 12-14. DpnI digestion master (water, rCutSmart, DpnI) into each well.
    p20.transfer(19, water, pcr_dest, new_tip='once')
    p20.transfer(5, rcutsmart, pcr_dest, new_tip='once')
    p20.transfer(1, dpni, pcr_dest, new_tip='once')

    # 15. Mix the DpnI reactions.
    for w in pcr_wells:
        p300.pick_up_tip()
        p300.mix(3, 30, pcr_plate[w])
        p300.drop_tip()

    # 16. Manual: DpnI digestion / inactivation.
    protocol.comment(
        'Incubate pcr_plate A1:G1 at 37°C for 30 min, then 65°C for 20 min '
        '(DpnI inactivation) on the thermocycler block.')

    # 17. Manual: clean and concentrate the fragments.
    protocol.comment(
        'Pause the protocol. Clean and concentrate each of the 7 fragments '
        'with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding '
        'Buffer to sample (250 µL per 50 µL), spin 30 s, wash 2 x 200 µL DNA '
        'Wash Buffer (30 s spins), elute in 20 µL water after 1 min at room '
        'temperature (30 s spin). Return the eluted fragments to their '
        'original positions pcr_plate A1:G1 (fragments 1-7) and resume the '
        'protocol.')

    # 18-19. Set up the Golden Gate reactions: water and ligase buffer.
    p20.transfer(7, water, assembly_dest, new_tip='once')
    p20.transfer(2, t4_buffer, assembly_dest, new_tip='once')

    # 20-22. Backbone fragments: fragment 2 (backbone), 5 (backbone/KanR), 6 (backbone).
    p20.transfer(3, pcr_plate['B1'], assembly_dest, new_tip='once')
    p20.transfer(2, pcr_plate['E1'], assembly_dest, new_tip='once')
    p20.transfer(3, pcr_plate['F1'], assembly_dest, new_tip='once')

    # 23. Chromoprotein fragments 1, 3, 4, 7 -> one per assembly.
    p20.transfer(2, [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']],
                 assembly_dest, new_tip='always')

    # 24. Golden Gate enzyme mix; mix 5 times after each dispense.
    for w in assembly_wells:
        p20.pick_up_tip()
        p20.aspirate(1, gg_enzyme)
        p20.dispense(1, assembly_plate[w])
        p20.mix(5, 20, assembly_plate[w])
        p20.drop_tip()

    # 25. Manual: Golden Gate thermocycling program.
    protocol.comment(
        'Run Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37°C 5 min then 16°C 5 min; then '
        '60°C 5 min; hold at 4°C. Lid about 85°C. If no module is available, '
        'pause and move reactions to another thermocycler.')

    # 26. Manual: clean and concentrate the assemblies.
    protocol.comment(
        'Clean and concentrate each assembly with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 µL wash) and '
        'elute in 10 µL molecular grade water; return the eluates to '
        'assembly_plate A1:D1.')

    # 27. Add purified assemblies to competent cells.
    p20.transfer(5, [assembly_plate[w] for w in assembly_wells],
                 cells_dest, new_tip='always')

    # 28. Manual: quantify the remaining eluate.
    protocol.comment(
        'Measure DNA concentration of the remaining 5 µL of each eluate with '
        'a NanoDrop-2000c for CFU/µg calculation.')

    # 29. Manual: heat shock.
    protocol.comment(
        'Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42°C '
        'for 60 s, then return to ice for about 2 min.')

    # 30. Add LB + 0.2% dextrose for recovery.
    p300.transfer(250, lb_dextrose, cells_dest, new_tip='once')

    # 31. Manual: recovery.
    protocol.comment(
        'Recover cells at 37°C for 60 min with shaking (about 250 rpm).')

    # 32. Manual: plating.
    protocol.comment(
        'Plate 50-200 µL of each recovery (neat or a 10x dilution, depending '
        'on predicted efficiency) onto separate LB agar plates containing '
        'kanamycin 50 µg/mL; incubate at 37°C overnight.')

    # 33. Manual: colony scoring.
    protocol.comment(
        'Manually count colonies per plate and score the fraction showing '
        'the expected chromoprotein colour (purple, orange, blue, green); '
        'report CFU/µg of DNA plated.')