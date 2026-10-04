"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

Automated with AssemblyTron-style logic on an Opentrons OT-2.
Based on: AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2
lab robots, Synthetic Biology 2022, doi:10.1093/synbio/ysac032 (CC BY 4.0).

Workflow
--------
  1. Build a Q5 PCR master mix for 8 reactions and distribute it to 7 fragment
     reactions (25 uL each) with j5-designed primers (0.1 uM final) and 0.5 ng
     of linearized template.
  2. Manual gradient PCR on a Bio-Rad C100 (annealing gradient and extension
     time from the AssemblyTron/j5 optimal annealing algorithm).
  3. DpnI digestion of residual plasmid template, then a manual Zymo DNA
     Clean & Concentrator-5 purification of each fragment.
  4. Golden Gate assembly: fragments pooled at volumes proportional to fragment
     length (roughly equimolar), with BsaI-HFv2 + T4 DNA ligase.
  5. Clean-up, then transformation into chemically competent E. coli TOP10.
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: 4 x 4-fragment chromoprotein plasmids',
    'author': 'Claude Opus 5',
    'description': ('Gradient PCR setup, DpnI digestion, length-proportional '
                    'Golden Gate assembly and transformation of four '
                    'four-fragment chromoprotein expression plasmids.'),
    'source': 'doi:10.1093/synbio/ysac032',
    'apiLevel': '2.13',
}

# Fragment identity, for the run log.
FRAGMENTS = {
    'A1': 'fragment 1 (chromoprotein, tsPurple)',
    'B1': 'fragment 2 (backbone)',
    'C1': 'fragment 3 (chromoprotein, YukonOFP)',
    'D1': 'fragment 4 (chromoprotein, aeBlue)',
    'E1': 'fragment 5 (backbone / KanR)',
    'F1': 'fragment 6 (backbone)',
    'G1': 'fragment 7 (chromoprotein, fuGFP)',
}

PCR_WELLS = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
ASSEMBLY_WELLS = ['A1', 'B1', 'C1', 'D1']


