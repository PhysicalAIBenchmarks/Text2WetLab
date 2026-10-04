from opentrons import protocol_api

metadata = {'protocolName': 'AssemblyTron Golden Gate of 4 chromoprotein plasmids', 'apiLevel': '2.13'}


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

    def xfer(v, srcs, dsts, mix_after=None):
        if not isinstance(srcs, list):
            srcs = [srcs] * len(dsts)
        p = pip(v)
        for s, d in zip(srcs, dsts):
            if p.hw_pipette['has_tip'] if False else False:
                pass
            if len(p.tip_racks[0].wells()) and not any(
                    w.has_tip for w in p.tip_racks[0].wells()):
                p.reset_tipracks()
            p.pick_up_tip()
            p.aspirate(v, s)
            p.dispense(v, d)
            if mix_after:
                p.mix(mix_after[0], mix_after[1], d)
            p.drop_tip()

    def mix(p, n, v, wells):
        for w in wells:
            p.pick_up_tip()
            p.mix(n, v, w)
            p.drop_tip()

    water = t50['A1']
    mm = t15e['D1']
    cols = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    pc = [pcr[w] for w in cols]
    a4 = [asm[w] for w in ['A1', 'B1', 'C1', 'D1']]

    xfer(106, water, [mm])
    xfer(40, t15e['A1'], [mm])
    xfer(4, t15e['B1'], [mm])
    xfer(2, t15e['C1'], [mm])
    mix(p300, 5, 100, [mm])
    xfer(19, mm, pc)
    xfer(2.5, [primer[w] for w in cols], pc)
    xfer(2.5, [primer[w.replace('1', '2')] for w in cols], pc)
    tw = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    xfer(1, [templ[w] for w in tw], pc)
    mix(p20, 3, 15, pc)
    protocol.comment('Seal pcr_plate (or move the PCR tubes) and transfer manually to the Bio-Rad C100 gradient thermocycler. Run: 98C 30 s; 34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature for each fragment, 72C extension at the time set by AssemblyTron (about 20-30 s/kb); final extension 72C 5 min; hold 4C. Take a sample of each reaction for gel electrophoresis, then return to the OT-2.')
    xfer(19, water, pc)
    xfer(5, t15e['A2'], pc)
    xfer(1, t15e['B2'], pc)
    mix(p300, 3, 30, pc)
    protocol.comment('Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C for 20 min (DpnI inactivation) on the thermocycler block.')
    protocol.comment('Pause: clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL water after 1 min at room temperature (30 s spin). Return the eluted fragments to pcr_plate A1:G1 (fragments 1-7) and resume.')
    xfer(7, water, a4)
    xfer(2, t15e['C2'], a4)
    xfer(3, pcr['B1'], a4)
    xfer(2, pcr['E1'], a4)
    xfer(3, pcr['F1'], a4)
    xfer(2, [pcr[w] for w in ['A1', 'C1', 'D1', 'G1']], a4)
    xfer(1, t15e['D2'], a4, mix_after=(5, 10))
    protocol.comment('Run Golden Gate program on assembly_plate in the Opentrons thermocycler module: 30 cycles of 37C 5 min then 16C 5 min; then 60C 5 min; hold at 4C. Lid about 85C. If no module is available, pause and move reactions to another thermocycler.')
    protocol.comment('Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in 10 uL molecular grade water; return the eluates to assembly_plate A1:D1.')
    xfer(5, a4, [cells[w] for w in ['A1', 'B1', 'C1', 'D1']])
    protocol.comment('Measure DNA concentration of the remaining 5 uL of each eluate with a NanoDrop-2000c for CFU/ug calculation.')
    protocol.comment('Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42C for 60 s, then return to ice for about 2 min.')
    xfer(250, t15['A1'], [cells[w] for w in ['A1', 'B1', 'C1', 'D1']])
    protocol.comment('Recover cells at 37C for 60 min with shaking (about 250 rpm).')
    protocol.comment('Plate 50-200 uL of each recovery (neat or a 10x dilution) onto separate LB agar plates containing kanamycin 50 ug/mL; incubate at 37C overnight.')
    protocol.comment('Manually count colonies per plate and score the fraction showing the expected chromoprotein colour (purple, orange, blue, green); report CFU/ug of DNA plated.')
