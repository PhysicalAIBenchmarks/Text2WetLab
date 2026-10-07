"""
Golden Gate assembly of four four-fragment chromoprotein expression plasmids
on an Opentrons OT-2, following the AssemblyTron workflow.

Reference
---------
Bryant J.A. et al. "AssemblyTron: flexible automation of DNA assembly with
Opentrons OT-2 lab robots." Synthetic Biology 7(1), 2022.
doi:10.1093/synbio/ysac032  (CC BY 4.0)

Workflow implemented (paper sections 2.3, 2.4 and 3.2)
------------------------------------------------------
  1. Build a Q5 PCR master mix (buffer, dNTPs, polymerase, water) for 8 rxns.
  2. Set up seven 25 uL PCRs (one per j5 fragment) with 0.1 uM primers and
     0.5 ng linearized plasmid template.
  3. PAUSE -> operator seals the plate and runs the gradient PCR on an
     external gradient thermocycler (the OT-2 thermocycler module has no
     gradient capability, see paper section 3.1).
  4. DpnI digestion of residual template: add 19 uL water, 5 uL rCutSmart
     Buffer and 1 uL DpnI to each 25 uL reaction, then 30 min at 37 C and
     20 min at 65 C off deck.
  5. PAUSE -> operator column-cleans each fragment (polymerase interferes
     with Golden Gate) and returns the eluates to the same wells.
  6. Assemble four 20 uL Golden Gate reactions, each from four fragments at a
     volume proportional to fragment length (roughly equimolar).
  7. PAUSE -> Golden Gate thermocycling (BsaI-HFv2 / T4 ligase).
  8. PAUSE -> clean and concentrate each assembly, elute in 10 uL water.
  9. Transform 5 uL of each eluate into 50 uL TOP10 chemically competent
     cells; 30 min on ice, 42 C / 60 s heat shock, add 250 uL LB + 0.2%
     dextrose, recover 60 min at 37 C, then plate.

Everything the OT-2 cannot do itself (sealing, thermocycling, ice baths, heat
shock, spin-column clean-ups, plating) is recorded with protocol.comment()
and a protocol.pause() at the point in the run where it happens.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - 4x four-fragment chromoprotein plasmids',
    'author': 'Automated from Bryant et al. 2022, Synth. Biol. 7:ysac032',
    'description': (
        'PCR of 7 fragments, DpnI digestion, Golden Gate assembly of 4 plasmids '
        'and transformation into E. coli TOP10, per the AssemblyTron workflow.'
    ),
    'apiLevel': '2.13',
}


# ---------------------------------------------------------------------------
# Reaction recipes
# ---------------------------------------------------------------------------
# PCR: 25 uL, Q5 High-Fidelity, 0.1 uM each primer, 0.5 ng linear template
# (paper section 2.3). Primer stocks are 1 uM and template stocks 0.5 ng/uL,
# so 2.5 uL of each primer and 1.0 uL of template per reaction.
PCR_RXN_VOL = 25.0
PRIMER_VOL = 2.5          # 2.5 uL of 1 uM stock in 25 uL -> 0.1 uM final
TEMPLATE_VOL = 1.0        # 1.0 uL of 0.5 ng/uL stock -> 0.5 ng template

# Per-reaction master-mix components. Buffer/dNTP/polymerase are the standard
# NEB Q5 amounts (1X buffer, 200 uM each dNTP, 0.02 U/uL Q5); the paper does
# not restate them, so NEB's Q5 recommendation is used. Water makes up the
# volume not contributed by the primers and template.
Q5_BUFFER_PER_RXN = 5.00      # 5X buffer -> 1X
DNTP_PER_RXN = 0.50           # 10 mM each -> 200 uM each
Q5_POL_PER_RXN = 0.25         # 2 U/uL -> 0.02 U/uL
WATER_PER_RXN = (
    PCR_RXN_VOL - (2 * PRIMER_VOL) - TEMPLATE_VOL
    - Q5_BUFFER_PER_RXN - DNTP_PER_RXN - Q5_POL_PER_RXN
)                             # = 13.25 uL
MM_PER_RXN = Q5_BUFFER_PER_RXN + DNTP_PER_RXN + Q5_POL_PER_RXN + WATER_PER_RXN
# = 19.0 uL of master mix per reaction, 19 + 2.5 + 2.5 + 1 = 25 uL total.

# Master mix is made for 8 reactions (7 fragments + 1 reaction of overage) so
# that the 7 aliquots can be drawn without running the tube dry.
MM_RXNS = 8

# DpnI template digestion, added straight to each finished 25 uL PCR
# (paper section 2.3): 19 uL water + 5 uL rCutSmart + 1 uL DpnI -> 50 uL.
DPNI_WATER_VOL = 19.0
RCUTSMART_VOL = 5.0
DPNI_VOL = 1.0

# Golden Gate reaction, 20 uL total (NEB Golden Gate Assembly Kit conditions,
# the protocol of Engler et al. that the AssemblyTron script is based on):
# 10 uL of fragments + 2 uL 10X T4 ligase buffer + 1 uL enzyme mix + water.
GG_RXN_VOL = 20.0
T4_BUFFER_VOL = 2.0
GG_ENZYME_VOL = 1.0

# Spin-column elution volume for each cleaned PCR fragment. The paper does not
# state it for the fragment clean-ups (only the 10 uL elution of the finished
# assemblies). Backbone fragments 2 and 6 are each consumed by all four
# assemblies at 3 uL, i.e. 12 uL, so 20 uL is chosen: enough for every
# assembly plus pipetting dead volume.
FRAGMENT_ELUTION_VOL = 20.0

# Clean-and-concentrate elution of each finished assembly (paper section 2.3):
# 10 uL of water, of which 5 uL is transformed and 5 uL kept for NanoDrop
# quantification of transformation efficiency.
ASSEMBLY_ELUTION_VOL = 10.0
DNA_INTO_CELLS_VOL = 5.0
CELLS_VOL = 50.0
RECOVERY_LB_VOL = 250.0

# --- j5 / AssemblyTron fragment table -------------------------------------
# (fragment label, pcr_plate well, fwd primer well, rev primer well, template well)
FRAGMENTS = [
    ('1 tsPurple chromoprotein', 'A1', 'A1', 'A2', 'A1'),
    ('2 backbone',               'B1', 'B1', 'B2', 'A1'),
    ('3 YukonOFP chromoprotein', 'C1', 'C1', 'C2', 'B1'),
    ('4 aeBlue chromoprotein',   'D1', 'D1', 'D2', 'C1'),
    ('5 backbone / KanR',        'E1', 'E1', 'E2', 'A1'),
    ('6 backbone',               'F1', 'F1', 'F2', 'A1'),
    ('7 fuGFP chromoprotein',    'G1', 'G1', 'G2', 'D1'),
]

# --- j5 / AssemblyTron assembly table -------------------------------------
# Volume of each cleaned fragment is proportional to its length, which gives a
# roughly equimolar mix assuming equal PCR yields (paper section 3.2).
# (assembly well, plasmid name, [(pcr_plate well of fragment, volume uL), ...])
ASSEMBLIES = [
    ('A1', 'tsPurple',  [('B1', 3.0), ('E1', 2.0), ('F1', 3.0), ('A1', 2.0)]),
    ('B1', 'YukonOFP',  [('B1', 3.0), ('E1', 2.0), ('F1', 3.0), ('C1', 2.0)]),
    ('C1', 'aeBlue',    [('B1', 3.0), ('E1', 2.0), ('F1', 3.0), ('D1', 2.0)]),
    ('D1', 'fuGFP',     [('B1', 3.0), ('E1', 2.0), ('F1', 3.0), ('G1', 2.0)]),
]

# Transformations: assembly well -> competent-cell well
TRANSFORMATIONS = [('A1', 'A1'), ('B1', 'B1'), ('C1', 'C1'), ('D1', 'D1')]


def run(protocol: protocol_api.ProtocolContext):

    # ----------------------------------------------------------------- deck
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
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    # ------------------------------------------------------------- reagents
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']          # empty at the start, built below
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']
    lb_dextrose = tubes_15ml_1['A1']

    # ------------------------------------------------- tip bookkeeping ----
    # Tips are unlimited: each rack is reset once all 96 of its tips are used,
    # so the run never stops for tips and no pipette ever moves without one.
    tips_used = {'p20': 0, 'p300': 0}

    def pick_up(pipette):
        key = 'p20' if pipette is p20 else 'p300'
        if tips_used[key] >= 96:
            pipette.reset_tipracks()
            tips_used[key] = 0
            protocol.comment(
                'Replace the used {} tip rack with a fresh one before '
                'continuing.'.format(key))
        pipette.pick_up_tip()
        tips_used[key] += 1

    def pipette_for(volume):
        """20 uL pipette handles 1-20 uL, 300 uL pipette handles 20-300 uL."""
        return p20 if volume <= 20.0 else p300

    def as_well(target):
        """Accept either a Well or a Location and return the parent Well."""
        return getattr(target, 'labware', target).as_well() \
            if hasattr(target, 'labware') else target

    def move(volume, source, dest, mix_after=None, blow_out_in_dest=True):
        """Single clean-tip transfer; always picks up and drops a tip."""
        pipette = pipette_for(volume)
        dest_well = as_well(dest)
        pick_up(pipette)
        pipette.aspirate(volume, source)
        pipette.dispense(volume, dest)
        if mix_after is not None:
            reps, mix_vol = mix_after
            pipette.mix(reps, mix_vol, dest)
        if blow_out_in_dest:
            pipette.blow_out(dest_well.top(-2))
        pipette.drop_tip()

    # =====================================================================
    # Step 1 - Q5 PCR master mix for 8 reactions, built in tubes_1_5ml_1 D1
    # =====================================================================
    protocol.comment(
        'STEP 1: building the Q5 PCR master mix for {} reactions in '
        'tubes_1_5ml_1 D1 (pcr_mm).'.format(MM_RXNS))

    mm_water = WATER_PER_RXN * MM_RXNS            # 106.0 uL
    mm_buffer = Q5_BUFFER_PER_RXN * MM_RXNS       #  40.0 uL
    mm_dntp = DNTP_PER_RXN * MM_RXNS              #   4.0 uL
    mm_pol = Q5_POL_PER_RXN * MM_RXNS             #   2.0 uL

    # Water first so the small enzyme/dNTP volumes are diluted on contact.
    move(mm_water, water, pcr_mm, blow_out_in_dest=True)
    move(mm_buffer, q5_buffer, pcr_mm, blow_out_in_dest=True)
    move(mm_dntp, dntp, pcr_mm, blow_out_in_dest=True)
    # Polymerase is added last and mixed in gently (glycerol stock).
    move(mm_pol, q5_pol, pcr_mm, mix_after=(8, 15), blow_out_in_dest=True)

    protocol.comment(
        'PCR master mix complete: {:.1f} uL water, {:.1f} uL 5X Q5 buffer, '
        '{:.1f} uL 10 mM dNTPs, {:.1f} uL Q5 polymerase '
        '= {:.1f} uL total ({:.2f} uL per reaction).'.format(
            mm_water, mm_buffer, mm_dntp, mm_pol,
            mm_water + mm_buffer + mm_dntp + mm_pol, MM_PER_RXN))

    # =====================================================================
    # Step 2 - seven 25 uL PCRs, one per j5 fragment
    # =====================================================================
    protocol.comment(
        'STEP 2: setting up {} PCRs of {:.0f} uL in pcr_plate column 1.'.format(
            len(FRAGMENTS), PCR_RXN_VOL))

    # Master mix into every PCR well. One tip is enough: a single clean source
    # dispensed into empty wells, with no contact between tip and well contents.
    pick_up(p20)
    for label, pcr_well, _fwd, _rev, _templ in FRAGMENTS:
        p20.aspirate(MM_PER_RXN, pcr_mm)
        p20.dispense(MM_PER_RXN, pcr_plate[pcr_well].bottom(2))
        p20.blow_out(pcr_plate[pcr_well].top(-2))
    p20.drop_tip()

    # Primers and template get a fresh tip each to avoid any cross-contamination.
    for label, pcr_well, fwd, rev, templ in FRAGMENTS:
        protocol.comment(
            'Fragment {}: pcr_plate {} <- {:.1f} uL master mix, {:.1f} uL fwd '
            'primer {}, {:.1f} uL rev primer {}, {:.1f} uL template {}.'.format(
                label, pcr_well, MM_PER_RXN, PRIMER_VOL, fwd, PRIMER_VOL, rev,
                TEMPLATE_VOL, templ))
        move(PRIMER_VOL, primer_plate[fwd], pcr_plate[pcr_well].bottom(2))
        move(PRIMER_VOL, primer_plate[rev], pcr_plate[pcr_well].bottom(2))
        move(TEMPLATE_VOL, template_plate[templ], pcr_plate[pcr_well].bottom(2),
             mix_after=(5, 15))

    # =====================================================================
    # Step 3 - OFF DECK: gradient PCR
    # =====================================================================
    protocol.comment('STEP 3 (off deck): gradient thermocycling.')
    protocol.comment(
        'OPERATOR: seal pcr_plate, spin it down briefly, transfer the seven '
        '25 uL reactions to the external gradient thermocycler in the tube '
        'positions given by AssemblyTron. The OT-2 thermocycler module has no '
        'gradient capability, so this step cannot be automated.')
    protocol.comment(
        'Cycling (paper section 2.3): 98 C for 30 s; then 34 cycles of 98 C '
        'for 10 s, 30 s at the AssemblyTron/j5 annealing gradient, and 72 C '
        'for the AssemblyTron extension time; then 72 C for 5 min; hold 4 C.')
    protocol.comment(
        'Assumption, since the paper gives no fragment lengths or primer Tms '
        'for this build: a 60-72 C annealing gradient across the block (each '
        'fragment within 0.4 C of its optimum, as the AssemblyTron algorithm '
        'guarantees) and a 30 s/kb Q5 extension set by the longest fragment.')
    protocol.comment(
        'OPERATOR: run a sample of each reaction on a gel to confirm a single '
        'product of the expected length, then return pcr_plate to slot 5 '
        'unsealed, with every fragment back in its original well.')
    protocol.pause(
        'Gradient PCR off deck. Return pcr_plate to slot 5 (fragments in '
        'A1-G1) and resume.')

    # =====================================================================
    # Step 4 - DpnI digestion of residual plasmid template
    # =====================================================================
    protocol.comment(
        'STEP 4: DpnI digestion. Adding {:.0f} uL water, {:.0f} uL rCutSmart '
        'Buffer and {:.0f} uL DpnI to each {:.0f} uL PCR -> {:.0f} uL.'.format(
            DPNI_WATER_VOL, RCUTSMART_VOL, DPNI_VOL, PCR_RXN_VOL,
            PCR_RXN_VOL + DPNI_WATER_VOL + RCUTSMART_VOL + DPNI_VOL))

    for label, pcr_well, _fwd, _rev, _templ in FRAGMENTS:
        dest = pcr_plate[pcr_well]
        move(DPNI_WATER_VOL, water, dest.bottom(2))
        move(RCUTSMART_VOL, rcutsmart, dest.bottom(2))
        move(DPNI_VOL, dpni, dest.bottom(2), mix_after=(5, 18))

    protocol.comment('STEP 4 (off deck): DpnI incubation.')
    protocol.comment(
        'OPERATOR: seal pcr_plate and incubate 30 min at 37 C, then '
        'heat-inactivate 20 min at 65 C (paper section 2.3).')
    protocol.pause(
        'DpnI digestion: 30 min at 37 C then 20 min at 65 C off deck. '
        'Return pcr_plate to slot 5 and resume.')

    # =====================================================================
    # Step 5 - OFF DECK: column clean-up of each fragment
    # =====================================================================
    protocol.comment('STEP 5 (off deck): fragment clean-up.')
    protocol.comment(
        'OPERATOR: clean and concentrate each of the seven digested fragments '
        'on a DNA Clean and Concentrator-5 column (Zymo). Residual polymerase '
        'interferes with Golden Gate assembly, so this clean-up is required '
        '(paper section 3.2).')
    protocol.comment(
        'Elute each fragment in {:.0f} uL nuclease-free water and return it to '
        'its own pcr_plate well (fragment 1 -> A1 ... fragment 7 -> G1). '
        '{:.0f} uL is chosen because backbone fragments 2 and 6 are each used '
        'by all four assemblies at 3 uL, so 12 uL is consumed plus dead '
        'volume; the paper does not specify this elution volume.'.format(
            FRAGMENT_ELUTION_VOL, FRAGMENT_ELUTION_VOL))
    protocol.pause(
        'Clean up the seven fragments, elute each in {:.0f} uL water, return '
        'them to pcr_plate A1-G1 in slot 5, and resume.'.format(
            FRAGMENT_ELUTION_VOL))

    # =====================================================================
    # Step 6 - four 20 uL Golden Gate reactions
    # =====================================================================
    protocol.comment(
        'STEP 6: setting up {} Golden Gate reactions of {:.0f} uL in '
        'assembly_plate column 1.'.format(len(ASSEMBLIES), GG_RXN_VOL))

    # Water first, into empty wells, so one tip is safe for all four.
    pick_up(p20)
    for well, name, frags in ASSEMBLIES:
        frag_total = sum(v for _w, v in frags)
        gg_water = GG_RXN_VOL - frag_total - T4_BUFFER_VOL - GG_ENZYME_VOL
        p20.aspirate(gg_water, water)
        p20.dispense(gg_water, assembly_plate[well].bottom(2))
        p20.blow_out(assembly_plate[well].top(-2))
    p20.drop_tip()

    for well, name, frags in ASSEMBLIES:
        frag_total = sum(v for _w, v in frags)
        gg_water = GG_RXN_VOL - frag_total - T4_BUFFER_VOL - GG_ENZYME_VOL
        protocol.comment(
            'Assembly {} ({}): {:.1f} uL water, {:.1f} uL 10X T4 ligase '
            'buffer, {} and {:.1f} uL Golden Gate Enzyme Mix = {:.0f} uL.'.format(
                well, name, gg_water, T4_BUFFER_VOL,
                ', '.join('{:.1f} uL of pcr_plate {}'.format(v, w)
                          for w, v in frags),
                GG_ENZYME_VOL, GG_RXN_VOL))
        move(T4_BUFFER_VOL, t4_buffer, assembly_plate[well].bottom(2))
        for frag_well, frag_vol in frags:
            move(frag_vol, pcr_plate[frag_well], assembly_plate[well].bottom(2))
        # Enzyme mix last, then mix the complete reaction.
        move(GG_ENZYME_VOL, gg_enzyme, assembly_plate[well].bottom(2),
             mix_after=(6, 15))

    # =====================================================================
    # Step 7 - OFF DECK: Golden Gate thermocycling
    # =====================================================================
    protocol.comment('STEP 7 (off deck): Golden Gate thermocycling.')
    protocol.comment(
        'OPERATOR: seal assembly_plate, spin it down and run the Golden Gate '
        'cycling. The paper runs this on the Opentrons thermocycler module, '
        'but no thermocycler module is loaded on this deck, so the protocol '
        'pauses for transfer exactly as the AssemblyTron script allows.')
    protocol.comment(
        'Cycling (BsaI-HFv2 + T4 ligase, four-insert conditions of Engler et '
        'al. as used by AssemblyTron; the paper cites the method rather than '
        'restating it): 30 cycles of 37 C for 1 min and 16 C for 1 min, then '
        '60 C for 5 min, then hold at 4 C.')
    protocol.pause(
        'Golden Gate thermocycling off deck. Return assembly_plate to slot 6 '
        'and resume.')

    # =====================================================================
    # Step 8 - OFF DECK: clean and concentrate the assemblies
    # =====================================================================
    protocol.comment('STEP 8 (off deck): assembly clean-up.')
    protocol.comment(
        'OPERATOR: clean and concentrate each of the four finished assemblies '
        'on a DNA Clean and Concentrator-5 column (Zymo) and elute in '
        '{:.0f} uL molecular-grade water (paper section 2.3). Return each '
        'eluate to its own assembly_plate well (A1-D1).'.format(
            ASSEMBLY_ELUTION_VOL))
    protocol.comment(
        'Of the {:.0f} uL eluate the robot transforms {:.0f} uL; keep the '
        'remaining {:.0f} uL for NanoDrop quantification so transformation '
        'efficiency can be reported as CFU/ug.'.format(
            ASSEMBLY_ELUTION_VOL, DNA_INTO_CELLS_VOL,
            ASSEMBLY_ELUTION_VOL - DNA_INTO_CELLS_VOL))
    protocol.comment(
        'OPERATOR: make sure cells_plate A1-D1 still holds {:.0f} uL of '
        'ice-cold TOP10 competent cells and place the plate on a chilled '
        'block in slot 7 before resuming.'.format(CELLS_VOL))
    protocol.pause(
        'Clean up the four assemblies, elute each in {:.0f} uL water, return '
        'assembly_plate to slot 6 with chilled competent cells in slot 7, and '
        'resume.'.format(ASSEMBLY_ELUTION_VOL))

    # =====================================================================
    # Step 9 - transformation into E. coli TOP10
    # =====================================================================
    protocol.comment(
        'STEP 9: adding {:.0f} uL of each cleaned assembly to {:.0f} uL of '
        'TOP10 chemically competent cells.'.format(
            DNA_INTO_CELLS_VOL, CELLS_VOL))

    for asm_well, cell_well in TRANSFORMATIONS:
        name = next(n for w, n, _f in ASSEMBLIES if w == asm_well)
        protocol.comment(
            '{}: {:.0f} uL from assembly_plate {} -> cells_plate {}.'.format(
                name, DNA_INTO_CELLS_VOL, asm_well, cell_well))
        # Dispensed near the surface and stirred gently: competent cells are
        # shear sensitive, so no vigorous mixing.
        pick_up(p20)
        p20.aspirate(DNA_INTO_CELLS_VOL, assembly_plate[asm_well])
        p20.dispense(DNA_INTO_CELLS_VOL, cells_plate[cell_well].bottom(3))
        p20.mix(3, 15, cells_plate[cell_well].bottom(2), rate=0.5)
        p20.blow_out(cells_plate[cell_well].top(-2))
        p20.drop_tip()

    protocol.comment('STEP 9 (off deck): ice incubation and heat shock.')
    protocol.comment(
        'OPERATOR: incubate the four transformation mixes 30 min on ice, heat '
        'shock 60 s at 42 C, then return them to ice for 2 min and place '
        'cells_plate back in slot 7. The 2 min back on ice is standard '
        'practice; the paper does not state it (paper section 2.3).')
    protocol.pause(
        '30 min on ice, 60 s at 42 C, 2 min on ice. Return cells_plate to '
        'slot 7 and resume so the robot can add recovery medium.')

    protocol.comment(
        'STEP 9: adding {:.0f} uL LB + 0.2% (w/v) dextrose to each '
        'transformation for recovery.'.format(RECOVERY_LB_VOL))
    for _asm_well, cell_well in TRANSFORMATIONS:
        pick_up(p300)
        p300.aspirate(RECOVERY_LB_VOL, lb_dextrose)
        p300.dispense(RECOVERY_LB_VOL, cells_plate[cell_well].bottom(3))
        p300.mix(3, 150, cells_plate[cell_well].bottom(2), rate=0.5)
        p300.blow_out(cells_plate[cell_well].top(-2))
        p300.drop_tip()

    # =====================================================================
    # Step 10 - OFF DECK: recovery and plating
    # =====================================================================
    protocol.comment('STEP 10 (off deck): recovery and plating.')
    protocol.comment(
        'OPERATOR: recover the four transformations 60 min at 37 C with '
        'shaking (paper section 2.3).')
    protocol.comment(
        'OPERATOR: plate 50-200 uL of each recovery, or of a 10x dilution, on '
        'LB agar containing kanamycin (fragment 5 carries the KanR marker) '
        'and incubate overnight at 37 C.')
    protocol.comment(
        'OPERATOR: score colonies by chromoprotein colour, count CFU/ug of '
        'assembly DNA using the NanoDrop reading from step 8, and confirm the '
        'four plasmids by Sanger or whole-plasmid sequencing.')
    protocol.comment(
        'Expected result (paper section 3.2): 300-800 colonies per assembly, '
        'about 1e4 CFU/ug, with over 98% of colonies chromoprotein positive.')
    protocol.pause(
        'Recover 60 min at 37 C, then plate on LB + kanamycin. End of the '
        'OT-2 run: collect assembly_plate and the leftover fragments.')

    protocol.comment('Protocol complete. No pipette is holding a tip.')
