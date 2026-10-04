"""AssemblyTron-style Golden Gate assembly of four four-fragment chromoprotein
expression plasmids on the Opentrons OT-2.

Based on: AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2
lab robots, Synthetic Biology 2022, doi:10.1093/synbio/ysac032 (CC BY).

Workflow
--------
1.  Build a Q5 PCR master mix for 8 reactions (7 fragments + overage).
2.  Set up seven 25 uL PCRs (master mix + 0.1 uM primers + 0.5 ng linearized
    template) in pcr_plate column 1.
3.  Manual gradient PCR off-deck (Bio-Rad C100), then back to the OT-2.
4.  DpnI digestion of residual methylated template.
5.  Manual Zymo DNA Clean & Concentrator-5 cleanup of the seven fragments.
6.  Four Golden Gate reactions (BsaI-HFv2 + T4 DNA ligase), fragment volumes
    proportional to fragment length, thermocycled on the OT-2 module.
7.  Manual cleanup of the assemblies, then transformation of E. coli TOP10
    chemically competent cells and recovery in LB + 0.2% dextrose.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'Golden Gate assembly of four four-fragment chromoprotein plasmids',
    'author': 'AssemblyTron-style automated build',
    'description': ('PCR setup, DpnI digestion, Golden Gate assembly with '
                    'BsaI-HFv2/T4 ligase and transformation of E. coli TOP10 '
                    'for four four-fragment chromoprotein expression plasmids.'),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------
    # Labware (fixed deck layout, loaded with the operator's labels)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Reagent positions
    # ------------------------------------------------------------------
    water = tubes_50ml_1.wells_by_name()['A1']          # nuclease-free water
    q5_buffer = tubes_1_5ml_1.wells_by_name()['A1']     # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1.wells_by_name()['B1']          # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1.wells_by_name()['C1']        # Q5 HF DNA polymerase
    pcr_mm = tubes_1_5ml_1.wells_by_name()['D1']        # PCR master mix (built here)
    rcutsmart = tubes_1_5ml_1.wells_by_name()['A2']     # rCutSmart buffer
    dpni = tubes_1_5ml_1.wells_by_name()['B2']          # DpnI
    t4_buffer = tubes_1_5ml_1.wells_by_name()['C2']     # 10X T4 DNA ligase buffer
    gg_enzyme = tubes_1_5ml_1.wells_by_name()['D2']     # BsaI-HFv2 + T4 ligase mix
    lb_dextrose = tubes_15ml_1.wells_by_name()['A1']    # LB + 0.2% (w/v) dextrose

    # Seven fragments occupy column 1 of the PCR / fragment plate.
    frag_wells = [pcr_plate.wells_by_name()[w]
                  for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    fwd_primers = [primer_plate.wells_by_name()[w]
                   for w in ('A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1')]
    rev_primers = [primer_plate.wells_by_name()[w]
                   for w in ('A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2')]
    # Fragment -> linearized template plasmid:
    #   1,2,5,6 from tsPurple (A1); 3 YukonOFP (B1); 4 aeBlue (C1); 7 fuGFP (D1)
    templates = [template_plate.wells_by_name()[w]
                 for w in ('A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1')]

    assembly_wells = [assembly_plate.wells_by_name()[w]
                      for w in ('A1', 'B1', 'C1', 'D1')]
    cell_wells = [cells_plate.wells_by_name()[w]
                  for w in ('A1', 'B1', 'C1', 'D1')]

    # ------------------------------------------------------------------
    # Tip handling: tips are unlimited, reset a rack once it is used up.
    # ------------------------------------------------------------------
    tips_used = {'left': 0, 'right': 0}
    TIPS_PER_RACK = 96

    def get_tip(pipette):
        mount = 'left' if pipette is p20 else 'right'
        if tips_used[mount] >= TIPS_PER_RACK:
            pipette.reset_tipracks()
            tips_used[mount] = 0
        pipette.pick_up_tip()
        tips_used[mount] += 1

    def pick_pipette(volume):
        """20 uL pipette handles 1-20 uL, 300 uL pipette handles 20-300 uL."""
        return p20 if volume <= 20 else p300

    def deliver(volume, source, dest, mix_after=None):
        """Single transfer with a fresh tip, split across aspirations if needed."""
        pipette = pick_pipette(volume)
        get_tip(pipette)
        remaining = volume
        while remaining > 0.0001:
            this_vol = min(remaining, pipette.max_volume)
            pipette.aspirate(this_vol, source)
            pipette.dispense(this_vol, dest)
            pipette.blow_out(dest.top(-1))
            remaining -= this_vol
        if mix_after is not None:
            reps, mix_vol = mix_after
            pipette.mix(reps, mix_vol, dest)
            pipette.blow_out(dest.top(-1))
        pipette.drop_tip()

    def distribute_one_to_many(volume, source, dests, mix_after=None):
        """One source well feeds every listed destination, fresh tip each time."""
        for dest in dests:
            deliver(volume, source, dest, mix_after=mix_after)

    def transfer_paired(volume, sources, dests, mix_after=None):
        """Sources and destinations pair in order."""
        for source, dest in zip(sources, dests):
            deliver(volume, source, dest, mix_after=mix_after)

    def mix_wells(reps, volume, wells):
        pipette = pick_pipette(volume)
        for well in wells:
            get_tip(pipette)
            pipette.mix(reps, volume, well)
            pipette.blow_out(well.top(-1))
            pipette.drop_tip()

    # ==================================================================
    # Part 1 - PCR master mix for 8 reactions (7 fragments + overage)
    # ==================================================================
    protocol.comment('STEP 1: 106 uL nuclease-free water -> PCR master mix tube '
                     '(tubes_1_5ml_1 D1).')
    deliver(106, water, pcr_mm)

    protocol.comment('STEP 2: 40 uL 5X Q5 reaction buffer -> PCR master mix tube.')
    deliver(40, q5_buffer, pcr_mm)

    protocol.comment('STEP 3: 4 uL 10 mM dNTPs -> PCR master mix tube.')
    deliver(4, dntp, pcr_mm)

    protocol.comment('STEP 4: 2 uL Q5 High-Fidelity DNA Polymerase -> PCR master '
                     'mix tube.')
    deliver(2, q5_pol, pcr_mm)

    protocol.comment('STEP 5: Mix PCR master mix, 5 cycles at 100 uL.')
    mix_wells(5, 100, [pcr_mm])

    # ==================================================================
    # Part 2 - Set up seven 25 uL PCRs (0.1 uM primers, 0.5 ng template)
    # ==================================================================
    protocol.comment('STEP 6: 19 uL PCR master mix -> pcr_plate A1:G1 '
                     '(fragments 1-7).')
    distribute_one_to_many(19, pcr_mm, frag_wells)

    protocol.comment('STEP 7: 2.5 uL forward primer (1 uM) -> pcr_plate A1:G1 '
                     '(0.1 uM final in 25 uL).')
    transfer_paired(2.5, fwd_primers, frag_wells)

    protocol.comment('STEP 8: 2.5 uL reverse primer (1 uM) -> pcr_plate A1:G1 '
                     '(0.1 uM final in 25 uL).')
    transfer_paired(2.5, rev_primers, frag_wells)

    protocol.comment('STEP 9: 1 uL linearized template plasmid (0.5 ng/uL, '
                     '0.5 ng per reaction) -> pcr_plate A1:G1. Fragments 1,2,5,6 '
                     'from tsPurple; 3 from YukonOFP; 4 from aeBlue; 7 from fuGFP.')
    transfer_paired(1, templates, frag_wells)

    protocol.comment('STEP 10: Mix pcr_plate A1:G1, 3 cycles at 15 uL.')
    mix_wells(3, 15, frag_wells)

    # ------------------------------------------------------------------
    # Manual gradient PCR
    # ------------------------------------------------------------------
    protocol.comment('STEP 11 (manual, not simulated): Seal pcr_plate (or move the '
                     'PCR tubes) and transfer manually to the Bio-Rad C100 gradient '
                     'thermocycler. Run: 98 C 30 s; 34 cycles of 98 C 10 s, '
                     'annealing 30 s at the AssemblyTron/j5 optimal-gradient '
                     'temperature for each fragment, 72 C extension at the time set '
                     'by AssemblyTron (about 20-30 s/kb); final extension 72 C 5 min; '
                     'hold 4 C. Take a sample of each reaction for gel '
                     'electrophoresis, then return the reactions to the OT-2.')
    protocol.pause('Run the gradient PCR off-deck, then return pcr_plate A1:G1 to '
                   'slot 5 and resume.')

    # ==================================================================
    # Part 3 - DpnI digestion of residual methylated plasmid template
    # ==================================================================
    protocol.comment('STEP 12: 19 uL nuclease-free water -> pcr_plate A1:G1.')
    distribute_one_to_many(19, water, frag_wells)

    protocol.comment('STEP 13: 5 uL rCutSmart Buffer -> pcr_plate A1:G1.')
    distribute_one_to_many(5, rcutsmart, frag_wells)

    protocol.comment('STEP 14: 1 uL DpnI -> pcr_plate A1:G1.')
    distribute_one_to_many(1, dpni, frag_wells)

    protocol.comment('STEP 15: Mix pcr_plate A1:G1, 3 cycles at 30 uL.')
    mix_wells(3, 30, frag_wells)

    protocol.comment('STEP 16 (manual, not simulated): Incubate pcr_plate A1:G1 at '
                     '37 C for 30 min, then 65 C for 20 min to inactivate DpnI, on '
                     'the thermocycler block.')

    protocol.comment('STEP 17 (manual, not simulated): Clean and concentrate each of '
                     'the 7 fragments with a Zymo DNA Clean & Concentrator-5 column: '
                     '5:1 DNA Binding Buffer to sample (250 uL per 50 uL), spin 30 s, '
                     'wash 2 x 200 uL DNA Wash Buffer (30 s spins), elute in 20 uL '
                     'water after 1 min at room temperature (30 s spin). Return the '
                     'eluted fragments to their original positions pcr_plate A1:G1 '
                     '(fragments 1-7) and resume the protocol.')
    protocol.pause('Clean and concentrate the 7 fragments, return 20 uL of each '
                   'eluate to pcr_plate A1:G1, then resume.')

    # ==================================================================
    # Part 4 - Golden Gate assembly (BsaI-HFv2 + T4 DNA ligase)
    # Fragment volumes are proportional to fragment length.
    # ==================================================================
    protocol.comment('STEP 18: 7 uL nuclease-free water -> assembly_plate A1:D1.')
    distribute_one_to_many(7, water, assembly_wells)

    protocol.comment('STEP 19: 2 uL 10X T4 DNA Ligase Buffer -> assembly_plate '
                     'A1:D1.')
    distribute_one_to_many(2, t4_buffer, assembly_wells)

    protocol.comment('STEP 20: 3 uL fragment 2 (backbone, pcr_plate B1) -> '
                     'assembly_plate A1:D1.')
    distribute_one_to_many(3, pcr_plate.wells_by_name()['B1'], assembly_wells)

    protocol.comment('STEP 21: 2 uL fragment 5 (backbone/KanR, pcr_plate E1) -> '
                     'assembly_plate A1:D1.')
    distribute_one_to_many(2, pcr_plate.wells_by_name()['E1'], assembly_wells)

    protocol.comment('STEP 22: 3 uL fragment 6 (backbone, pcr_plate F1) -> '
                     'assembly_plate A1:D1.')
    distribute_one_to_many(3, pcr_plate.wells_by_name()['F1'], assembly_wells)

    protocol.comment('STEP 23: 2 uL of each chromoprotein fragment -> its own '
                     'assembly: fragment 1 (A1) -> A1, fragment 3 (C1) -> B1, '
                     'fragment 4 (D1) -> C1, fragment 7 (G1) -> D1.')
    chromoprotein_frags = [pcr_plate.wells_by_name()[w]
                           for w in ('A1', 'C1', 'D1', 'G1')]
    transfer_paired(2, chromoprotein_frags, assembly_wells)

    protocol.comment('STEP 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA '
                     'ligase) -> assembly_plate A1:D1, mixing 5 times after '
                     'dispensing (20 uL reactions).')
    distribute_one_to_many(1, gg_enzyme, assembly_wells, mix_after=(5, 15))

    protocol.comment('STEP 25 (not simulated): Run the Golden Gate program on '
                     'assembly_plate in the Opentrons thermocycler module: 30 cycles '
                     'of 37 C 5 min then 16 C 5 min; then 60 C 5 min; hold at 4 C. '
                     'Lid about 85 C. If no module is available, pause and move the '
                     'reactions to another thermocycler.')

    protocol.comment('STEP 26 (manual, not simulated): Clean and concentrate each '
                     'assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 '
                     'binding buffer, 2 x 200 uL wash) and elute in 10 uL molecular '
                     'grade water; return the eluates to assembly_plate A1:D1.')
    protocol.pause('Run the Golden Gate thermocycler program, clean and concentrate '
                   'the four assemblies, return 10 uL of each eluate to '
                   'assembly_plate A1:D1, then resume.')

    # ==================================================================
    # Part 5 - Transformation of E. coli TOP10 competent cells
    # ==================================================================
    protocol.comment('STEP 27: 5 uL purified Golden Gate assembly -> 50 uL TOP10 '
                     'chemically competent cells, assembly_plate A1:D1 -> '
                     'cells_plate A1:D1.')
    transfer_paired(5, assembly_wells, cell_wells)

    protocol.comment('STEP 28 (manual, not simulated): Measure the DNA concentration '
                     'of the remaining 5 uL of each eluate with a NanoDrop-2000c for '
                     'the CFU/ug calculation.')

    protocol.comment('STEP 29 (manual, not simulated): Incubate cells_plate A1:D1 for '
                     '30 min on ice, heat shock at 42 C for 60 s, then return to ice '
                     'for about 2 min.')
    protocol.pause('Incubate the transformations 30 min on ice, heat shock 42 C for '
                   '60 s, return to ice about 2 min, then resume for recovery '
                   'medium.')

    protocol.comment('STEP 30: 250 uL LB + 0.2% (w/v) dextrose -> cells_plate A1:D1.')
    distribute_one_to_many(250, lb_dextrose, cell_wells)

    protocol.comment('STEP 31 (manual, not simulated): Recover the cells at 37 C for '
                     '60 min with shaking at about 250 rpm.')

    protocol.comment('STEP 32 (manual, not simulated): Plate 50-200 uL of each '
                     'recovery (neat or a 10x dilution, depending on predicted '
                     'efficiency) onto separate LB agar plates containing kanamycin '
                     'at 50 ug/mL; incubate at 37 C overnight.')

    protocol.comment('STEP 33 (manual, not simulated): Manually count the colonies on '
                     'each plate and score the fraction showing the expected '
                     'chromoprotein colour (tsPurple purple, YukonOFP orange, aeBlue '
                     'blue, fuGFP green); report CFU/ug of DNA plated.')

    protocol.comment('Protocol complete: four four-fragment Golden Gate chromoprotein '
                     'assemblies transformed into E. coli TOP10.')
