"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow on the OT-2 (Synth. Biol. 2022, doi:10.1093/synbio/ysac032):
PCR setup of seven fragments, DpnI digestion of residual template, column clean-up,
Golden Gate assembly with BsaI-HFv2 + T4 DNA ligase, and transformation into
chemically competent E. coli TOP10.
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 chromoprotein plasmids (4 fragments each)',
    'author': 'AssemblyTron',
    'description': (
        'PCR amplification of 7 fragments, DpnI digestion, Golden Gate assembly of four '
        'four-fragment chromoprotein expression plasmids, and transformation into E. coli TOP10.'
    ),
    'apiLevel': '2.13',
}


def run(protocol):
    # ------------------------------------------------------------------ labware
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

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

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

    # Fragments 1-7 live in column 1 of the PCR plate.
    frag_wells = [pcr_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    fwd_primers = [primer_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    rev_primers = [primer_plate[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    # Fragment -> template: frags 1,2,5,6 from tsPurple plasmid; 3 YukonOFP; 4 aeBlue; 7 fuGFP.
    templates = [template_plate[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]

    assembly_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    cell_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    # Chromoprotein insert for each of the four assemblies (fragments 1, 3, 4, 7).
    insert_wells = [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']]

    def pip_for(volume):
        """Pick the pipette whose working range covers this volume."""
        return p20 if volume <= 20 else p300

    def transfer(volume, source, dest, mix_after=None, new_tip='always'):
        pipette = pip_for(volume)
        pipette.transfer(volume, source, dest, mix_after=mix_after, new_tip=new_tip)

    def mix(volume, well, cycles):
        pipette = pip_for(volume)
        pipette.pick_up_tip()
        pipette.mix(cycles, volume, well)
        pipette.drop_tip()

    # ------------------------------------------------- 1-5: PCR master mix (8 rxn)
    protocol.comment('Building PCR master mix for 8 reactions in tubes_1_5ml_1 D1.')
    transfer(106, water, pcr_mm)
    transfer(40, q5_buffer, pcr_mm)
    transfer(4, dntp, pcr_mm)
    transfer(2, q5_pol, pcr_mm)
    mix(100, pcr_mm, 5)

    # ------------------------------------------------- 6-10: PCR reaction assembly
    protocol.comment('Distributing 19 uL PCR master mix to pcr_plate A1:G1.')
    transfer(19, pcr_mm, frag_wells)

    protocol.comment('Adding 2.5 uL of each forward primer (1 uM).')
    transfer(2.5, fwd_primers, frag_wells)

    protocol.comment('Adding 2.5 uL of each reverse primer (1 uM).')
    transfer(2.5, rev_primers, frag_wells)

    protocol.comment('Adding 1 uL linearized template (0.5 ng/uL) to each reaction.')
    transfer(1, templates, frag_wells)

    protocol.comment('Mixing each 25 uL PCR reaction.')
    for well in frag_wells:
        mix(15, well, 3)

    # ------------------------------------------------------------- 11: gradient PCR
    protocol.comment(
        'MANUAL STEP (not simulated): seal pcr_plate (or move the PCR tubes) and transfer '
        'manually to the Bio-Rad C100 gradient thermocycler. Run: 98 C 30 s; 34 cycles of '
        '98 C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature for '
        'each fragment, 72 C extension at the time set by AssemblyTron (about 20-30 s/kb); '
        'final extension 72 C 5 min; hold 4 C. Take a sample of each reaction for gel '
        'electrophoresis, then return the plate to the OT-2.')

    # --------------------------------------------------------- 12-15: DpnI digestion
    protocol.comment('Setting up DpnI digests (50 uL final) in pcr_plate A1:G1.')
    transfer(19, water, frag_wells)
    transfer(5, rcutsmart, frag_wells)
    transfer(1, dpni, frag_wells)

    protocol.comment('Mixing each 50 uL DpnI digest.')
    for well in frag_wells:
        mix(30, well, 3)

    # ------------------------------------------------- 16-17: incubation + clean-up
    protocol.comment(
        'MANUAL STEP (not simulated): incubate pcr_plate A1:G1 at 37 C for 30 min, then '
        '65 C for 20 min (DpnI inactivation) on the thermocycler block.')

    protocol.pause(
        'PAUSE (not simulated): clean and concentrate each of the 7 fragments with a Zymo '
        'DNA Clean & Concentrator-5 column: 5:1 DNA Binding Buffer to sample (250 uL per '
        '50 uL), spin 30 s, wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL '
        'water after 1 min at room temperature (30 s spin). Return the eluted fragments to '
        'their original positions pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')

    # ------------------------------------------------ 18-24: Golden Gate reactions
    protocol.comment('Setting up four 20 uL Golden Gate reactions in assembly_plate A1:D1.')
    transfer(7, water, assembly_wells)
    transfer(2, t4_buffer, assembly_wells)

    # Backbone fragments are shared by all four assemblies; volumes scale with length.
    protocol.comment('Adding shared backbone fragments 2, 5 and 6.')
    transfer(3, pcr_plate['B1'], assembly_wells)
    transfer(2, pcr_plate['E1'], assembly_wells)
    transfer(3, pcr_plate['F1'], assembly_wells)

    protocol.comment('Adding chromoprotein fragments 1, 3, 4 and 7 to their assemblies.')
    transfer(2, insert_wells, assembly_wells)

    protocol.comment('Adding 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase).')
    transfer(1, gg_enzyme, assembly_wells, mix_after=(5, 10))

    # -------------------------------------------- 25-26: thermocycling + clean-up
    protocol.comment(
        'MANUAL STEP (not simulated): run the Golden Gate program on assembly_plate in the '
        'Opentrons thermocycler module: 30 cycles of 37 C 5 min then 16 C 5 min; then '
        '60 C 5 min; hold at 4 C. Lid about 85 C. If no module is available, pause and move '
        'the reactions to another thermocycler.')

    protocol.comment(
        'MANUAL STEP (not simulated): clean and concentrate each assembly with a Zymo DNA '
        'Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and elute in '
        '10 uL molecular grade water; return the eluates to assembly_plate A1:D1.')

    # ------------------------------------------------------ 27-33: transformation
    protocol.comment('Adding 5 uL of each purified assembly to competent TOP10 cells.')
    transfer(5, assembly_wells, cell_wells)

    protocol.comment(
        'MANUAL STEP (not simulated): measure the DNA concentration of the remaining 5 uL of '
        'each eluate with a NanoDrop-2000c for the CFU/ug calculation.')

    protocol.comment(
        'MANUAL STEP (not simulated): incubate cells_plate A1:D1 for 30 min on ice, heat '
        'shock at 42 C for 60 s, then return to ice for about 2 min.')

    protocol.comment('Adding 250 uL LB + 0.2% (w/v) dextrose to each transformation.')
    transfer(250, lb_dextrose, cell_wells)

    protocol.comment(
        'MANUAL STEP (not simulated): recover the cells at 37 C for 60 min with shaking '
        '(about 250 rpm).')

    protocol.comment(
        'MANUAL STEP (not simulated): plate 50-200 uL of each recovery (neat or a 10x '
        'dilution, depending on predicted efficiency) onto separate LB agar plates '
        'containing kanamycin 50 ug/mL; incubate at 37 C overnight.')

    protocol.comment(
        'MANUAL STEP (not simulated): manually count the colonies per plate and score the '
        'fraction showing the expected chromoprotein colour (purple, orange, blue, green); '
        'report CFU/ug of DNA plated.')

    p20.reset_tipracks()
    p300.reset_tipracks()
