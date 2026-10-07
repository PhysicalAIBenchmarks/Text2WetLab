"""
Golden Gate assembly of four 4-fragment chromoprotein expression plasmids on the OT-2.

Implements the AssemblyTron / j5 workflow described in:
  AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab robots
  Synth. Biol. 2022, doi:10.1093/synbio/ysac032 (CC BY).

End-to-end pipeline on the deck, from fragment PCR setup through Golden Gate assembly to
transformation into E. coli TOP10. Steps the robot cannot perform itself (thermocycling,
column clean-ups, off-deck incubations, plating) are recorded with protocol.comment().
"""

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'AssemblyTron Golden Gate: 4x chromoprotein plasmids',
    'description': 'PCR of 7 fragments -> DpnI digest -> column cleanup -> '
                   'Golden Gate (20 uL x4) -> TOP10 transformation.',
}

# ------------------------------------------------------------------------------
# Fixed design (j5 / AssemblyTron, given in the task)
# ------------------------------------------------------------------------------

# Fragments 1-7 live in pcr_plate column 1 (A1:G1).
FRAG_WELLS = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']

# Forward primers are primer_plate A1:G1, reverse primers primer_plate A2:G2.
# Template source for each fragment (template_plate), 0.5 ng/uL.
# Index = fragment number - 1.
TEMPLATE_WELLS = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']

# Golden Gate assemblies, one per chromoprotein. Fragment volumes (uL) are
# proportional to fragment length, given in the task, in a 20 uL reaction.
ASSEMBLIES = {
    'A1': {'chromo': 'A1', 'frag2': 3.0, 'frag5': 2.0, 'frag6': 3.0, 'chromo_vol': 2.0},  # tsPurple
    'B1': {'chromo': 'C1', 'frag2': 3.0, 'frag5': 2.0, 'frag6': 3.0, 'chromo_vol': 2.0},  # YukonOFP
    'C1': {'chromo': 'D1', 'frag2': 3.0, 'frag5': 2.0, 'frag6': 3.0, 'chromo_vol': 2.0},  # aeBlue
    'D1': {'chromo': 'G1', 'frag2': 3.0, 'frag5': 2.0, 'frag6': 3.0, 'chromo_vol': 2.0},  # fuGFP
}


