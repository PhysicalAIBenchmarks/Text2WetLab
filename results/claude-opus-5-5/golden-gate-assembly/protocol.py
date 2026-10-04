"""AssemblyTron-style Golden Gate assembly of four four-fragment chromoprotein
expression plasmids on the Opentrons OT-2.

Seven fragments are amplified by PCR from linearized pIDMv5K chromoprotein
templates, residual template is removed with DpnI, the fragments are cleaned and
concentrated, combined in volumes proportional to fragment length with
BsaI-HFv2 + T4 DNA ligase, and the purified assemblies are transformed into
chemically competent E. coli TOP10 cells.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Golden Gate assembly of four chromoprotein plasmids (AssemblyTron)',
    'author': 'AssemblyTron',
    'description': ('PCR of 7 fragments, DpnI digestion, Golden Gate assembly of four '
                    'four-fragment chromoprotein plasmids, and transformation into E. coli TOP10.'),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ---------------------------------------------------------------- labware
    tubes_50ml_1 = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
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

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # ---------------------------------------------------------------- reagents
    water = tubes_50ml_1.wells_by_name()['A1']
    q5_buffer = tubes_1_5ml_1.wells_by_name()['A1']
    dntp = tubes_1_5ml_1.wells_by_name()['B1']
    q5_pol = tubes_1_5ml_1.wells_by_name()['C1']
    pcr_mm = tubes_1_5ml_1.wells_by_name()['D1']
    rcutsmart = tubes_1_5ml_1.wells_by_name()['A2']
    dpni = tubes_1_5ml_1.wells_by_name()['B2']
    t4_buffer = tubes_1_5ml_1.wells_by_name()['C2']
    gg_enzyme = tubes_1_5ml_1.wells_by_name()['D2']
    lb_dextrose = tubes_15ml_1.wells_by_name()['A1']

    frag_wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']   # fragments 1-7
    fragments = [pcr_plate.wells_by_name()[w] for w in frag_wells]
    fwd_primers = [primer_plate.wells_by_name()[w] for w in frag_wells]
    rev_primers = [primer_plate.wells_by_name()[w] for w in
                   ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    # fragment -> template: 1,2,5,6 from tsPurple (A1); 3 YukonOFP; 4 aeBlue; 7 fuGFP
    templates = [template_plate.wells_by_name()[w] for w in
                 ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]
    assemblies = [assembly_plate.wells_by_name()[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cells = [cells_plate.wells_by_name()[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # ------------------------------------------------------- tip bookkeeping
    # Tips are unlimited: recycle a rack once all 96 tips of it have been used.
    tips_used = {'left': 0, 'right': 0}

    def pick_up(pipette):
        if tips_used[pipette.mount] >= 96:
            pipette.reset_tipracks()
            tips_used[pipette.mount] = 0
        tips_used[pipette.mount] += 1
        pipette.pick_up_tip()

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    def xfer(volume, source, dest, mix_reps=0, mix_volume=None):
        """One transfer with a fresh tip, discarded afterwards."""
        pipette = pipette_for(volume)
        pick_up(pipette)
        pipette.aspirate(volume, source)
        pipette.dispense(volume, dest)
        if mix_reps:
            pipette.mix(mix_reps, mix_volume, dest)
        pipette.blow_out(dest.top())
        pipette.drop_tip()

    def mix_well(well, reps, volume):
        pipette = pipette_for(volume)
        pick_up(pipette)
        pipette.mix(reps, volume, well)
        pipette.blow_out(well.top())
        pipette.drop_tip()

    # =====================================================================
    # PCR master mix for 8 reactions (steps 1-5)
    # =====================================================================
    protocol.comment('Step 1-4: building PCR master mix in tubes_1_5ml_1 D1.')
    xfer(106, water, pcr_mm)        # nuclease-free water
    xfer(40, q5_buffer, pcr_mm)     # 5X Q5 reaction buffer
    xfer(4, dntp, pcr_mm)           # 10 mM dNTPs
    xfer(2, q5_pol, pcr_mm)         # Q5 High-Fidelity DNA Polymerase

    protocol.comment('Step 5: mixing PCR master mix, 5 cycles at 100 uL.')
    mix_well(pcr_mm, 5, 100)

    # =====================================================================
    # PCR set-up, 25 uL per fragment (steps 6-10)
    # =====================================================================
    protocol.comment('Step 6: 19 uL PCR master mix to pcr_plate A1:G1.')
    for frag in fragments:
        xfer(19, pcr_mm, frag)

    protocol.comment('Step 7: 2.5 uL forward primer (1 uM) to each PCR.')
    for primer, frag in zip(fwd_primers, fragments):
        xfer(2.5, primer, frag)

    protocol.comment('Step 8: 2.5 uL reverse primer (1 uM) to each PCR.')
    for primer, frag in zip(rev_primers, fragments):
        xfer(2.5, primer, frag)

    protocol.comment('Step 9: 1 uL linearized template (0.5 ng/uL) to each PCR.')
    for template, frag in zip(templates, fragments):
        xfer(1, template, frag)

    protocol.comment('Step 10: mixing PCRs, 3 cycles at 15 uL.')
    for frag in fragments:
        mix_well(frag, 3, 15)

    # ------------------------------------------------- off-deck thermocycling
    protocol.comment(
        'Step 11 (manual): seal pcr_plate (or move the PCR tubes) and transfer to the '
        'Bio-Rad C100 gradient thermocycler. Run 98 C 30 s; 34 cycles of 98 C 10 s, '
        'annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature for each '
        'fragment, 72 C extension at the time set by AssemblyTron (about 20-30 s/kb); '
        'final extension 72 C 5 min; hold 4 C. Take a sample of each reaction for gel '
        'electrophoresis, then return the plate to the OT-2.')

    # =====================================================================
    # DpnI digestion of residual template, 50 uL (steps 12-16)
    # =====================================================================
    protocol.comment('Step 12: 19 uL nuclease-free water to pcr_plate A1:G1.')
    for frag in fragments:
        xfer(19, water, frag)

    protocol.comment('Step 13: 5 uL rCutSmart Buffer to pcr_plate A1:G1.')
    for frag in fragments:
        xfer(5, rcutsmart, frag)

    protocol.comment('Step 14: 1 uL DpnI to pcr_plate A1:G1.')
    for frag in fragments:
        xfer(1, dpni, frag)

    protocol.comment('Step 15: mixing DpnI digests, 3 cycles at 30 uL.')
    for frag in fragments:
        mix_well(frag, 3, 30)

    protocol.comment(
        'Step 16 (manual): incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for '
        '20 min to inactivate DpnI, on the thermocycler block.')

    protocol.pause(
        'Step 17: clean and concentrate each of the 7 fragments with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 DNA Binding Buffer to sample, i.e. 250 uL per 50 uL; '
        'spin 30 s; wash 2 x 200 uL DNA Wash Buffer with 30 s spins; elute in 20 uL water '
        'after 1 min at room temperature, 30 s spin). Return the eluted fragments 1-7 to '
        'pcr_plate A1:G1 and resume.')
    protocol.comment(
        'Step 17 (manual): purified fragments 1-7 returned to pcr_plate A1:G1 in 20 uL water.')

    # =====================================================================
    # Golden Gate assemblies, 20 uL each (steps 18-24)
    # Fragment volumes are proportional to fragment length.
    # =====================================================================
    protocol.comment('Step 18: 7 uL nuclease-free water to assembly_plate A1:D1.')
    for well in assemblies:
        xfer(7, water, well)

    protocol.comment('Step 19: 2 uL 10X T4 DNA Ligase Buffer to assembly_plate A1:D1.')
    for well in assemblies:
        xfer(2, t4_buffer, well)

    protocol.comment('Step 20: 3 uL fragment 2 (backbone) from pcr_plate B1 to each assembly.')
    for well in assemblies:
        xfer(3, pcr_plate.wells_by_name()['B1'], well)

    protocol.comment('Step 21: 2 uL fragment 5 (backbone/KanR) from pcr_plate E1 to each assembly.')
    for well in assemblies:
        xfer(2, pcr_plate.wells_by_name()['E1'], well)

    protocol.comment('Step 22: 3 uL fragment 6 (backbone) from pcr_plate F1 to each assembly.')
    for well in assemblies:
        xfer(3, pcr_plate.wells_by_name()['F1'], well)

    protocol.comment('Step 23: 2 uL chromoprotein fragments 1, 3, 4, 7 to assemblies A1:D1.')
    chromo_sources = [pcr_plate.wells_by_name()[w] for w in ['A1', 'C1', 'D1', 'G1']]
    for source, well in zip(chromo_sources, assemblies):
        xfer(2, source, well)

    protocol.comment('Step 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase), mix 5 times.')
    for well in assemblies:
        xfer(1, gg_enzyme, well, mix_reps=5, mix_volume=10)

    protocol.comment(
        'Step 25 (manual): run the Golden Gate program on assembly_plate in the Opentrons '
        'thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; then 60 C 5 min; '
        'hold at 4 C; lid about 85 C. If no module is available, pause and move the '
        'reactions to another thermocycler.')

    protocol.comment(
        'Step 26 (manual): clean and concentrate each assembly with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in 10 uL '
        'molecular grade water; return the eluates to assembly_plate A1:D1.')

    # =====================================================================
    # Transformation of E. coli TOP10 (steps 27-30)
    # =====================================================================
    protocol.comment('Step 27: 5 uL purified assembly to competent cells in cells_plate A1:D1.')
    for well, cell in zip(assemblies, cells):
        xfer(5, well, cell)

    protocol.comment(
        'Step 28 (manual): measure the DNA concentration of the remaining 5 uL of each '
        'eluate on a NanoDrop-2000c for the CFU/ug calculation.')

    protocol.comment(
        'Step 29 (manual): incubate cells_plate A1:D1 for 30 min on ice, heat shock at '
        '42 C for 60 s, then return to ice for about 2 min.')

    protocol.comment('Step 30: 250 uL LB + 0.2% (w/v) dextrose to cells_plate A1:D1.')
    for cell in cells:
        xfer(250, lb_dextrose, cell)

    protocol.comment(
        'Step 31 (manual): recover the cells at 37 C for 60 min with shaking (about 250 rpm).')

    protocol.comment(
        'Step 32 (manual): plate 50-200 uL of each recovery (neat or a 10x dilution, '
        'depending on predicted efficiency) onto separate LB agar plates containing '
        'kanamycin 50 ug/mL; incubate at 37 C overnight.')

    protocol.comment(
        'Step 33 (manual): count colonies per plate and score the fraction showing the '
        'expected chromoprotein colour (purple, orange, blue, green); report CFU/ug of '
        'DNA plated.')