def run(protocol):
    # ------------------------------------------------------------------
    # Deck
    # ------------------------------------------------------------------
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

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

    # Reagent tubes
    water = tubes_50ml_1['A1']          # nuclease-free water
    q5_buffer = tubes_1_5ml_1['A1']     # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1['B1']          # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1['C1']        # Q5 High-Fidelity DNA Polymerase
    pcr_mm = tubes_1_5ml_1['D1']        # PCR master mix (built below)
    rcutsmart = tubes_1_5ml_1['A2']     # rCutSmart Buffer
    dpni = tubes_1_5ml_1['B2']          # DpnI
    t4_buffer = tubes_1_5ml_1['C2']     # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']     # Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase)
    lb_dextrose = tubes_15ml_1['A1']    # LB + 0.2% (w/v) dextrose

    # ------------------------------------------------------------------
    # Tip bookkeeping: tips are unlimited, so recycle a rack once spent.
    # ------------------------------------------------------------------
    tips_used = {'left': 0, 'right': 0}

    def budget(pipette, n_tips):
        """Reset the tip rack if this operation would run it past 96 tips."""
        mount = pipette.mount
        if tips_used[mount] + n_tips > 96:
            pipette.reset_tipracks()
            tips_used[mount] = 0
        tips_used[mount] += n_tips

    def pick(pipette):
        budget(pipette, 1)
        pipette.pick_up_tip()

    def mix_wells(pipette, wells, cycles, volume):
        """Mix each well with a fresh tip."""
        for well in wells:
            pick(pipette)
            pipette.mix(cycles, volume, well)
            pipette.drop_tip()

    def move(pipette, volume, sources, dests, mix_after=None):
        """One fresh tip per source/destination pair."""
        if not isinstance(sources, list):
            sources = [sources] * len(dests)
        budget(pipette, len(dests))
        pipette.transfer(volume, sources, dests,
                         new_tip='always', mix_after=mix_after)

    # ==================================================================
    # Part 1 - PCR setup (7 fragments, 25 uL reactions)
    # ==================================================================
    protocol.comment('=== Part 1: PCR setup for 7 fragments (25 uL each) ===')

    # Step 1-4: Q5 master mix for 8 reactions, assembled in tubes_1_5ml_1 D1.
    protocol.comment('Step 1: 106 uL nuclease-free water -> PCR master mix tube (D1).')
    move(p300, 106, water, [pcr_mm])

    protocol.comment('Step 2: 40 uL 5X Q5 reaction buffer -> PCR master mix tube (D1).')
    move(p300, 40, q5_buffer, [pcr_mm])

    protocol.comment('Step 3: 4 uL 10 mM dNTPs -> PCR master mix tube (D1).')
    move(p20, 4, dntp, [pcr_mm])

    protocol.comment('Step 4: 2 uL Q5 High-Fidelity DNA Polymerase -> PCR master mix tube (D1).')
    move(p20, 2, q5_pol, [pcr_mm])

    # Step 5: homogenise the 152 uL master mix.
    protocol.comment('Step 5: mix the PCR master mix, 5 cycles at 100 uL.')
    mix_wells(p300, [pcr_mm], 5, 100)

    # Step 6: 19 uL master mix into each fragment reaction.
    protocol.comment('Step 6: 19 uL PCR master mix -> pcr_plate A1:G1.')
    move(p20, 19, pcr_mm, [pcr_plate[w] for w in PCR_WELLS])

    # Step 7-8: j5-designed primers, 2.5 uL of 1 uM each -> 0.1 uM in 25 uL.
    protocol.comment('Step 7: 2.5 uL forward primer (1 uM) -> matching pcr_plate well.')
    move(p20, 2.5,
         [primer_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']],
         [pcr_plate[w] for w in PCR_WELLS])

    protocol.comment('Step 8: 2.5 uL reverse primer (1 uM) -> matching pcr_plate well.')
    move(p20, 2.5,
         [primer_plate[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']],
         [pcr_plate[w] for w in PCR_WELLS])

    # Step 9: 1 uL of 0.5 ng/uL linearized template = 0.5 ng per reaction.
    protocol.comment('Step 9: 1 uL linearized template plasmid (0.5 ng/uL) -> pcr_plate A1:G1.')
    for src, dest in zip(['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1'], PCR_WELLS):
        protocol.comment('  template_plate {} -> pcr_plate {} ({})'.format(
            src, dest, FRAGMENTS[dest]))
    move(p20, 1,
         [template_plate[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']],
         [pcr_plate[w] for w in PCR_WELLS])

    # Step 10: homogenise each 25 uL reaction.
    protocol.comment('Step 10: mix pcr_plate A1:G1, 3 cycles at 15 uL.')
    mix_wells(p20, [pcr_plate[w] for w in PCR_WELLS], 3, 15)

    # Step 11: manual gradient PCR (OT-2 thermocycler module has no gradient).
    protocol.comment('Step 11 (MANUAL, not simulated): seal pcr_plate (or cap the PCR '
                     'tubes) and transfer to the Bio-Rad C100 gradient thermocycler.')
    protocol.comment('  Program: 98 C 30 s; 34 cycles of [98 C 10 s, annealing 30 s at '
                     'the AssemblyTron/j5 optimal-gradient temperature for each '
                     'fragment, 72 C extension for the AssemblyTron-set time '
                     '(~20-30 s/kb)]; final extension 72 C 5 min; hold 4 C.')
    protocol.comment('  Position each tube in the gradient block per the AssemblyTron '
                     'reactions_setup instructions.')
    protocol.comment('  Then remove a sample of each reaction for gel electrophoresis '
                     'and return the reactions to pcr_plate A1:G1 on the OT-2.')
    protocol.pause('Run the gradient PCR, take gel samples, then return pcr_plate '
                   'A1:G1 to slot 5 and resume.')

    # ==================================================================
    # Part 2 - DpnI digestion of residual template
    # ==================================================================
    protocol.comment('=== Part 2: DpnI digestion of residual plasmid template ===')

    protocol.comment('Step 12: 19 uL nuclease-free water -> pcr_plate A1:G1.')
    move(p20, 19, water, [pcr_plate[w] for w in PCR_WELLS])

    protocol.comment('Step 13: 5 uL rCutSmart Buffer -> pcr_plate A1:G1.')
    move(p20, 5, rcutsmart, [pcr_plate[w] for w in PCR_WELLS])

    protocol.comment('Step 14: 1 uL DpnI -> pcr_plate A1:G1.')
    move(p20, 1, dpni, [pcr_plate[w] for w in PCR_WELLS])

    protocol.comment('Step 15: mix pcr_plate A1:G1, 3 cycles at 30 uL (50 uL digests).')
    mix_wells(p300, [pcr_plate[w] for w in PCR_WELLS], 3, 30)

    # Step 16: manual incubation.
    protocol.comment('Step 16 (MANUAL, not simulated): incubate pcr_plate A1:G1 at 37 C '
                     'for 30 min, then 65 C for 20 min to inactivate DpnI, on the '
                     'thermocycler block.')

    # Step 17: manual column clean-up. Residual polymerase fills in BsaI sticky
    # ends, so each fragment must be purified before Golden Gate assembly.
    protocol.comment('Step 17 (MANUAL, not simulated): clean and concentrate each of the '
                     '7 fragments on a Zymo DNA Clean & Concentrator-5 column.')
    protocol.comment('  5:1 DNA Binding Buffer to sample (250 uL per 50 uL digest), spin '
                     '30 s; wash 2 x 200 uL DNA Wash Buffer (30 s spins); elute in 20 uL '
                     'water after 1 min at room temperature (30 s spin).')
    protocol.comment('  This removes polymerase, which otherwise fills in the BsaI '
                     'overhangs and blocks assembly.')
    protocol.comment('  Return the eluted fragments 1-7 to their original positions, '
                     'pcr_plate A1:G1.')
    protocol.pause('Column-purify fragments 1-7, return 20 uL eluates to pcr_plate '
                   'A1:G1, then resume.')

    # ==================================================================
    # Part 3 - Golden Gate assembly (20 uL reactions)
    # ==================================================================
    protocol.comment('=== Part 3: Golden Gate assembly, 4 x 4-fragment reactions ===')
    protocol.comment('Fragment volumes are proportional to fragment length, which gives '
                     'a roughly equimolar mix assuming similar PCR yields.')

    assembly_dests = [assembly_plate[w] for w in ASSEMBLY_WELLS]

    protocol.comment('Step 18: 7 uL nuclease-free water -> assembly_plate A1:D1.')
    move(p20, 7, water, assembly_dests)

    protocol.comment('Step 19: 2 uL 10X T4 DNA Ligase Buffer -> assembly_plate A1:D1.')
    move(p20, 2, t4_buffer, assembly_dests)

    protocol.comment('Step 20: 3 uL fragment 2 (backbone) from pcr_plate B1 -> assembly_plate A1:D1.')
    move(p20, 3, pcr_plate['B1'], assembly_dests)

    protocol.comment('Step 21: 2 uL fragment 5 (backbone/KanR) from pcr_plate E1 -> assembly_plate A1:D1.')
    move(p20, 2, pcr_plate['E1'], assembly_dests)

    protocol.comment('Step 22: 3 uL fragment 6 (backbone) from pcr_plate F1 -> assembly_plate A1:D1.')
    move(p20, 3, pcr_plate['F1'], assembly_dests)

    protocol.comment('Step 23: 2 uL of the variable chromoprotein fragment into each assembly.')
    for src, dest in zip(['A1', 'C1', 'D1', 'G1'], ASSEMBLY_WELLS):
        protocol.comment('  pcr_plate {} -> assembly_plate {} ({})'.format(
            src, dest, FRAGMENTS[src]))
    move(p20, 2,
         [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']],
         assembly_dests)

    protocol.comment('Step 24: 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 DNA ligase) '
                     '-> assembly_plate A1:D1, mixing 5 times after dispensing.')
    move(p20, 1, gg_enzyme, assembly_dests, mix_after=(5, 10))

    # Step 25: Opentrons thermocycler module (no gradient needed for Golden Gate).
    protocol.comment('Step 25 (MANUAL/MODULE, not simulated): run the Golden Gate program '
                     'on assembly_plate in the Opentrons thermocycler module.')
    protocol.comment('  30 cycles of [37 C 5 min, 16 C 5 min]; then 60 C 5 min; hold 4 C. '
                     'Lid ~85 C.')
    protocol.comment('  If no thermocycler module is available, pause here and move the '
                     'reactions to a separate thermocycler.')
    protocol.pause('Run the Golden Gate thermocycler program on assembly_plate A1:D1, '
                   'then resume.')

    # Step 26: manual clean-up of the assemblies.
    protocol.comment('Step 26 (MANUAL, not simulated): clean and concentrate each assembly '
                     'on a Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, '
                     '2 x 200 uL washes) and elute in 10 uL molecular grade water.')
    protocol.comment('  Return the 10 uL eluates to assembly_plate A1:D1.')
    protocol.pause('Column-purify the four assemblies, return 10 uL eluates to '
                   'assembly_plate A1:D1, then resume.')

    # ==================================================================
    # Part 4 - Transformation into E. coli TOP10
    # ==================================================================
    protocol.comment('=== Part 4: transformation into chemically competent E. coli TOP10 ===')

    protocol.comment('Step 27: 5 uL purified Golden Gate assembly -> 50 uL competent cells.')
    move(p20, 5, assembly_dests, [cells_plate[w] for w in ASSEMBLY_WELLS])

    protocol.comment('Step 28 (MANUAL, not simulated): measure the DNA concentration of '
                     'the remaining 5 uL of each eluate on a NanoDrop-2000c for the '
                     'CFU/ug transformation efficiency calculation.')

    protocol.comment('Step 29 (MANUAL, not simulated): incubate cells_plate A1:D1 for '
                     '30 min on ice, heat shock at 42 C for 60 s, then return to ice for '
                     'about 2 min.')
    protocol.pause('Ice 30 min, heat shock 42 C for 60 s, back on ice ~2 min, then '
                   'return cells_plate to slot 7 and resume.')

    protocol.comment('Step 30: 250 uL LB + 0.2% (w/v) dextrose -> cells_plate A1:D1.')
    move(p300, 250, lb_dextrose, [cells_plate[w] for w in ASSEMBLY_WELLS])

    protocol.comment('Step 31 (MANUAL, not simulated): recover the cells at 37 C for '
                     '60 min with shaking at about 250 rpm.')

    protocol.comment('Step 32 (MANUAL, not simulated): plate 50-200 uL of each recovery, '
                     'neat or as a 10x dilution depending on the predicted efficiency, '
                     'onto separate LB agar plates with kanamycin at 50 ug/mL; incubate '
                     'at 37 C overnight.')

    protocol.comment('Step 33 (MANUAL, not simulated): count colonies per plate, score '
                     'the fraction showing the expected chromoprotein colour (A1 purple '
                     'tsPurple, B1 orange YukonOFP, C1 blue aeBlue, D1 green fuGFP) and '
                     'report CFU/ug of DNA plated.')

    protocol.comment('=== Protocol complete: four Golden Gate chromoprotein assemblies '
                     'transformed ===')