def run(protocol):
    # --------------------------------------------------------------------------
    # Labware (deck is fixed by the operator; each piece loaded with its label)
    # --------------------------------------------------------------------------
    p20_tips = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    p300_tips = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[p20_tips])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[p300_tips])

    tubes_50ml = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_15ml_epp = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes_15ml = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    # Reagent tubes (by label)
    water = tubes_50ml['A1']              # nuclease-free water (unlimited)
    q5_buffer = tubes_15ml_epp['A1']      # 5X Q5 Reaction Buffer
    dntp = tubes_15ml_epp['B1']           # 10 mM dNTPs
    q5_pol = tubes_15ml_epp['C1']         # Q5 High-Fidelity DNA Polymerase
    pcr_mm = tubes_15ml_epp['D1']         # empty -> becomes PCR master mix
    rcutsmart = tubes_15ml_epp['A2']      # rCutSmart Buffer (10X)
    dpni = tubes_15ml_epp['B2']           # DpnI
    t4_buffer = tubes_15ml_epp['C2']      # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_15ml_epp['D2']      # Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase)
    lb_dextrose = tubes_15ml['A1']        # LB + 0.2% (w/v) dextrose

    pcr_wells = [pcr_plate[w] for w in FRAG_WELLS]

    # ==========================================================================
    # Stage 1 — PCR master mix (buffer + dNTPs + polymerase + water) for 8 reactions
    # ==========================================================================
    #
    # PCR is 25 uL per reaction (paper Methods 2.3) with 0.1 uM primers (1 uM stock)
    # and 0.5 ng template (0.5 ng/uL stock):
    #   5 uL 5X Q5 buffer (1X) + 0.5 uL 10 mM dNTPs (200 uM) + 0.25 uL Q5 pol
    #   + 2.5 uL fwd primer + 2.5 uL rev primer + 1 uL template + 13.25 uL water.
    # The master mix in tube D1 holds everything except the primers and template
    # (those differ per fragment): 19 uL per reaction, made for 8 reactions
    # (7 fragments + one reaction of dead volume so the last pipette is reliable).
    N_PCR_MASTERMIX = 8
    MM_WATER_UL = 13.25 * N_PCR_MASTERMIX   # 106 uL
    MM_BUFFER_UL = 5.0 * N_PCR_MASTERMIX    # 40 uL
    MM_DNTP_UL = 0.5 * N_PCR_MASTERMIX      # 4 uL
    MM_POL_UL = 0.25 * N_PCR_MASTERMIX      # 2 uL

    p300.transfer(MM_WATER_UL, water, pcr_mm, new_tip='once')
    p300.transfer(MM_BUFFER_UL, q5_buffer, pcr_mm, new_tip='once')
    p20.transfer(MM_DNTP_UL, dntp, pcr_mm, new_tip='once')
    p20.transfer(MM_POL_UL, q5_pol, pcr_mm, new_tip='once')
    p300.pick_up_tip()
    p300.mix(5, 100.0, pcr_mm)
    p300.drop_tip()

    # ==========================================================================
    # Stage 2 — Set up the 7 PCR reactions in pcr_plate A1:G1
    # ==========================================================================
    # 19 uL master mix + 2.5 uL fwd + 2.5 uL rev + 1 uL template = 25 uL each.
    p20.transfer(19.0, pcr_mm, pcr_wells, new_tip='once')

    fwd_wells = [primer_plate[w] for w in FRAG_WELLS]         # A1..G1
    rev_wells = [primer_plate[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    p20.transfer(2.5, fwd_wells, pcr_wells, new_tip='always')
    p20.transfer(2.5, rev_wells, pcr_wells, new_tip='always')
    p20.transfer(1.0, [template_plate[w] for w in TEMPLATE_WELLS], pcr_wells, new_tip='always')

    for well in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15.0, well)
        p20.drop_tip()

    # ==========================================================================
    # Stage 3 — off-deck PCR (gradient thermocycler)
    # ==========================================================================
    protocol.comment(
        'Seal pcr_plate (or transfer the 7 tubes) and move to the Bio-Rad C100 gradient '
        'thermocycler. Run: 98 C 30 s; 34 cycles of (98 C 10 s; anneal 30 s at the '
        'AssemblyTron/j5 optimal-gradient temperature for each fragment; 72 C extension at '
        'the AssemblyTron-calculated time, ~20-30 s/kb); 72 C 5 min final extension; hold '
        '4 C. Take a small gel sample of each reaction to confirm fragment sizes, then '
        'return the plate to the OT-2.'
    )

    # ==========================================================================
    # Stage 4 — DpnI digest of residual template (back on the OT-2)
    # ==========================================================================
    # Paper Methods 2.3: 19 uL water + 5 uL rCutSmart + 1 uL DpnI per reaction.
    # Added to each 25 uL PCR -> 50 uL total with 1X rCutSmart.
    p20.transfer(19.0, water, pcr_wells, new_tip='once')
    p20.transfer(5.0, rcutsmart, pcr_wells, new_tip='once')
    p20.transfer(1.0, dpni, pcr_wells, new_tip='once')

    for well in pcr_wells:
        p300.pick_up_tip()
        p300.mix(3, 30.0, well)
        p300.drop_tip()

    protocol.comment(
        'Incubate the 7 DpnI reactions (pcr_plate A1:G1) at 37 C for 30 min, then heat '
        'denature DpnI at 65 C for 20 min.'
    )

    # ==========================================================================
    # Stage 5 — Off-deck column clean-up of fragments
    # ==========================================================================
    # Cleaning removes the Q5 polymerase, which was found to interfere with assembly.
    # Elute in 20 uL water: fragments 2 and 6 are added at 3 uL to all four assemblies
    # (12 uL total needed), so a 10 uL elution would not be enough.
    protocol.comment(
        'PAUSE. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 DNA Binding Buffer to sample; 2x 200 uL DNA Wash Buffer), '
        'eluting each fragment in 20 uL molecular-grade water after 1 min at room temperature. '
        'Return the eluates to pcr_plate A1:G1 (fragments 1-7) and resume.'
    )

    # ==========================================================================
    # Stage 6 — Golden Gate assembly (20 uL reactions in assembly_plate A1:D1)
    # ==========================================================================
    # Fixed design: water 7 uL + 10X T4 ligase buffer 2 uL (1X) + fragments
    # (frag2 3 + frag5 2 + frag6 3 + chromo 2 = 10 uL) + GG enzyme mix 1 uL = 20 uL.
    # Fragment 2 = pcr B1, fragment 5 = pcr E1, fragment 6 = pcr F1 (shared by all 4).
    assembly_wells = [assembly_plate[w] for w in ASSEMBLIES]

    p20.transfer(7.0, water, assembly_wells, new_tip='once')
    p20.transfer(2.0, t4_buffer, assembly_wells, new_tip='once')

    # Shared backbone/KanR fragments go to all four assemblies.
    p20.transfer(ASSEMBLIES['A1']['frag2'], pcr_plate['B1'], assembly_wells, new_tip='once')  # fragment 2, 3 uL
    p20.transfer(ASSEMBLIES['A1']['frag5'], pcr_plate['E1'], assembly_wells, new_tip='once')  # fragment 5, 2 uL
    p20.transfer(ASSEMBLIES['A1']['frag6'], pcr_plate['F1'], assembly_wells, new_tip='once')  # fragment 6, 3 uL

    # Chromoprotein fragment into its own assembly well.
    for dest, spec in ASSEMBLIES.items():
        p20.transfer(spec['chromo_vol'], pcr_plate[spec['chromo']],
                     assembly_plate[dest], new_tip='always')

    # Enzyme last, with a light mix.
    p20.transfer(1.0, gg_enzyme, assembly_wells, new_tip='once', mix_after=(3, 15.0))

    protocol.comment(
        'Run the Golden Gate program on assembly_plate in the Opentrons thermocycler module: '
        '30 cycles of (37 C 5 min then 16 C 5 min), then 60 C 5 min, hold at 4 C; lid ~85 C. '
        'If the thermocycler module is not available, pause and move the reactions to a '
        'bench thermocycler.'
    )

    # ==========================================================================
    # Stage 7 — Off-deck clean-up of the assembled plasmids
    # ==========================================================================
    protocol.comment(
        'Clean and concentrate each of the 4 Golden Gate assemblies with a Zymo DNA Clean & '
        'Concentrator-5 column (5:1 binding buffer; 2x 200 uL wash) and elute in 10 uL '
        'molecular-grade water; return the eluates to assembly_plate A1:D1.'
    )

    # ==========================================================================
    # Stage 8 — Transformation into TOP10 competent cells
    # ==========================================================================
    # 5 uL of each assembly eluate -> 50 uL chemically competent TOP10 (cells_plate A1:D1).
    cell_wells = [cells_plate[w] for w in ASSEMBLIES]
    p20.transfer(5.0, assembly_wells, cell_wells, new_tip='always', mix_after=(3, 20.0))

    protocol.comment(
        'Measure the DNA concentration of the remaining ~5 uL of each eluate with a '
        'NanoDrop-2000c for the CFU/ug calculation, then incubate cells_plate A1:D1 on ice '
        'for 30 min, heat shock at 42 C for 60 s, and return to ice for ~2 min.'
    )

    # Recovery in LB + 0.2% dextrose (paper Methods 2.3: 250 uL per transformation).
    p300.transfer(250.0, lb_dextrose, cell_wells, new_tip='once')

    protocol.comment(
        'Recover the cells at 37 C for 60 min with shaking (~250 rpm).'
    )

    protocol.comment(
        'Plate 50-200 uL of each recovery (neat or a 10x dilution, depending on predicted '
        'efficiency) onto LB agar + kanamycin 50 ug/mL; incubate at 37 C overnight.'
    )

    protocol.comment(
        'Manually count colonies per plate and score the fraction showing the expected '
        'chromoprotein colour (tsPurple = purple, YukonOFP = orange, aeBlue = blue, '
        'fuGFP = green); report CFU/ug of DNA plated.'
    )