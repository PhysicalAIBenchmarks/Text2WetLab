from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate, 4 chromoprotein plasmids',
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

    water = t50['A1']
    q5_buffer, dntp, q5_pol, mm = t15e['A1'], t15e['B1'], t15e['C1'], t15e['D1']
    rcut, dpni, t4buf, gg = t15e['A2'], t15e['B2'], t15e['C2'], t15e['D2']
    lb = t15['A1']

    def pip(v):
        return p20 if v <= 20 else p300

    def xfer(vol, src, dsts, mix=None):
        """One fresh tip per destination; mix = (reps, vol) after dispensing."""
        p = pip(vol)
        if not isinstance(dsts, list):
            dsts = [dsts]
        srcs = src if isinstance(src, list) else [src] * len(dsts)
        for s, d in zip(srcs, dsts):
            if len(p.tip_racks[0].wells()) and not p.has_tip:
                try:
                    p.pick_up_tip()
                except Exception:
                    p.reset_tipracks()
                    p.pick_up_tip()
            p.aspirate(vol, s)
            p.dispense(vol, d)
            if mix:
                p.mix(mix[0], mix[1], d)
            p.drop_tip()

    def mix_wells(wells, reps, vol):
        p = pip(vol)
        for w in wells:
            try:
                p.pick_up_tip()
            except Exception:
                p.reset_tipracks()
                p.pick_up_tip()
            p.mix(reps, vol, w)
            p.drop_tip()

    col = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pcrw = [pcr[w] for w in col]
    asmw = [asm[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cellw = [cells[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # 1-5 master mix
    xfer(106, water, mm)
    xfer(40, q5_buffer, mm)
    xfer(4, dntp, mm)
    xfer(2, q5_pol, mm)
    mix_wells([mm], 5, 100)
    # 6-10 PCR setup
    xfer(19, mm, pcrw)
    xfer(2.5, [primer[w] for w in col], pcrw)
    xfer(2.5, [primer[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']], pcrw)
    xfer(1, [templ[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']], pcrw)
    mix_wells(pcrw, 3, 15)
    protocol.comment('Seal pcr_plate (or move PCR tubes) and transfer manually to the Bio-Rad C100 gradient thermocycler. '
                     'Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient '
                     'temperature for each fragment, 72C extension (~20-30 s/kb); final extension 72C 5 min; hold 4C. '
                     'Take a sample of each reaction for gel electrophoresis, then return to the OT-2.')
    # 12-15 DpnI
    xfer(19, water, pcrw)
    xfer(5, rcut, pcrw)
    xfer(1, dpni, pcrw)
    mix_wells(pcrw, 3, 30)
    protocol.comment('Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation).')
    protocol.comment('Pause. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 column: '
                     '5:1 binding buffer (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL, elute in 20 uL water after 1 min '
                     '(30 s spin). Return fragments to pcr_plate A1:G1 and resume.')
    # 18-24 Golden Gate
    xfer(7, water, asmw)
    xfer(2, t4buf, asmw)
    xfer(3, pcr['B1'], asmw)
    xfer(2, pcr['E1'], asmw)
    xfer(3, pcr['F1'], asmw)
    for f in ['A1', 'C1', 'D1', 'G1']:
        pass
    xfer(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], asmw)
    xfer(1, gg, asmw, mix=(5, 10))
    protocol.comment('Run Golden Gate program on assembly_plate in the thermocycler module: 30 cycles of 37C 5 min then '
                     '16C 5 min; then 60C 5 min; hold 4C. Lid ~85C.')
    protocol.comment('Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, '
                     '2 x 200 uL wash), elute in 10 uL molecular grade water; return eluates to assembly_plate A1:D1.')
    # 27
    xfer(5, asmw, cellw)
    protocol.comment('Measure DNA concentration of remaining 5 uL of each eluate with a NanoDrop-2000c for CFU/ug.')
    protocol.comment('Incubate cells_plate A1:D1 30 min on ice, heat shock 42C for 60 s, return to ice ~2 min.')
    xfer(250, lb, cellw)
    protocol.comment('Recover cells at 37C for 60 min with shaking (~250 rpm).')
    protocol.comment('Plate 50-200 uL of each recovery (neat or 10x dilution) on LB agar + kanamycin 50 ug/mL; '
                     'incubate 37C overnight.')
    protocol.comment('Count colonies per plate, score fraction with expected chromoprotein colour; report CFU/ug DNA plated.')
