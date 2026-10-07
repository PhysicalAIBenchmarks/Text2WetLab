"""AssemblyTron Golden Gate assembly of four four-fragment chromoprotein
expression plasmids on the OT-2, following:

    Boehm et al., "AssemblyTron: flexible automation of DNA assembly with
    Opentrons OT-2 lab robots", Synth. Biol. 2022, doi:10.1093/synbio/ysac032

Workflow (paper Methods 2.3/2.4 and Results 3.2, Golden Gate path):

  1. PCR of 7 fragments (25 uL reactions, Q5 polymerase, 0.1 uM primers,
     0.5 ng linearized plasmid template) set up from a master mix in the
     pcr_plate, which stands in for the 100 uL PCR tubes. The OT-2
     thermocycler has no gradient capability, so cycling is done off-deck
     on a gradient thermocycler at the AssemblyTron/j5-computed annealing
     gradient (manual step).
  2. DpnI digestion of the PCR products to remove the methylated,
     template-derived plasmid DNA (paper recipe: 19 uL water + 5 uL
     rCutSmart + 1 uL DpnI; 37 C 30 min, 65 C 20 min).
  3. Column clean-up of every fragment (Zymo DNA Clean & Concentrator-5)
     to remove residual polymerase, which would otherwise fill in the
     BsaI sticky ends (manual step); eluates return to the PCR wells.
  4. Golden Gate assembly: cleaned fragments combined in volumes
     proportional to fragment length (roughly equimolar), 10X T4 ligase
     buffer, BsaI-HFv2 + T4 ligase mix, water to 20 uL; cycled in a
     thermocycler following Engler et al. (manual step).
  5. Clean-up of the assembly reactions, elution in 10 uL water (manual),
     and transformation of the whole eluate into 50 uL E. coli TOP10:
     30 min on ice, heat shock 42 C 60 s, recovery 60 min at 37 C with
     250 uL LB + 0.2% dextrose added by the robot.

Volumes/times not fixed by the paper are chosen below and flagged in
comments.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - four chromoprotein plasmids',
    'author': 'OT-2 protocol from Boehm et al. 2022 (doi:10.1093/synbio/ysac032)',
    'description': 'PCR of 7 fragments, DpnI digest, clean-up, four 20 uL '
                   'Golden Gate assemblies, clean-up, transformation into '
                   'TOP10 competent cells.',
    'apiLevel': '2.13',
}

# --------------------------------------------------------------------------
# Design tables (fixed by the j5/AssemblyTron output given in the task)
# --------------------------------------------------------------------------

# Fragment number -> (pcr_plate well, fwd primer, rev primer, template well)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1'),  # tsPurple chromoprotein
    2: ('B1', 'B1', 'B2', 'A1'),  # backbone
    3: ('C1', 'C1', 'C2', 'B1'),  # YukonOFP chromoprotein
    4: ('D1', 'D1', 'D2', 'C1'),  # aeBlue chromoprotein
    5: ('E1', 'E1', 'E2', 'A1'),  # backbone / KanR
    6: ('F1', 'F1', 'F2', 'A1'),  # backbone
    7: ('G1', 'G1', 'G2', 'D1'),  # fuGFP chromoprotein
}

# assembly_plate well -> {fragment number: volume (uL) of cleaned fragment}
# (volumes proportional to fragment length => roughly equimolar, paper 3.2)
ASSEMBLIES = {
    'A1': {2: 3.0, 5: 2.0, 6: 3.0, 1: 2.0},  # tsPurple construct
    'B1': {2: 3.0, 5: 2.0, 6: 3.0, 3: 2.0},  # YukonOFP construct
    'C1': {2: 3.0, 5: 2.0, 6: 3.0, 4: 2.0},  # aeBlue construct
    'D1': {2: 3.0, 5: 2.0, 6: 3.0, 7: 2.0},  # fuGFP construct
}

# --------------------------------------------------------------------------
# Reaction volumes derived from the paper (Methods 2.3)
# --------------------------------------------------------------------------
# PCR: 25 uL total per reaction, Q5, 0.1 uM primers, 0.5 ng template.
#   Per-reaction master mix (buffer + dNTP + polymerase + water) = 19 uL:
MM_WATER = 13.25      # water to 19 uL per reaction
MM_Q5_BUFFER = 5.0    # 5X Q5 reaction buffer -> 1X in 25 uL
MM_DNTP = 0.5         # 10 mM dNTPs -> 200 uM in 25 uL (Q5 standard)
MM_Q5_POL = 0.25      # Q5 polymerase, 0.5 uL/50 uL reaction scaled to 25 uL
# 0.25 uL is below the p20 minimum of 1 uL, which is exactly why the
# polymerase is pipetted through the master mix (8 reactions = 7 fragments
# + 1 spare/dead volume, as staged in tube D1): 8 x 0.25 = 2 uL.
MM_RXN_VOLUME = MM_WATER + MM_Q5_BUFFER + MM_DNTP + MM_Q5_POL   # = 19.0 uL
MM_REACTIONS = 8
PRIMER_VOLUME = 2.5   # 1 uM primer stock -> 0.1 uM in 25 uL (paper)
TEMPLATE_VOLUME = 1.0  # 0.5 ng/uL template -> 0.5 ng per reaction (paper)

# DpnI digestion of each PCR product, paper's recipe applied to one 25 uL
# PCR: +19 uL water, +5 uL rCutSmart (10X -> 1X in the resulting 50 uL),
# +1 uL DpnI; 37 C 30 min, then 65 C 20 min to inactivate.
DPNI_WATER = 19.0
DPNI_RCUTSMART = 5.0
DPNI_ENZYME = 1.0

# Column clean-up of fragments (manual). Fragments 2 and 6 are each used at
# 3 uL x 4 assemblies = 12 uL, so the paper's 10 uL elution would be too
# tight; elute in 20 uL water (volume chosen here, not fixed by the paper).
FRAGMENT_ELUTION = 20.0

# Golden Gate reaction, 20 uL total (fixed):
GG_T4_BUFFER = 2.0    # 10X T4 DNA ligase buffer -> 1X in 20 uL
GG_ENZYME_MIX = 1.0   # BsaI-HFv2 + T4 ligase premix. The paper does not
                      # fix the premix volume; 1 uL per 20 uL reaction is
                      # the standard usage for a combined Golden Gate
                      # enzyme mix (paper leaves this open -> our choice).
# fragments contribute 10.0 uL (3+2+3+2), so water makes up the balance:
GG_WATER = 20.0 - GG_T4_BUFFER - GG_ENZYME_MIX - 10.0   # = 7.0 uL

# Assembly clean-up elution: 10 uL water (paper Methods 2.3); the whole
# eluate is transformed into the 50 uL of cells (paper). The paper also
# NanoDrops a spare 5 uL for CFU/ug calculations; skipped here since the
# task ends at transformation (noted at the pause below).
ASSEMBLY_ELUTION = 10.0

# Recovery medium: 250 uL LB + 0.2% (w/v) dextrose (paper Methods 2.3).
LB_DEXTROSE_VOLUME = 250.0


def run(protocol: protocol_api.ProtocolContext):
    # ------------------------- labware & instruments ----------------------
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

    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tips300])

    # reagent locations
    water = tubes_50ml_1['A1']           # nuclease-free water
    q5_buffer = tubes_1_5ml_1['A1']      # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1['B1']           # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1['C1']         # Q5 High-Fidelity DNA Polymerase
    pcr_mm_tube = tubes_1_5ml_1['D1']    # empty -> PCR master mix made here
    rcutsmart = tubes_1_5ml_1['A2']      # rCutSmart Buffer (10X)
    dpni = tubes_1_5ml_1['B2']           # DpnI
    t4_buffer = tubes_1_5ml_1['C2']      # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']      # BsaI-HFv2 + T4 ligase mix
    lb_dextrose = tubes_15ml_1['A1']     # LB + 0.2% (w/v) dextrose

    pcr_wells = [pcr_plate[FRAGMENTS[n][0]] for n in sorted(FRAGMENTS)]
    assembly_wells = [assembly_plate[w] for w in sorted(ASSEMBLIES)]

    protocol.comment(
        'AssemblyTron Golden Gate run (Boehm et al. 2022): 7 fragment PCRs '
        '-> DpnI digest -> fragment clean-up -> four 20 uL Golden Gate '
        'assemblies (tsPurple, YukonOFP, aeBlue, fuGFP) -> assembly '
        'clean-up -> transformation of TOP10 cells in cells_plate A1:D1. '
        'Keep enzyme tubes on ice; plates stay on deck between manual steps '
        'unless stated otherwise.')

    # ======================================================================
    # STEP 1 - PCR master mix (8 reactions: 7 fragments + 1 spare)
    # ======================================================================
    protocol.comment(
        'STEP 1: preparing Q5 PCR master mix in tubes_1_5ml_1 D1 for 8 '
        'reactions (7 PCRs + 1 dead-volume spare): {w:.2f} uL water + '
        '{b:.0f} uL 5X Q5 buffer + {d:.1f} uL 10 mM dNTPs + {p:.1f} uL Q5 '
        'polymerase = {t:.0f} uL total ({mm:.1f} uL per reaction). '
        'Polymerase is added through the master mix because 0.25 uL per '
        '25 uL reaction is below the p20 pipetting range.'.format(
            w=MM_WATER * MM_REACTIONS, b=MM_Q5_BUFFER * MM_REACTIONS,
            d=MM_DNTP * MM_REACTIONS, p=MM_Q5_POL * MM_REACTIONS,
            t=MM_RXN_VOLUME * MM_REACTIONS, mm=MM_RXN_VOLUME))

    p300.transfer(MM_WATER * MM_REACTIONS, water, pcr_mm_tube)
    p300.transfer(MM_Q5_BUFFER * MM_REACTIONS, q5_buffer, pcr_mm_tube)
    p20.transfer(MM_DNTP * MM_REACTIONS, dntp, pcr_mm_tube)
    p20.transfer(MM_Q5_POL * MM_REACTIONS, q5_pol, pcr_mm_tube)
    # mix the master mix (last and largest component volume: use p300)
    p300.pick_up_tip()
    p300.mix(5, 100.0, pcr_mm_tube)
    p300.drop_tip()

    # ======================================================================
    # STEP 2 - set up the 7 PCRs in pcr_plate A1:G1 (25 uL each)
    # ======================================================================
    protocol.comment(
        'STEP 2: setting up 7 x 25 uL PCRs in pcr_plate A1:G1: {mm:.1f} uL '
        'master mix + {fp:.1f} uL forward primer + {rp:.1f} uL reverse '
        'primer (1 uM stocks -> 0.1 uM final, paper 2.3) + {tpl:.1f} uL '
        'linearized template (0.5 ng/uL -> 0.5 ng, paper 2.3).'.format(
            mm=MM_RXN_VOLUME, fp=PRIMER_VOLUME, rp=PRIMER_VOLUME,
            tpl=TEMPLATE_VOLUME))

    # master mix: 19 uL per well is below the p300 20 uL minimum, so the
    # p20 (1-20 uL range) dispenses it; a single tip suffices since the tip
    # only ever carries master mix.
    p20.transfer(MM_RXN_VOLUME, pcr_mm_tube, pcr_wells, new_tip='once')

    for n in sorted(FRAGMENTS):
        pcr_well, fwd, rev, tpl = FRAGMENTS[n]
        p20.transfer(PRIMER_VOLUME, primer_plate[fwd],
                     pcr_plate[pcr_well], new_tip='always')
        p20.transfer(PRIMER_VOLUME, primer_plate[rev],
                     pcr_plate[pcr_well], new_tip='always')

    # templates: fresh tip per fragment (template A1 is shared by
    # fragments 1, 2, 5 and 6 - no carry-over of DNA between PCRs)
    for n in sorted(FRAGMENTS):
        pcr_well, fwd, rev, tpl = FRAGMENTS[n]
        p20.transfer(TEMPLATE_VOLUME, template_plate[tpl],
                     pcr_plate[pcr_well], new_tip='always')

    # mix each completed PCR
    for well in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15.0, well)
        p20.drop_tip()

    # ------------------ manual: gradient PCR (off deck) -------------------
    protocol.comment(
        'MANUAL STEP - PCR (off-deck gradient thermocycler, e.g. Bio-Rad '
        'C100; the OT-2 thermocycler has no gradient capability, paper '
        '3.1): seal pcr_plate, transfer it to the gradient thermocycler at '
        'the block positions/annealing-temperature gradient computed by '
        'AssemblyTron (each fragment within 0.4 C of its j5 annealing Tm), '
        'and run: 98 C 30 s initial denaturation; 34 cycles of [98 C 10 s; '
        'annealing 30 s at the gradient temperature for that fragment; '
        '72 C extension at 20-30 s/kb for Q5 - use 90 s here, sized for '
        'the longest backbone fragment]; final extension 72 C 5 min; hold '
        '4 C. (Paper uses 34 or 36 cycles; 34 chosen.) Optionally remove '
        'a small sample of each reaction for agarose gel QC (paper 3.2). '
        'Return the UNSEALED pcr_plate to deck slot 5 and resume.')
    protocol.pause('Run the gradient PCR off-deck, then return pcr_plate to '
                   'slot 5 and resume.')

    # ======================================================================
    # STEP 3 - DpnI digestion of the PCR products (paper 2.3 recipe)
    # ======================================================================
    protocol.comment(
        'STEP 3: DpnI digest to destroy the methylated plasmid template '
        'carried over from the PCRs: adding {w:.0f} uL water + {b:.0f} uL '
        'rCutSmart (10X -> 1X in the resulting 50 uL) + {e:.0f} uL DpnI to '
        'each 25 uL PCR in pcr_plate A1:G1.'.format(
            w=DPNI_WATER, b=DPNI_RCUTSMART, e=DPNI_ENZYME))

    p20.transfer(DPNI_WATER, water, pcr_wells, new_tip='once')
    p20.transfer(DPNI_RCUTSMART, rcutsmart, pcr_wells, new_tip='once')
    p20.transfer(DPNI_ENZYME, dpni, pcr_wells, new_tip='once')

    for well in pcr_wells:
        p300.pick_up_tip()
        p300.mix(3, 30.0, well)
        p300.drop_tip()

    # ---------------- manual: DpnI incubation (off deck) ------------------
    protocol.comment(
        'MANUAL STEP - DpnI digestion (paper 2.3): seal pcr_plate and '
        'incubate in a thermocycler at 37 C for 30 min, then deactivate '
        'DpnI at 65 C for 20 min. Unseal and return the plate to deck '
        'slot 5.')
    protocol.pause('Incubate pcr_plate: 37 C 30 min, then 65 C 20 min; '
                   'return to slot 5 and resume.')

    # ---------------- manual: fragment clean-up (columns) -----------------
    protocol.comment(
        'MANUAL STEP - fragment clean-up (paper 3.2: residual polymerase '
        'fills in the BsaI sticky ends and must be removed before '
        'assembly): clean and concentrate EACH of the 7 digested fragments '
        '(50 uL each in pcr_plate A1:G1) on a Zymo DNA Clean & '
        'Concentrator-5 column (add 5 volumes DNA Binding Buffer, load, '
        'wash twice with 200 uL DNA Wash Buffer, then elute with {el:.0f} '
        'uL nuclease-free water). Elute in {el:.0f} uL rather than the '
        'paper\'s 10 uL final-assembly elution because shared fragments '
        'need up to 12 uL (3 uL x 4 assemblies) plus pipetting dead '
        'volume - our choice where the paper leaves fragment elution open. '
        'Return each eluate to its ORIGINAL pcr_plate well (fragment 1 -> '
        'A1, 2 -> B1, 3 -> C1, 4 -> D1, 5 -> E1, 6 -> F1, 7 -> G1).'.format(
            el=FRAGMENT_ELUTION))
    protocol.pause('Column-purify the 7 fragments, elute each in 20 uL '
                   'water back into its pcr_plate well, and resume.')

    # ======================================================================
    # STEP 4 - Golden Gate assembly set-up in assembly_plate A1:D1 (20 uL)
    # ======================================================================
    protocol.comment(
        'STEP 4: setting up four 20 uL Golden Gate reactions in '
        'assembly_plate A1 (tsPurple), B1 (YukonOFP), C1 (aeBlue), D1 '
        '(fuGFP): {w:.1f} uL water + {b:.1f} uL 10X T4 ligase buffer + '
        'cleaned fragments in length-proportional volumes (3+2+3+2 = '
        '10 uL; backbone fragments 2/5/6 shared by all four constructs, '
        'plus one chromoprotein fragment each) + {e:.1f} uL BsaI-HFv2/T4 '
        'ligase mix added last to start the reactions.'.format(
            w=GG_WATER, b=GG_T4_BUFFER, e=GG_ENZYME_MIX))

    p20.transfer(GG_WATER, water, assembly_wells, new_tip='once')
    p20.transfer(GG_T4_BUFFER, t4_buffer, assembly_wells, new_tip='once')

    # shared backbone fragments: one tip per fragment source is safe - the
    # tip only ever contacts that one fragment plus wells that all receive
    # it. (fragment 2: 3 uL, fragment 5: 2 uL, fragment 6: 3 uL per well)
    for frag_n in (2, 5, 6):
        src = pcr_plate[FRAGMENTS[frag_n][0]]
        vol = ASSEMBLIES['A1'][frag_n]  # identical across the 4 assemblies
        p20.transfer(vol, src, assembly_wells, new_tip='once')

    # chromoprotein fragment: different source per assembly -> fresh tip
    # each time; volumes are identical (2 uL) across assemblies.
    for asm_well, frags in ASSEMBLIES.items():
        chromo = [n for n in frags if n not in (2, 5, 6)][0]
        p20.transfer(frags[chromo], pcr_plate[FRAGMENTS[chromo][0]],
                     assembly_plate[asm_well], new_tip='always')

    # enzyme mix last (starts the digestion/ligation cycling), then mix;
    # fresh tip per well since mix_after re-enters each reaction
    p20.transfer(GG_ENZYME_MIX, gg_enzyme, assembly_wells,
                 new_tip='always', mix_after=(3, 15.0))

    # ---------------- manual: Golden Gate cycling -------------------------
    protocol.comment(
        'MANUAL STEP - Golden Gate thermocycling (paper 3.2, based on '
        'Engler et al.): seal assembly_plate A1:D1 and seat it on the '
        'Opentrons thermocycler module (or move it to any thermocycler if '
        'no module is available - the protocol pauses either way). Run '
        'with a heated lid: 30 cycles of [37 C 5 min (BsaI digestion); '
        '16 C 5 min (T4 ligation)]; final 37 C 15 min to drive assembly '
        'to completion; 60 C 5 min to heat-inactivate; hold 4 C. (Cycle '
        'count/lengths follow the Engler one-pot protocol the paper '
        'cites; the paper does not print the program.) Return/seal the '
        'plate in deck slot 6 when done.')
    protocol.pause('Run the Golden Gate cycling program on assembly_plate, '
                   'then resume.')

    # ---------------- manual: assembly clean-up (columns) -----------------
    protocol.comment(
        'MANUAL STEP - assembly clean-up (paper 2.3): clean and '
        'concentrate each 20 uL Golden Gate reaction on a Zymo DNA Clean & '
        'Concentrator-5 column and elute with {el:.0f} uL molecular-grade '
        'water. Return each eluate to its assembly_plate well (A1:D1). '
        'The paper NanoDrops a spare 5 uL of eluate to compute CFU/ug '
        'transformation efficiencies; skipped here since this run ends at '
        'transformation and the whole 10 uL eluate is transformed.'.format(
            el=ASSEMBLY_ELUTION))
    protocol.pause('Column-purify the 4 assemblies, elute each in 10 uL '
                   'water back into assembly_plate A1:D1, and resume.')

    # ======================================================================
    # STEP 5 - transformation into E. coli TOP10 (cells_plate A1:D1)
    # ======================================================================
    protocol.comment(
        'STEP 5: adding each {el:.0f} uL cleaned assembly eluate to 50 uL '
        'of TOP10 chemically competent cells (Hanahan method) in '
        'cells_plate A1 (tsPurple), B1 (YukonOFP), C1 (aeBlue), D1 '
        '(fuGFP), with a gentle 2x mix.'.format(el=ASSEMBLY_ELUTION))

    p20.transfer(ASSEMBLY_ELUTION,
                 [assembly_plate[w] for w in sorted(ASSEMBLIES)],
                 [cells_plate[w] for w in sorted(ASSEMBLIES)],
                 new_tip='always', mix_after=(2, 10.0))

    # ---------------- manual: ice incubation + heat shock -----------------
    protocol.comment(
        'MANUAL STEP - transformation (paper 2.3): incubate the cells on '
        'ice for 30 min, heat-shock at 42 C for exactly 60 s (heat block '
        'or water bath; cannot be done on-deck), then return the plate to '
        'ice briefly. Bring cells_plate back to deck slot 7 and resume so '
        'the robot can add recovery medium.')
    protocol.pause('Incubate 30 min on ice, heat shock 42 C 60 s, return '
                   'cells_plate to slot 7 and resume.')

    # recovery medium, added by the robot (paper 2.3: 250 uL LB + 0.2%
    # dextrose; 250 uL fits the p300 and keeps the 360 uL wells < capacity)
    protocol.comment(
        'Adding {v:.0f} uL LB + 0.2% (w/v) dextrose recovery medium from '
        'tubes_15ml_1 A1 to each transformation well.'.format(
            v=LB_DEXTROSE_VOLUME))
    p300.transfer(LB_DEXTROSE_VOLUME, lb_dextrose,
                  [cells_plate[w] for w in sorted(ASSEMBLIES)],
                  new_tip='always', mix_after=(3, 200.0))

    # ---------------- manual: outgrowth recovery --------------------------
    protocol.comment(
        'MANUAL STEP - recovery (paper 2.3): incubate the transformation '
        'mixes at 37 C for 60 min with shaking/aeration to allow '
        'kanamycin-resistance expression.')
    protocol.pause('Recover cells at 37 C for 60 min, then resume to end '
                   'the robot run.')

    # ---------------- manual: plating (end of robot work) -----------------
    protocol.comment(
        'MANUAL STEP - plating and scoring (paper 2.3/3.2): plate 50-200 '
        'uL of each recovery (neat or as a 10x dilution, depending on '
        'expected efficiency; the paper saw 300-800 colonies per assembly) '
        'onto LB agar with kanamycin 50 ug/mL - all four constructs carry '
        'the KanR fragment 5. Incubate at 37 C overnight, then count '
        'colonies and score chromoprotein colour: A1 purple (tsPurple), '
        'B1 orange (YukonOFP), C1 blue (aeBlue), D1 green (fuGFP); >98% '
        'of colonies are expected to show the correct colour.')
    protocol.comment(
        'Robot work complete. Intermediates left on deck: spare PCR master '
        'mix in tubes_1_5ml_1 D1, unused primer/template stocks, and '
        'fragment leftovers in pcr_plate A1:G1 for re-use or archiving.')
