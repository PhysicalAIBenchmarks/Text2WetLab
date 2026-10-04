from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate, 4 x 4-fragment chromoprotein plasmids',
            'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    t50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    t15e = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    templ = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
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

    def move(vol, src, dsts, mix_after=0, new_tip=True):
        """src: single well or list (paired with dsts)."""
        p = pip(vol)
        if not isinstance(dsts, list):
            dsts = [dsts]
        srcs = src if isinstance(src, list) else [src] * len(dsts)
        for s, d in zip(srcs, dsts):
            try:
                p.pick_up_tip()
            except Exception:
                p.reset_tipracks()
                p.pick_up_tip()
            p.aspirate(vol, s)
            p.dispense(vol, d)
            if mix_after:
                p.mix(mix_after, min(vol, p.max_volume), d)
            p.drop_tip()

    def mix(well_list, cycles, vol):
        p = pip(vol)
        for w in well_list:
            try:
                p.pick_up_tip()
            except Exception:
                p.reset_tipracks()
                p.pick_up_tip()
            p.mix(cycles, vol, w)
            p.drop_tip()

    water = t50['A1']
    q5buf, dntp, q5pol, mm = t15e['A1'], t15e['B1'], t15e['C1'], t15e['D1']
    rcut, dpni, t4buf, ggenz = t15e['A2'], t15e['B2'], t15e['C2'], t15e['D2']
    lb = t15['A1']

    pcr_w = [pcr[f'{r}1'] for r in 'ABCDEFG']
    asm_w = [asm[f'{r}1'] for r in 'ABCD']
    cell_w = [cells[f'{r}1'] for r in 'ABCD']

    # PCR master mix
    move(106, water, mm)
    move(40, q5buf, mm)
    move(4, dntp, mm)
    move(2, q5pol, mm)
    mix([mm], 5, 100)
    move(19, mm, pcr_w)
    move(2.5, [primer[f'{r}1'] for r in 'ABCDEFG'], pcr_w)
    move(2.5, [primer[f'{r}2'] for r in 'ABCDEFG'], pcr_w)
    tsrc = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    move(1, [templ[w] for w in tsrc], pcr_w)
    mix(pcr_w, 3, 15)
    protocol.comment('Seal pcr_plate (or move PCR tubes) and transfer manually to the Bio-Rad C100 gradient thermocycler. '
                     'Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 optimal gradient '
                     'temperature for each fragment, 72C extension (~20-30 s/kb); final 72C 5 min; hold 4C. '
                     'Take a sample of each reaction for gel electrophoresis, then return to the OT-2.')

    # DpnI digestion
    move(19, water, pcr_w)
    move(5, rcut, pcr_w)
    move(1, dpni, pcr_w)
    mix(pcr_w, 3, 30)
    protocol.comment('Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation).')
    protocol.comment('Pause. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 column: '
                     '5:1 DNA Binding Buffer to sample, spin 30 s, wash 2 x 200 uL DNA Wash Buffer (30 s spins), '
                     'elute in 20 uL water after 1 min at RT (30 s spin). Return eluates to pcr_plate A1:G1 and resume.')

    # Golden Gate
    move(7, water, asm_w)
    move(2, t4buf, asm_w)
    move(3, pcr['B1'], asm_w)
    move(2, pcr['E1'], asm_w)
    move(3, pcr['F1'], asm_w)
    move(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], asm_w)
    move(1, ggenz, asm_w, mix_after=5)
    protocol.comment('Run Golden Gate program on assembly_plate in the Opentrons thermocycler module: 30 cycles of '
                     '37C 5 min then 16C 5 min; then 60C 5 min; hold 4C. Lid ~85C. If no module, pause and move '
                     'reactions to another thermocycler.')
    protocol.comment('Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding '
                     'buffer, 2 x 200 uL wash), elute in 10 uL molecular grade water; return eluates to assembly_plate A1:D1.')

    # Transformation
    move(5, asm_w, cell_w)
    protocol.comment('Measure DNA concentration of the remaining 5 uL of each eluate with a NanoDrop-2000c for CFU/ug.')
    protocol.comment('Incubate cells_plate A1:D1 30 min on ice, heat shock 42C for 60 s, return to ice ~2 min.')
    move(250, lb, cell_w)
    protocol.comment('Recover cells at 37C for 60 min with shaking (~250 rpm).')
    protocol.comment('Plate 50-200 uL of each recovery (neat or 10x dilution) onto LB agar + kanamycin 50 ug/mL; '
                     'incubate 37C overnight.')
    protocol.comment('Manually count colonies per plate, score fraction with expected chromoprotein colour '
                     '(purple, orange, blue, green); report CFU/ug DNA plated.')
