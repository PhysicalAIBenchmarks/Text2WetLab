"""
AssemblyTron-style Golden Gate assembly of four four-fragment chromoprotein
expression plasmids on the Opentrons OT-2.

Reference: "AssemblyTron: flexible automation of DNA assembly with Opentrons
OT-2 lab robots", Synthetic Biology 2022, doi:10.1093/synbio/ysac032 (CC BY).

Workflow
  1.  Build a Q5 PCR master mix for 8 reactions (7 fragments + overage).
  2.  Set up 7 x 25 uL PCRs: 19 uL master mix, 0.1 uM final of each j5-designed
      primer (2.5 uL of a 1 uM stock), 0.5 ng linearized template (1 uL at
      0.5 ng/uL).
  3.  Manual gradient PCR on a Bio-Rad C100 (the OT-2 thermocycler module has
      no gradient capability), then back to the OT-2.
  4.  DpnI digestion to remove residual circular template.
  5.  Manual Zymo DNA Clean & Concentrator-5 cleanup of each fragment; residual
      polymerase fills in BsaI sticky ends and must be removed.
  6.  Golden Gate assembly: fragment volumes proportional to fragment length
      (roughly equimolar, assuming similar PCR efficiency), with T4 ligase
      buffer and the BsaI-HFv2 + T4 ligase Golden Gate Enzyme Mix.
  7.  Thermocycled assembly, cleanup, and transformation into chemically
      competent E. coli TOP10.

Fragments 2, 5 and 6 are the shared backbone/KanR parts; fragments 1, 3, 4 and
7 are the four chromoprotein coding parts (tsPurple, aeBlue, fuGFP, YukonOFP)
that distinguish the four final plasmids.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - 4 x 4-fragment chromoprotein plasmids',
    'author': 'AssemblyTron (Synth. Biol. 2022, ysac032)',
    'description': (
        'Gradient PCR setup, DpnI digestion, Golden Gate assembly with '
        'BsaI-HFv2 + T4 ligase, and transformation into E. coli TOP10.'
    ),
    'apiLevel': '2.13',
}


def run(protocol: protocol_api.ProtocolContext):

    # ------------------------------------------------------------------
    # Labware
    # ------------------------------------------------------------------
    tiprack20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack300])

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
    gg_enzyme = tubes_1_5ml_1.wells_by_name()['D2']     # BsaI-HFv2 + T4 ligase
    lb_dextrose = tubes_15ml_1.wells_by_name()['A1']    # LB + 0.2% (w/v) dextrose

    # Fragments 1-7 occupy column 1 of the PCR plate, in order.
    frag_names = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
    frag_wells = [pcr_plate.wells_by_name()[w] for w in frag_names]

    fwd_primers = [primer_plate.wells_by_name()[w] for w in frag_names]
    rev_primers = [primer_plate.wells_by_name()[w]
                   for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]

    # Template per fragment, as given on the run sheet. The shared backbone
    # parts and the tsPurple insert all come off the tsPurple plasmid; the
    # other three chromoprotein parts come off their own plasmids.
    #   fragment 1 -> template_plate A1 (tsPurple, chromoprotein part)
    #   fragment 2 -> template_plate A1 (backbone part)
    #   fragment 3 -> template_plate B1 (YukonOFP, chromoprotein part)
    #   fragment 4 -> template_plate C1 (aeBlue, chromoprotein part)
    #   fragment 5 -> template_plate A1 (backbone/KanR part)
    #   fragment 6 -> template_plate A1 (backbone part)
    #   fragment 7 -> template_plate D1 (fuGFP, chromoprotein part)
    template_map = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']
    templates = [template_plate.wells_by_name()[w] for w in template_map]

    assembly_names = ['A1', 'B1', 'C1', 'D1']
    assembly_wells = [assembly_plate.wells_by_name()[w] for w in assembly_names]
    cell_wells = [cells_plate.wells_by_name()[w] for w in assembly_names]

    # ------------------------------------------------------------------
    # Helpers. Tips are unlimited: reset the rack when it runs out.
    # ------------------------------------------------------------------
    def pick_up(pipette):
        try:
            pipette.pick_up_tip()
        except Exception:
            pipette.reset_tipracks()
            pipette.pick_up_tip()

    def transfer_one(pipette, volume, source, dest, mix_after=None):
        """Single aspirate/dispense with a fresh tip."""
        pick_up(pipette)
        pipette.aspirate(volume, source)
        pipette.dispense(volume, dest)
        if mix_after is not None:
            pipette.mix(mix_after[0], mix_after[1], dest)
        pipette.blow_out(dest.top())
        pipette.drop_tip()

    def distribute_one_to_many(pipette, volume, source, dests, mix_after=None):
        """One source well feeds every destination; fresh tip per destination."""
        for dest in dests:
            transfer_one(pipette, volume, source, dest, mix_after=mix_after)

    def transfer_pairwise(pipette, volume, sources, dests):
        """Sources and destinations pair in order; fresh tip per pair."""
        for source, dest in zip(sources, dests):
            transfer_one(pipette, volume, source, dest)

    def mix_wells(pipette, reps, volume, wells):
        for well in wells:
            pick_up(pipette)
            pipette.mix(reps, volume, well)
            pipette.blow_out(well.top())
            pipette.drop_tip()

    # ==================================================================
    # Part 1 - PCR master mix for 8 reactions (7 fragments + 1 overage)
    # ==================================================================
    protocol.comment(
        'STEP 1: 106 uL nuclease-free water -> PCR master mix tube '
        '(tubes_1_5ml_1 D1).')
    transfer_one(p300, 106, water, pcr_mm)

    protocol.comment(
        'STEP 2: 40 uL 5X Q5 reaction buffer -> PCR master mix tube.')
    transfer_one(p300, 40, q5_buffer, pcr_mm)

    protocol.comment('STEP 3: 4 uL 10 mM dNTPs -> PCR master mix tube.')
    transfer_one(p20, 4, dntp, pcr_mm)

    protocol.comment(
        'STEP 4: 2 uL Q5 High-Fidelity DNA Polymerase -> PCR master mix tube.')
    transfer_one(p20, 2, q5_pol, pcr_mm)

    protocol.comment('STEP 5: mix the PCR master mix, 5 cycles at 100 uL.')
    mix_wells(p300, 5, 100, [pcr_mm])

    # ==================================================================
    # Part 2 - PCR setup, 7 x 25 uL reactions
    # ==================================================================
    protocol.comment(
        'STEP 6: 19 uL PCR master mix -> pcr_plate A1:G1 (fragments 1-7).')
    distribute_one_to_many(p20, 19, pcr_mm, frag_wells)

    protocol.comment(
        'STEP 7: 2.5 uL forward primer (1 uM) -> matching pcr_plate well '
        '(0.1 uM final in 25 uL).')
    transfer_pairwise(p20, 2.5, fwd_primers, frag_wells)

    protocol.comment(
        'STEP 8: 2.5 uL reverse primer (1 uM) -> matching pcr_plate well '
        '(0.1 uM final in 25 uL).')
    transfer_pairwise(p20, 2.5, rev_primers, frag_wells)

    protocol.comment(
        'STEP 9: 1 uL linearized template plasmid (0.5 ng/uL = 0.5 ng) '
        '-> matching pcr_plate well.')
    transfer_pairwise(p20, 1, templates, frag_wells)

    protocol.comment('STEP 10: mix pcr_plate A1:G1, 3 cycles at 15 uL.')
    mix_wells(p20, 3, 15, frag_wells)

    # ------------------------------------------------------------------
    # Manual gradient PCR (not simulated)
    # ------------------------------------------------------------------
    protocol.comment(
        'STEP 11 (manual, not simulated): seal pcr_plate (or cap and move the '
        '100 uL PCR tubes) and carry the reactions to the Bio-Rad C100 '
        'gradient thermocycler. The OT-2 thermocycler module has no gradient '
        'capability, so this step is off-robot. Program: 98 C for 30 s; '
        '34 cycles of 98 C for 10 s, 30 s annealing at the '
        'AssemblyTron/j5 optimal-gradient temperature for each fragment '
        '(place each tube in the block column given by the gradient '
        'algorithm), and 72 C extension for the AssemblyTron-calculated time '
        '(about 20-30 s/kb); final extension 72 C for 5 min; hold at 4 C. '
        'Remove a sample of each reaction for gel electrophoresis to confirm '
        'fragment size, then return pcr_plate to slot 5 and resume.')
    protocol.pause(
        'Run the gradient PCR on the Bio-Rad C100, check fragments on a gel, '
        'then return pcr_plate to slot 5 and resume.')

    # ==================================================================
    # Part 3 - DpnI digestion of residual template
    # ==================================================================
    protocol.comment(
        'STEP 12: 19 uL nuclease-free water -> each PCR, pcr_plate A1:G1.')
    distribute_one_to_many(p20, 19, water, frag_wells)

    protocol.comment(
        'STEP 13: 5 uL rCutSmart Buffer -> each PCR, pcr_plate A1:G1.')
    distribute_one_to_many(p20, 5, rcutsmart, frag_wells)

    protocol.comment('STEP 14: 1 uL DpnI -> each PCR, pcr_plate A1:G1.')
    distribute_one_to_many(p20, 1, dpni, frag_wells)

    protocol.comment(
        'STEP 15: mix pcr_plate A1:G1, 3 cycles at 30 uL (50 uL digests).')
    mix_wells(p300, 3, 30, frag_wells)

    protocol.comment(
        'STEP 16 (manual, not simulated): incubate pcr_plate A1:G1 at 37 C for '
        '30 min to digest residual methylated plasmid template, then 65 C for '
        '20 min to inactivate DpnI, on the thermocycler block.')

    protocol.comment(
        'STEP 17 (manual, not simulated): clean and concentrate each of the 7 '
        'fragments on a Zymo DNA Clean & Concentrator-5 column. Residual Q5 '
        'polymerase fills in BsaI overhangs and must be removed before Golden '
        'Gate. Add DNA Binding Buffer 5:1 to sample (250 uL per 50 uL digest), '
        'spin 30 s, wash twice with 200 uL DNA Wash Buffer (30 s spins), then '
        'elute in 20 uL nuclease-free water after 1 min at room temperature '
        '(30 s spin). Return the eluted fragments 1-7 to their original '
        'positions pcr_plate A1:G1 and resume.')
    protocol.pause(
        'Clean and concentrate fragments 1-7 (Zymo DCC-5, elute in 20 uL '
        'water), return them to pcr_plate A1:G1, then resume.')

    # ==================================================================
    # Part 4 - Golden Gate assembly, 4 x 20 uL reactions
    # ==================================================================
    # Fragment volumes are proportional to fragment length, which gives a
    # roughly equimolar mix given similar PCR efficiency across fragments.
    protocol.comment(
        'STEP 18: 7 uL nuclease-free water -> assembly_plate A1:D1.')
    distribute_one_to_many(p20, 7, water, assembly_wells)

    protocol.comment(
        'STEP 19: 2 uL 10X T4 DNA Ligase Buffer -> assembly_plate A1:D1 '
        '(1X final in 20 uL).')
    distribute_one_to_many(p20, 2, t4_buffer, assembly_wells)

    protocol.comment(
        'STEP 20: 3 uL fragment 2 (backbone, pcr_plate B1) -> every assembly, '
        'assembly_plate A1:D1.')
    distribute_one_to_many(p20, 3, pcr_plate.wells_by_name()['B1'],
                           assembly_wells)

    protocol.comment(
        'STEP 21: 2 uL fragment 5 (backbone/KanR, pcr_plate E1) -> every '
        'assembly, assembly_plate A1:D1.')
    distribute_one_to_many(p20, 2, pcr_plate.wells_by_name()['E1'],
                           assembly_wells)

    protocol.comment(
        'STEP 22: 3 uL fragment 6 (backbone, pcr_plate F1) -> every assembly, '
        'assembly_plate A1:D1.')
    distribute_one_to_many(p20, 3, pcr_plate.wells_by_name()['F1'],
                           assembly_wells)

    protocol.comment(
        'STEP 23: 2 uL of each chromoprotein fragment -> its own assembly: '
        'fragment 1 (pcr_plate A1) -> A1, fragment 3 (C1) -> B1, '
        'fragment 4 (D1) -> C1, fragment 7 (G1) -> D1.')
    chromoprotein_frags = [pcr_plate.wells_by_name()[w]
                           for w in ['A1', 'C1', 'D1', 'G1']]
    transfer_pairwise(p20, 2, chromoprotein_frags, assembly_wells)

    protocol.comment(
        'STEP 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase) -> '
        'assembly_plate A1:D1, mixing 5 times after each dispense.')
    distribute_one_to_many(p20, 1, gg_enzyme, assembly_wells,
                           mix_after=(5, 15))

    protocol.comment(
        'STEP 25 (not simulated): run the Golden Gate program on '
        'assembly_plate in the Opentrons thermocycler module: 30 cycles of '
        '37 C for 5 min then 16 C for 5 min; 60 C for 5 min; hold at 4 C, with '
        'the lid at about 85 C. No gradient is needed, so the on-deck module '
        'is suitable. If no module is available, pause here and move the '
        'reactions to a separate thermocycler, then return them to '
        'assembly_plate A1:D1.')

    protocol.comment(
        'STEP 26 (manual, not simulated): clean and concentrate each assembly '
        'on a Zymo DNA Clean & Concentrator-5 column (DNA Binding Buffer 5:1 '
        'to sample, two 200 uL DNA Wash Buffer washes) and elute in 10 uL '
        'molecular grade water. Return the eluates to assembly_plate A1:D1.')
    protocol.pause(
        'Thermocycle the Golden Gate reactions, clean and concentrate them '
        '(elute in 10 uL water), return the eluates to assembly_plate A1:D1, '
        'then resume.')

    # ==================================================================
    # Part 5 - Transformation into chemically competent E. coli TOP10
    # ==================================================================
    protocol.comment(
        'STEP 27: 5 uL of each purified Golden Gate assembly -> 50 uL '
        'competent TOP10 cells, assembly_plate A1:D1 into cells_plate A1:D1.')
    transfer_pairwise(p20, 5, assembly_wells, cell_wells)

    protocol.comment(
        'STEP 28 (manual, not simulated): measure the DNA concentration of the '
        'remaining 5 uL of each eluate on a NanoDrop-2000c microvolume '
        'spectrophotometer, for the CFU/ug transformation efficiency '
        'calculation.')

    protocol.comment(
        'STEP 29 (manual, not simulated): incubate cells_plate A1:D1 for '
        '30 min on ice, heat shock at 42 C for 60 s, then return to ice for '
        'about 2 min.')
    protocol.pause(
        'Ice 30 min, heat shock 42 C for 60 s, ice about 2 min, then return '
        'cells_plate to slot 7 and resume for outgrowth medium.')

    protocol.comment(
        'STEP 30: 250 uL LB + 0.2% (w/v) dextrose (catabolite repression) -> '
        'cells_plate A1:D1.')
    distribute_one_to_many(p300, 250, lb_dextrose, cell_wells)

    protocol.comment(
        'STEP 31 (manual, not simulated): recover the transformations at 37 C '
        'for 60 min with shaking at about 250 rpm.')

    protocol.comment(
        'STEP 32 (manual, not simulated): plate 50-200 uL of each recovery, '
        'neat or as a 10x dilution depending on the predicted assembly '
        'efficiency, onto separate LB agar plates containing 50 ug/mL '
        'kanamycin; incubate at 37 C overnight.')

    protocol.comment(
        'STEP 33 (manual, not simulated): count colonies on each plate and '
        'score the fraction showing the expected chromoprotein colour '
        '(tsPurple purple, YukonOFP orange, aeBlue blue, fuGFP green); report '
        'transformation efficiency as CFU/ug of DNA plated.')

    protocol.comment('Protocol complete.')
