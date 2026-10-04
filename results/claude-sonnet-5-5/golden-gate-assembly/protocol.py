from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate, 4 x 4-fragment chromoprotein plasmids', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    w50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    t15 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    templ = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    asm = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    f15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    def pip(v):
        return p20 if v <= 20 else p300

    def xfer(v, src, dests, tip='always', **kw):
        p = pip(v)
        p.reset_tipracks()
        if not isinstance(src, list):
            src = [src] * len(dests)
        for s, d in zip(src, dests):
            p.transfer(v, s, d, new_tip=tip, **kw)

    water = w50['A1']
    D1 = t15['D1']
    cols = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pc = [pcr[c] for c in cols]
    ac = [asm[c] for c in ['A1', 'B1', 'C1', 'D1']]

    # master mix
    xfer(106, water, [D1])
    xfer(40, t15['A1'], [D1])
    xfer(4, t15['B1'], [D1])
    xfer(2, t15['C1'], [D1])
    p300.reset_tipracks()
    p300.pick_up_tip()
    p300.mix(5, 100, D1)
    p300.drop_tip()
    xfer(19, D1, pc, tip='once')
    xfer(2.5, [primer[c] for c in cols], pc)
    xfer(2.5, [primer[c[0] + '2'] for c in cols], pc)
    tm = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    xfer(1, [templ[c] for c in tm], pc)
    p20.reset_tipracks()
    for w in pc:
        p20.pick_up_tip()
        p20.mix(3, 15, w)
        p20.drop_tip()
    protocol.comment('Seal pcr_plate and move to Bio-Rad C100 gradient thermocycler. 98C 30 s; 34 x (98C 10 s, '
                     'annealing 30 s at AssemblyTron/j5 optimal gradient temperature per fragment, 72C at ~20-30 s/kb); '
                     '72C 5 min; hold 4C. Sample for gel, then return to OT-2.')
    # DpnI
    xfer(19, water, pc, tip='once')
    xfer(5, t15['A2'], pc, tip='once')
    xfer(1, t15['B2'], pc)
    p300.reset_tipracks()
    for w in pc:
        p300.pick_up_tip()
        p300.mix(3, 30, w)
        p300.drop_tip()
    protocol.comment('Incubate pcr_plate A1:G1 at 37C 30 min, then 65C 20 min (DpnI inactivation).')
    protocol.comment('Pause: Zymo DNA Clean & Concentrator-5 on each of 7 fragments (5:1 binding buffer, spin 30 s, '
                     '2 x 200 uL wash, elute 20 uL water after 1 min). Return to pcr_plate A1:G1 and resume.')
    # Golden Gate
    xfer(7, water, ac, tip='once')
    xfer(2, t15['C2'], ac, tip='once')
    xfer(3, pcr['B1'], ac)
    xfer(2, pcr['E1'], ac)
    xfer(3, pcr['F1'], ac)
    xfer(2, [pcr['A1'], pcr['C1'], pcr['D1'], pcr['G1']], ac)
    xfer(1, t15['D2'], ac, mix_after=(5, 10))
    protocol.comment('Golden Gate on thermocycler: 30 x (37C 5 min, 16C 5 min); 60C 5 min; hold 4C; lid ~85C.')
    protocol.comment('Zymo clean-up of each assembly (5:1 binding buffer, 2 x 200 uL wash), elute in 10 uL water; '
                     'return eluates to assembly_plate A1:D1.')
    xfer(5, ac, [cells[c] for c in ['A1', 'B1', 'C1', 'D1']])
    protocol.comment('Measure DNA concentration of remaining 5 uL of each eluate by NanoDrop-2000c.')
    protocol.comment('Incubate cells_plate A1:D1 30 min on ice, heat shock 42C 60 s, ice ~2 min.')
    xfer(250, f15['A1'], [cells[c] for c in ['A1', 'B1', 'C1', 'D1']])
    protocol.comment('Recover cells 37C 60 min, ~250 rpm.')
    protocol.comment('Plate 50-200 uL of each recovery on LB agar + kanamycin 50 ug/mL; incubate 37C overnight.')
    protocol.comment('Count colonies, score expected chromoprotein colour (purple, orange, blue, green); report CFU/ug.')
