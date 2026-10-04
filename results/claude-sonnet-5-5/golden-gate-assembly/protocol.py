from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate, 4 x 4-fragment chromoprotein plasmids',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    t50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    t15e = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    asm = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    t15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    water = t50['A1']
    q5buf, dntp, q5pol, mm = t15e['A1'], t15e['B1'], t15e['C1'], t15e['D1']
    rcut, dpni, t4buf, ggenz = t15e['A2'], t15e['B2'], t15e['C2'], t15e['D2']
    lb = t15['A1']

    def xfer(pip, vol, src, dsts, new_tip='always', mix_after=None):
        if not isinstance(dsts, list):
            dsts = [dsts]
        if not isinstance(src, list):
            src = [src] * len(dsts)
        if new_tip == 'once':
            pip.pick_up_tip()
        for s, d in zip(src, dsts):
            if new_tip == 'always':
                pip.pick_up_tip()
            pip.aspirate(vol, s)
            pip.dispense(vol, d)
            if mix_after:
                pip.mix(*mix_after, d)
            if new_tip == 'always':
                pip.drop_tip()
        if new_tip == 'once':
            pip.drop_tip()

    col1 = [pcr.wells_by_name()[w + '1'] for w in 'ABCDEFG']
    asm_w = [asm[w + '1'] for w in 'ABCD']
    cell_w = [cells[w + '1'] for w in 'ABCD']

    # PCR master mix (8 reactions)
    xfer(p300, 106, water, mm)
    xfer(p300, 40, q5buf, mm)
    xfer(p20, 4, dntp, mm)
    xfer(p20, 2, q5pol, mm)
    p300.pick_up_tip()
    p300.mix(5, 100, mm)
    p300.drop_tip()
    xfer(p20, 19, mm, col1, new_tip='once')

    xfer(p20, 2.5, [primer[w + '1'] for w in 'ABCDEFG'], col1)
    xfer(p20, 2.5, [primer[w + '2'] for w in 'ABCDEFG'], col1)
    tmpl = [template[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]
    xfer(p20, 1, tmpl, col1)
    for w in col1:
        p20.pick_up_tip()
        p20.mix(3, 15, w)
        p20.drop_tip()

    protocol.comment('Seal pcr_plate (or move the PCR tubes) and transfer manually to the Bio-Rad C100 gradient '
                     'thermocycler. Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 '
                     'optimal-gradient temperature for each fragment, 72C extension (about 20-30 s/kb); final '
                     'extension 72C 5 min; hold 4C. Take a sample of each reaction for gel electrophoresis, '
                     'then return to the OT-2.')

    # DpnI digestion
    xfer(p20, 19, water, col1, new_tip='once')
    xfer(p20, 5, rcut, col1)
    xfer(p20, 1, dpni, col1)
    for w in col1:
        p300.pick_up_tip()
        p300.mix(3, 30, w)
        p300.drop_tip()

    protocol.comment('Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation).')
    protocol.comment('Pause. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 '
                     'column: 5:1 DNA Binding Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA '
                     'Wash Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature (30 s spin). '
                     'Return the eluted fragments to pcr_plate A1:G1 (fragments 1-7) and resume.')

    # Golden Gate
    xfer(p20, 7, water, asm_w, new_tip='once')
    xfer(p20, 2, t4buf, asm_w)
    xfer(p20, 3, pcr['B1'], asm_w)
    xfer(p20, 2, pcr['E1'], asm_w)
    xfer(p20, 3, pcr['F1'], asm_w)
    xfer(p20, 2, [pcr['A1'], pcr['C1'], pcr['D1'], pcr['G1']], asm_w)
    xfer(p20, 1, ggenz, asm_w, mix_after=(5, 10))

    protocol.comment('Run Golden Gate program on assembly_plate in the thermocycler module: 30 cycles of 37C 5 min '
                     'then 16C 5 min; then 60C 5 min; hold at 4C. Lid about 85C.')
    protocol.comment('Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding '
                     'buffer, 2 x 200 uL wash) and elute in 10 uL molecular grade water; return the eluates to '
                     'assembly_plate A1:D1.')

    xfer(p20, 5, asm_w, cell_w)
    protocol.comment('Measure DNA concentration of the remaining 5 uL of each eluate with a NanoDrop-2000c for '
                     'CFU/ug calculation.')
    protocol.comment('Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42C for 60 s, then return to ice '
                     'for about 2 min.')
    xfer(p300, 250, lb, cell_w)
    protocol.comment('Recover cells at 37C for 60 min with shaking (about 250 rpm).')
    protocol.comment('Plate 50-200 uL of each recovery (neat or 10x dilution) onto LB agar + kanamycin 50 ug/mL; '
                     'incubate at 37C overnight.')
    protocol.comment('Manually count colonies per plate and score the fraction showing the expected chromoprotein '
                     'colour (purple, orange, blue, green); report CFU/ug of DNA plated.')
