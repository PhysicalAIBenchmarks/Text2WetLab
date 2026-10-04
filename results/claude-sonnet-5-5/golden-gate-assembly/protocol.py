from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate of four 4-fragment chromoprotein plasmids',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    t50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    t15e = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primers = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    templates = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    asm = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    t15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    def pip(v):
        return p20 if v <= 20 else p300

    def xfer(vol, src, dests, new_tip_each=True, mix_after=None):
        """Transfer vol from src to each dest (list of wells)."""
        p = pip(vol)
        if not new_tip_each:
            p.pick_up_tip()
        for d in dests:
            if new_tip_each:
                p.pick_up_tip()
            p.aspirate(vol, src)
            p.dispense(vol, d)
            if mix_after:
                p.mix(*mix_after, d)
            if new_tip_each:
                p.drop_tip()
        if not new_tip_each:
            p.drop_tip()

    def pair(vol, srcs, dests):
        p = pip(vol)
        for s, d in zip(srcs, dests):
            p.pick_up_tip()
            p.aspirate(vol, s)
            p.dispense(vol, d)
            p.drop_tip()

    water = t50['A1']
    q5buf, dntp, q5pol, mm = t15e['A1'], t15e['B1'], t15e['C1'], t15e['D1']
    rcut, dpni, t4buf, ggenz = t15e['A2'], t15e['B2'], t15e['C2'], t15e['D2']
    lb = t15['A1']

    frag_rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    pcr_w = [pcr[r + '1'] for r in frag_rows]
    asm_w = [asm[r + '1'] for r in 'ABCD']
    cell_w = [cells[r + '1'] for r in 'ABCD']

    # 1-5 master mix
    xfer(106, water, [mm], new_tip_each=False)
    xfer(40, q5buf, [mm])
    xfer(4, dntp, [mm])
    xfer(2, q5pol, [mm])
    p300.pick_up_tip()
    p300.mix(5, 100, mm)
    p300.drop_tip()

    # 6 master mix
    xfer(19, mm, pcr_w, new_tip_each=False)
    # 7-8 primers
    pair(2.5, [primers[r + '1'] for r in frag_rows], pcr_w)
    pair(2.5, [primers[r + '2'] for r in frag_rows], pcr_w)
    # 9 templates
    pair(1, [templates[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']], pcr_w)
    # 10 mix
    for w in pcr_w:
        p20.pick_up_tip()
        p20.mix(3, 15, w)
        p20.drop_tip()

    protocol.comment('Seal pcr_plate and transfer manually to Bio-Rad C100 gradient thermocycler. '
                     'Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 '
                     'optimal gradient temperature per fragment, 72C extension (~20-30 s/kb); '
                     'final 72C 5 min; hold 4C. Sample each reaction for gel, then return to OT-2.')

    # 12-15 DpnI digestion
    xfer(19, water, pcr_w, new_tip_each=False)
    xfer(5, rcut, pcr_w, new_tip_each=False)
    xfer(1, dpni, pcr_w)
    for w in pcr_w:
        p300.pick_up_tip()
        p300.mix(3, 30, w)
        p300.drop_tip()

    protocol.comment('Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation).')
    protocol.comment('Pause: clean and concentrate each of the 7 fragments with a Zymo DNA Clean & '
                     'Concentrator-5 column: 5:1 binding buffer to sample (250 uL per 50 uL), spin 30 s, '
                     'wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL water after 1 min at '
                     'room temperature (30 s spin). Return fragments to pcr_plate A1:G1 and resume.')

    # 18-24 Golden Gate set-up
    xfer(7, water, asm_w, new_tip_each=False)
    xfer(2, t4buf, asm_w, new_tip_each=False)
    xfer(3, pcr['B1'], asm_w, new_tip_each=False)
    xfer(2, pcr['E1'], asm_w, new_tip_each=False)
    xfer(3, pcr['F1'], asm_w, new_tip_each=False)
    pair(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], asm_w)
    xfer(1, ggenz, asm_w, mix_after=(5, 10))

    protocol.comment('Run Golden Gate program on assembly_plate in thermocycler: 30 cycles of 37C 5 min '
                     'then 16C 5 min; then 60C 5 min; hold 4C. Lid ~85C.')
    protocol.comment('Clean and concentrate each assembly with Zymo DNA Clean & Concentrator-5 '
                     '(5:1 binding buffer, 2 x 200 uL wash), elute in 10 uL water; return eluates to '
                     'assembly_plate A1:D1.')

    # 27 transformation
    pair(5, asm_w, cell_w)
    protocol.comment('Measure DNA concentration of remaining 5 uL of each eluate with NanoDrop-2000c.')
    protocol.comment('Incubate cells_plate A1:D1 30 min on ice, heat shock 42C 60 s, ice ~2 min.')
    xfer(250, lb, cell_w)
    protocol.comment('Recover cells at 37C for 60 min with shaking (~250 rpm).')
    protocol.comment('Plate 50-200 uL of each recovery (neat or 10x dilution) onto LB agar + kanamycin '
                     '50 ug/mL; incubate 37C overnight.')
    protocol.comment('Count colonies per plate, score fraction with expected chromoprotein colour '
                     '(purple, orange, blue, green); report CFU/ug DNA plated.')
