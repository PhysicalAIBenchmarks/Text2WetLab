from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate assembly of four 4-fragment chromoprotein plasmids',
    'author': 'AssemblyTron-derived',
    'apiLevel': '2.15',
}


def run(protocol: protocol_api.ProtocolContext):
    tubes50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes15x = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    water = tubes50['A1']
    q5_buffer = tubes15x['A1']
    dntp = tubes15x['B1']
    q5_pol = tubes15x['C1']
    pcr_mm = tubes15x['D1']
    rcutsmart = tubes15x['A2']
    dpni = tubes15x['B2']
    t4_buffer = tubes15x['C2']
    gg_enzyme = tubes15x['D2']
    lb = tubes15['A1']

    def fresh_tips():
        p20.reset_tipracks()
        p300.reset_tipracks()

    def pip_for(vol):
        return p20 if vol <= 20 else p300

    def move(vol, src, dsts, **kw):
        pip = pip_for(vol)
        if not isinstance(src, list):
            src = [src] * len(dsts)
        pip.transfer(vol, src, dsts, new_tip='always', **kw)

    def mix_wells(cycles, vol, wells):
        pip = pip_for(vol)
        for w in wells:
            pip.pick_up_tip()
            pip.mix(cycles, vol, w)
            pip.drop_tip()

    pcr_wells = [pcr[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    asm_wells = [assembly[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cell_wells = [cells[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # 1-5 PCR master mix
    fresh_tips()
    p300.transfer(106, water, pcr_mm, new_tip='always')
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='always')
    p20.transfer(4, dntp, pcr_mm, new_tip='always')
    p20.transfer(2, q5_pol, pcr_mm, new_tip='always')
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # 6 master mix to PCR plate
    fresh_tips()
    move(19, pcr_mm, pcr_wells)

    # 7-8 primers
    fresh_tips()
    move(2.5, [primer[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']], pcr_wells)
    fresh_tips()
    move(2.5, [primer[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']], pcr_wells)

    # 9 templates
    fresh_tips()
    move(1, [template[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']], pcr_wells)

    # 10 mix
    fresh_tips()
    mix_wells(3, 15, pcr_wells)

    # 11 PCR
    protocol.comment(
        'MANUAL: Seal pcr_plate (or move the PCR tubes) and transfer to the Bio-Rad C100 gradient '
        'thermocycler. Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 '
        'optimal-gradient temperature for each fragment, 72C extension at the time set by AssemblyTron '
        '(about 20-30 s/kb); final extension 72C 5 min; hold 4C. Take a sample of each reaction for gel '
        'electrophoresis, then return to the OT-2.')

    # 12-14 DpnI digest setup
    fresh_tips()
    move(19, water, pcr_wells)
    fresh_tips()
    move(5, rcutsmart, pcr_wells)
    fresh_tips()
    move(1, dpni, pcr_wells)

    # 15 mix
    fresh_tips()
    mix_wells(3, 30, pcr_wells)

    # 16 DpnI incubation
    protocol.comment(
        'MANUAL: Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation) '
        'on the thermocycler block.')

    # 17 cleanup
    protocol.comment(
        'MANUAL (pause): Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & '
        'Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 uL per 50 uL), spin 30 s, wash '
        '2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature '
        '(30 s spin). Return the eluted fragments to their original positions pcr_plate A1:G1 '
        '(fragments 1-7) and resume the protocol.')

    # 18-24 Golden Gate setup
    fresh_tips()
    move(7, water, asm_wells)
    fresh_tips()
    move(2, t4_buffer, asm_wells)
    fresh_tips()
    move(3, pcr['B1'], asm_wells)
    fresh_tips()
    move(2, pcr['E1'], asm_wells)
    fresh_tips()
    move(3, pcr['F1'], asm_wells)
    fresh_tips()
    move(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], asm_wells)
    fresh_tips()
    move(1, gg_enzyme, asm_wells, mix_after=(5, 10))

    # 25 Golden Gate program
    protocol.comment(
        'MANUAL: Run Golden Gate program on assembly_plate in the Opentrons thermocycler module: '
        '30 cycles of 37C 5 min then 16C 5 min; then 60C 5 min; hold at 4C. Lid about 85C. If no '
        'module is available, pause and move reactions to another thermocycler.')

    # 26 cleanup
    protocol.comment(
        'MANUAL: Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column '
        '(5:1 binding buffer, 2 x 200 uL wash) and elute in 10 uL molecular grade water; return the '
        'eluates to assembly_plate A1:D1.')

    # 27 transformation
    fresh_tips()
    move(5, asm_wells, cell_wells)

    # 28-29
    protocol.comment(
        'MANUAL: Measure DNA concentration of the remaining 5 uL of each eluate with a NanoDrop-2000c '
        'for CFU/ug calculation.')
    protocol.comment(
        'MANUAL: Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42C for 60 s, then return '
        'to ice for about 2 min.')

    # 30 recovery medium
    fresh_tips()
    move(250, lb, cell_wells)

    # 31-33
    protocol.comment('MANUAL: Recover cells at 37C for 60 min with shaking (about 250 rpm).')
    protocol.comment(
        'MANUAL: Plate 50-200 uL of each recovery (neat or a 10x dilution, depending on predicted '
        'efficiency) onto separate LB agar plates containing kanamycin 50 ug/mL; incubate at 37C overnight.')
    protocol.comment(
        'MANUAL: Manually count colonies per plate and score the fraction showing the expected '
        'chromoprotein colour (purple, orange, blue, green); report CFU/ug of DNA plated.')
