"""AssemblyTron-style Golden Gate assembly of four four-fragment chromoprotein
expression plasmids on the Opentrons OT-2.

Workflow (after AssemblyTron, Synth. Biol. 2022, doi:10.1093/synbio/ysac032):
  1. Build a Q5 PCR master mix and distribute it over 7 fragment reactions.
  2. Add j5-designed primer pairs (0.1 uM final) and 0.5 ng linearized template.
  3. Off-deck gradient PCR, then DpnI digestion of residual template.
  4. Off-deck Zymo clean & concentrate of the 7 fragments.
  5. Golden Gate assembly (BsaI-HFv2 + T4 ligase), fragment volumes scaled to
     fragment length, 4 reactions (tsPurple, YukonOFP, aeBlue, fuGFP).
  6. Off-deck cleanup, then transformation of E. coli TOP10 competent cells.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 x 4-fragment chromoprotein plasmids',
    'author': 'Claude Opus 5.5',
    'description': ('Golden Gate assembly of four four-fragment chromoprotein '
                    'expression plasmids from seven PCR fragments, with DpnI '
                    'digestion and transformation into E. coli TOP10.'),
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

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips300])

    # ------------------------------------------------------------- reagent map
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

    # Seven PCR fragments live in column 1 of the PCR plate.
    frag_wells = [pcr_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    fwd_primers = [primer_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    rev_primers = [primer_plate[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    # Fragment -> linearized template (frag 1,2,5,6 share the tsPurple plasmid).
    templates = [template_plate[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]

    assembly_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cell_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    # One chromoprotein insert per assembly: tsPurple, YukonOFP, aeBlue, fuGFP.
    insert_wells = [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']]

    def mix_wells(pipette, wells, reps, volume):
        """Resuspend each well with a fresh tip."""
        for well in wells:
            pipette.pick_up_tip()
            pipette.mix(reps, volume, well)
            pipette.drop_tip()

    # ======================================================= 1-5: PCR master mix
    protocol.comment('Building Q5 PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')
    p300.transfer(106, water, pcr_mm)                 # 1
    p300.transfer(40, q5_buffer, pcr_mm)              # 2
    p20.transfer(4, dntp, pcr_mm)                     # 3
    p20.transfer(2, q5_pol, pcr_mm)                   # 4

    p300.pick_up_tip()                                # 5
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # =============================================== 6-10: assemble 7 PCRs
    protocol.comment('Distributing 19 uL master mix to pcr_plate A1:G1.')
    p20.transfer(19, pcr_mm, frag_wells, new_tip='once')             # 6

    protocol.comment('Adding j5-designed primers (2.5 uL each, 0.1 uM final).')
    p20.transfer(2.5, fwd_primers, frag_wells, new_tip='always')     # 7
    p20.transfer(2.5, rev_primers, frag_wells, new_tip='always')     # 8

    protocol.comment('Adding 1 uL linearized template (0.5 ng total per reaction).')
    p20.transfer(1, templates, frag_wells, new_tip='always')         # 9

    mix_wells(p20, frag_wells, 3, 15)                                # 10
    p20.reset_tipracks()

    # ------------------------------------------------- 11: off-deck gradient PCR
    protocol.comment(
        'MANUAL STEP: Seal pcr_plate (or move the PCR tubes) and transfer to the '
        'Bio-Rad C1000 gradient thermocycler. Run 98 C 30 s; 34 cycles of '
        '98 C 10 s, 30 s annealing at the AssemblyTron/j5 optimal-gradient '
        'temperature for each fragment, 72 C extension for the AssemblyTron-set '
        'time (~20-30 s/kb); final extension 72 C 5 min; hold 4 C. Take a sample '
        'of each reaction for gel electrophoresis, then return the plate to the OT-2.')

    # ====================================================== 12-15: DpnI digestion
    protocol.comment('Setting up DpnI digests (50 uL each) to remove template plasmid.')
    p20.transfer(19, water, frag_wells, new_tip='once')              # 12
    p20.transfer(5, rcutsmart, frag_wells, new_tip='once')           # 13
    p20.transfer(1, dpni, frag_wells, new_tip='once')                # 14

    mix_wells(p300, frag_wells, 3, 30)                               # 15
    p300.reset_tipracks()

    # ------------------------------------------------- 16-17: off-deck incubation
    protocol.comment(
        'MANUAL STEP: Incubate pcr_plate A1:G1 at 37 C for 30 min, then 65 C for '
        '20 min to inactivate DpnI, on the thermocycler block.')

    protocol.comment(
        'MANUAL STEP: Pausing for off-deck Zymo DNA Clean & Concentrator-5 '
        'cleanup of the 7 fragments; eluates go back into pcr_plate A1:G1 at '
        '20 uL each.')
    protocol.pause(
        'Clean and concentrate each of the 7 fragments on a Zymo DNA Clean & '
        'Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 uL per '
        '50 uL), spin 30 s, wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute '
        'in 20 uL nuclease-free water after 1 min at room temperature (30 s '
        'spin). Return the eluted fragments to their original positions in '
        'pcr_plate A1:G1 (fragments 1-7) and resume.')

    # ================================================= 18-24: Golden Gate setup
    protocol.comment('Setting up four 20 uL Golden Gate reactions in assembly_plate A1:D1.')
    p20.transfer(7, water, assembly_wells, new_tip='once')           # 18
    p20.transfer(2, t4_buffer, assembly_wells, new_tip='once')       # 19

    # Shared backbone fragments; volumes are proportional to fragment length.
    p20.transfer(3, pcr_plate['B1'], assembly_wells, new_tip='once')  # 20
    p20.transfer(2, pcr_plate['E1'], assembly_wells, new_tip='once')  # 21
    p20.transfer(3, pcr_plate['F1'], assembly_wells, new_tip='once')  # 22

    # One chromoprotein coding fragment per reaction.
    p20.transfer(2, insert_wells, assembly_wells, new_tip='always')   # 23

    protocol.comment('Adding Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase).')
    p20.transfer(1, gg_enzyme, assembly_wells,                        # 24
                 new_tip='always', mix_after=(5, 15))
    p20.reset_tipracks()

    # --------------------------------------------- 25-26: assembly + cleanup
    protocol.comment(
        'MANUAL STEP: Run the Golden Gate program on assembly_plate in the '
        'Opentrons thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; '
        'then 60 C 5 min; hold at 4 C, lid ~85 C. If no module is available, '
        'pause and move the reactions to another thermocycler.')

    protocol.comment(
        'MANUAL STEP: Clean and concentrate each assembly on a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in '
        '10 uL molecular grade water; return the eluates to assembly_plate A1:D1.')

    # ================================================== 27-33: transformation
    protocol.comment('Adding 5 uL purified assembly to 50 uL TOP10 competent cells.')
    p20.transfer(5, assembly_wells, cell_wells, new_tip='always')     # 27

    protocol.comment(
        'MANUAL STEP: Measure the DNA concentration of the remaining 5 uL of each '
        'eluate on a NanoDrop-2000c for the CFU/ug calculation.')

    protocol.comment(
        'MANUAL STEP: Incubate cells_plate A1:D1 for 30 min on ice, heat shock at '
        '42 C for 60 s, then return to ice for ~2 min.')

    protocol.comment('Adding 250 uL LB + 0.2% (w/v) dextrose to each transformation.')
    p300.transfer(250, lb_dextrose, cell_wells, new_tip='always')     # 30

    protocol.comment(
        'MANUAL STEP: Recover the cells at 37 C for 60 min with shaking (~250 rpm).')

    protocol.comment(
        'MANUAL STEP: Plate 50-200 uL of each recovery (neat or a 10x dilution, '
        'depending on predicted efficiency) onto separate LB agar plates '
        'containing 50 ug/mL kanamycin; incubate at 37 C overnight.')

    protocol.comment(
        'MANUAL STEP: Count colonies per plate and score the fraction showing the '
        'expected chromoprotein colour (purple, orange, blue, green); report '
        'CFU/ug of DNA plated.')
