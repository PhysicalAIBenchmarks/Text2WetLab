"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow on the OT-2 (Synth. Biol. 2022, doi:10.1093/synbio/ysac032):
  * build a PCR master mix for 8 reactions
  * set up 7 fragment PCRs (j5-designed primers, 0.1 uM final, 0.5 ng linearized template)
  * DpnI digest residual methylated template
  * clean/concentrate the fragments (manual Zymo DCC-5 step)
  * combine the fragments in volumes proportional to fragment length with
    BsaI-HFv2 + T4 DNA ligase (Golden Gate Enzyme Mix)
  * clean up the assemblies and transform chemically competent E. coli TOP10
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 four-fragment chromoprotein plasmids',
    'author': 'AssemblyTron automation',
    'description': ('PCR setup, DpnI digestion, Golden Gate assembly and '
                    'transformation of four chromoprotein expression plasmids'),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------ labware
    tubes_50ml_1 = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware(
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
    tubes_15ml_1 = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left',
                                   tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tiprack_300])

    # ------------------------------------------------------------------ reagents
    water = tubes_50ml_1['A1']

    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']

    lb_dextrose = tubes_15ml_1['A1']

    # fragments 1-7 live in column 1 of the PCR plate
    frag_wells = [pcr_plate[w] for w in
                  ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    fwd_primers = [primer_plate[w] for w in
                   ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    rev_primers = [primer_plate[w] for w in
                   ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    # fragment -> template: 1,2,5,6 come off tsPurple (A1); the three other
    # chromoproteins supply fragments 3, 4 and 7
    templates = [template_plate[w] for w in
                 ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]

    assembly_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cell_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]

    def pick(volume):
        """20 uL pipette for 1-20 uL, 300 uL pipette above that."""
        return p20 if volume <= 20 else p300

    # ============================================================ 1. PCR master mix
    protocol.comment('Building PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')

    # step 1 - water (106 uL, split over two 53 uL aspirations)
    p300.pick_up_tip()
    for _ in range(2):
        p300.aspirate(53, water)
        p300.dispense(53, pcr_mm)
    p300.blow_out(pcr_mm.top())
    p300.drop_tip()

    # step 2 - 5X Q5 reaction buffer
    p300.pick_up_tip()
    p300.aspirate(40, q5_buffer)
    p300.dispense(40, pcr_mm)
    p300.blow_out(pcr_mm.top())
    p300.drop_tip()

    # step 3 - 10 mM dNTPs
    p20.pick_up_tip()
    p20.aspirate(4, dntp)
    p20.dispense(4, pcr_mm)
    p20.blow_out(pcr_mm.top())
    p20.drop_tip()

    # step 4 - Q5 High-Fidelity DNA Polymerase
    p20.pick_up_tip()
    p20.aspirate(2, q5_pol)
    p20.dispense(2, pcr_mm)
    p20.blow_out(pcr_mm.top())
    p20.drop_tip()

    # step 5 - mix the master mix, 5 cycles at 100 uL
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.blow_out(pcr_mm.top())
    p300.drop_tip()

    # ============================================================ 2. PCR setup
    # step 6 - 19 uL master mix into each fragment well
    p20.pick_up_tip()
    for well in frag_wells:
        p20.aspirate(19, pcr_mm)
        p20.dispense(19, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 7 - 2.5 uL forward primer (1 uM -> 0.1 uM final in 25 uL)
    for src, dest in zip(fwd_primers, frag_wells):
        p20.pick_up_tip()
        p20.aspirate(2.5, src)
        p20.dispense(2.5, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # step 8 - 2.5 uL reverse primer
    for src, dest in zip(rev_primers, frag_wells):
        p20.pick_up_tip()
        p20.aspirate(2.5, src)
        p20.dispense(2.5, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # step 9 - 1 uL linearized template (0.5 ng/uL -> 0.5 ng per reaction)
    for src, dest in zip(templates, frag_wells):
        p20.pick_up_tip()
        p20.aspirate(1, src)
        p20.dispense(1, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # step 10 - mix each 25 uL reaction, 3 cycles at 15 uL
    for well in frag_wells:
        p20.pick_up_tip()
        p20.mix(3, 15, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    p20.reset_tipracks()
    p300.reset_tipracks()

    # step 11 - off-deck gradient PCR
    protocol.comment(
        'MANUAL STEP (not simulated): seal pcr_plate (or move the PCR tubes) and '
        'transfer to the Bio-Rad C1000 gradient thermocycler. Run 98 C 30 s; '
        '34 cycles of 98 C 10 s, annealing 30 s at the AssemblyTron/j5 '
        'optimal-gradient temperature for each fragment, 72 C extension at the '
        'time set by AssemblyTron (about 20-30 s/kb); final extension 72 C 5 min; '
        'hold 4 C. Take a sample of each reaction for gel electrophoresis, then '
        'return pcr_plate to slot 5 on the OT-2.')
    protocol.pause('Run gradient PCR off-deck, then return pcr_plate to slot 5.')

    # ============================================================ 3. DpnI digestion
    protocol.comment('DpnI digestion of residual methylated plasmid template '
                     '(25 uL PCR + 19 uL water + 5 uL rCutSmart + 1 uL DpnI = 50 uL).')

    # step 12 - 19 uL water into each PCR
    p20.pick_up_tip()
    for well in frag_wells:
        p20.aspirate(19, water)
        p20.dispense(19, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 13 - 5 uL rCutSmart Buffer
    for well in frag_wells:
        p20.pick_up_tip()
        p20.aspirate(5, rcutsmart)
        p20.dispense(5, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    # step 14 - 1 uL DpnI
    for well in frag_wells:
        p20.pick_up_tip()
        p20.aspirate(1, dpni)
        p20.dispense(1, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    # step 15 - mix each 50 uL digest, 3 cycles at 30 uL
    for well in frag_wells:
        p300.pick_up_tip()
        p300.mix(3, 30, well)
        p300.blow_out(well.top())
        p300.drop_tip()

    p20.reset_tipracks()
    p300.reset_tipracks()

    # step 16 - digestion incubation
    protocol.comment(
        'MANUAL STEP (not simulated): incubate pcr_plate A1:G1 at 37 C for 30 min, '
        'then 65 C for 20 min to inactivate DpnI, on the thermocycler block.')

    # step 17 - column clean-up of the fragments
    protocol.comment(
        'MANUAL STEP (not simulated): clean and concentrate each of the 7 fragments '
        'with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA Binding Buffer to '
        'sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL DNA Wash Buffer '
        '(30 s spins), elute in 20 uL water after 1 min at room temperature (30 s '
        'spin). Return the eluted fragments to their original positions '
        'pcr_plate A1:G1 (fragments 1-7) and resume.')
    protocol.pause('Clean and concentrate fragments 1-7; return 20 uL eluates to '
                   'pcr_plate A1:G1, then resume.')

    # ============================================================ 4. Golden Gate
    protocol.comment(
        'Golden Gate assembly: four four-fragment reactions in assembly_plate A1:D1. '
        'Fragment volumes are proportional to fragment length (backbone pieces 2, 5 '
        'and 6 shared by all four assemblies; chromoprotein insert differs per well).')

    # step 18 - 7 uL water per reaction
    p20.pick_up_tip()
    for well in assembly_wells:
        p20.aspirate(7, water)
        p20.dispense(7, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 19 - 2 uL 10X T4 DNA Ligase Buffer
    for well in assembly_wells:
        p20.pick_up_tip()
        p20.aspirate(2, t4_buffer)
        p20.dispense(2, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    # step 20 - 3 uL fragment 2 (backbone) into all four reactions
    p20.pick_up_tip()
    for well in assembly_wells:
        p20.aspirate(3, frag_wells[1])
        p20.dispense(3, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 21 - 2 uL fragment 5 (backbone/KanR)
    p20.pick_up_tip()
    for well in assembly_wells:
        p20.aspirate(2, frag_wells[4])
        p20.dispense(2, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 22 - 3 uL fragment 6 (backbone)
    p20.pick_up_tip()
    for well in assembly_wells:
        p20.aspirate(3, frag_wells[5])
        p20.dispense(3, well)
        p20.blow_out(well.top())
    p20.drop_tip()

    # step 23 - 2 uL of chromoprotein fragments 1, 3, 4, 7 (one per reaction)
    for src, dest in zip([frag_wells[0], frag_wells[2], frag_wells[3],
                          frag_wells[6]], assembly_wells):
        p20.pick_up_tip()
        p20.aspirate(2, src)
        p20.dispense(2, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # step 24 - 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase), then mix
    for well in assembly_wells:
        p20.pick_up_tip()
        p20.aspirate(1, gg_enzyme)
        p20.dispense(1, well)
        p20.mix(5, 15, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    p20.reset_tipracks()
    p300.reset_tipracks()

    # step 25 - thermocycler assembly program
    protocol.comment(
        'MANUAL/MODULE STEP (not simulated): run the Golden Gate program on '
        'assembly_plate in the Opentrons thermocycler module: 30 cycles of 37 C '
        '5 min then 16 C 5 min; then 60 C 5 min; hold at 4 C. Lid about 85 C. '
        'If no module is available, pause and move the reactions to another '
        'thermocycler.')

    # step 26 - clean up the assemblies
    protocol.comment(
        'MANUAL STEP (not simulated): clean and concentrate each assembly with a '
        'Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 uL '
        'wash) and elute in 10 uL molecular grade water; return the eluates to '
        'assembly_plate A1:D1.')
    protocol.pause('Clean up the four assemblies; return 10 uL eluates to '
                   'assembly_plate A1:D1, then resume.')

    # ============================================================ 5. Transformation
    # step 27 - 5 uL purified assembly into 50 uL competent TOP10 cells
    for src, dest in zip(assembly_wells, cell_wells):
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(5, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # step 28 - quantify the leftover eluate
    protocol.comment(
        'MANUAL STEP (not simulated): measure the DNA concentration of the '
        'remaining 5 uL of each eluate with a NanoDrop-2000c for the CFU/ug '
        'calculation.')

    # step 29 - heat shock
    protocol.comment(
        'MANUAL STEP (not simulated): incubate cells_plate A1:D1 for 30 min on ice, '
        'heat shock at 42 C for 60 s, then return to ice for about 2 min.')

    # step 30 - 250 uL LB + 0.2% dextrose
    for well in cell_wells:
        p300.pick_up_tip()
        p300.aspirate(250, lb_dextrose)
        p300.dispense(250, well)
        p300.blow_out(well.top())
        p300.drop_tip()

    p20.reset_tipracks()
    p300.reset_tipracks()

    # steps 31-33 - recovery, plating and scoring
    protocol.comment(
        'MANUAL STEP (not simulated): recover the cells at 37 C for 60 min with '
        'shaking (about 250 rpm).')
    protocol.comment(
        'MANUAL STEP (not simulated): plate 50-200 uL of each recovery (neat or a '
        '10x dilution, depending on predicted efficiency) onto separate LB agar '
        'plates containing kanamycin 50 ug/mL; incubate at 37 C overnight.')
    protocol.comment(
        'MANUAL STEP (not simulated): count colonies per plate and score the '
        'fraction showing the expected chromoprotein colour (tsPurple = purple, '
        'YukonOFP = orange, aeBlue = blue, fuGFP = green); report CFU/ug of DNA '
        'plated.')
