from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate chromoprotein assembly', 'apiLevel': '2.15'}


def run(protocol: protocol_api.ProtocolContext):
    t50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    t15 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    templ = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    asm = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    t15ml = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    def pip(v):
        return p20 if v <= 20 else p300

    def xfer(v, src, dst, **kw):
        p = pip(v)
        if p.tip_racks[0].next_tip() is None if False else False:
            pass
        try:
            p.transfer(v, src, dst, new_tip='always', **kw)
        except Exception:
            p.reset_tipracks()
            p.transfer(v, src, dst, new_tip='always', **kw)

    def mix(wells, reps, v):
        p = pip(v)
        for w in wells:
            p.pick_up_tip()
            p.mix(reps, v, w)
            p.drop_tip()

    water = t50['A1']
    mm = t15['D1']
    col = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pc = [pcr[w] for w in col]
    ac = [asm[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cc = [cells[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # master mix
    p300.transfer(106, water, mm, new_tip='always')
    p300.transfer(40, t15['A1'], mm, new_tip='always')
    p20.transfer(4, t15['B1'], mm, new_tip='always')
    p20.transfer(2, t15['C1'], mm, new_tip='always')
    mix([mm], 5, 100)
    p20.transfer(19, mm, pc, new_tip='always')
    p20.transfer(2.5, [primer[w] for w in col], pc, new_tip='always')
    rev = ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']
    p20.transfer(2.5, [primer[w] for w in rev], pc, new_tip='always')
    tw = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    p20.transfer(1, [templ[w] for w in tw], pc, new_tip='always')
    mix(pc, 3, 15)
    protocol.comment('Seal pcr_plate and run gradient PCR manually on Bio-Rad C100: 98C 30 s; 34x (98C 10 s, annealing 30 s at j5 gradient temp, 72C ~20-30 s/kb); 72C 5 min; 4C hold. Take gel samples, return to OT-2.')
    p20.transfer(19, water, pc, new_tip='always')
    p20.transfer(5, t15['A2'], pc, new_tip='always')
    p20.transfer(1, t15['B2'], pc, new_tip='always')
    mix(pc, 3, 30)
    protocol.comment('Incubate pcr_plate at 37C 30 min then 65C 20 min.')
    protocol.comment('PAUSE: Zymo DNA Clean & Concentrator-5 cleanup of 7 fragments (5:1 binding buffer, 2x200 uL wash, elute 20 uL); return to pcr_plate A1:G1.')

    p20.transfer(7, water, ac, new_tip='once')
    p20.transfer(2, t15['C2'], ac, new_tip='once')
    p20.transfer(3, pcr['B1'], ac, new_tip='always')
    p20.transfer(2, pcr['E1'], ac, new_tip='always')
    p20.transfer(3, pcr['F1'], ac, new_tip='always')
    p20.transfer(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], ac, new_tip='always')
    p20.transfer(1, t15['D2'], ac, new_tip='always', mix_after=(5, 10))
    protocol.comment('Golden Gate on thermocycler: 30x (37C 5 min, 16C 5 min); 60C 5 min; 4C hold; lid 85C.')
    protocol.comment('Zymo cleanup of each assembly (5:1 binding buffer, 2x200 uL wash), elute in 10 uL water; return to assembly_plate A1:D1.')
    p20.transfer(5, ac, cc, new_tip='always')
    protocol.comment('NanoDrop remaining 5 uL of each eluate.')
    protocol.comment('Ice 30 min, heat shock 42C 60 s, ice ~2 min.')
    p300.transfer(250, t15ml['A1'], cc, new_tip='always')
    protocol.comment('Recover 37C 60 min shaking at ~250 rpm.')
    protocol.comment('Plate 50-200 uL on LB agar + kanamycin 50 ug/mL; 37C overnight.')
    protocol.comment('Count colonies, score chromoprotein colour, report CFU/ug.')
