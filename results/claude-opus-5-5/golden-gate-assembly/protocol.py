"""AssemblyTron Golden Gate assembly of four chromoprotein expression plasmids.

Reproduces the Golden Gate workflow of:
  AssemblyTron: flexible automation of DNA assembly with Opentrons OT-2 lab robots
  Synth. Biol. 2022, doi:10.1093/synbio/ysac032 (CC BY 4.0)

Four four-fragment pIDMv5K chromoprotein expression plasmids (tsPurple, YukonOFP,
aeBlue, fuGFP) are built from seven PCR fragments: three shared backbone parts
(fragments 2, 5 and 6) plus one chromoprotein part per assembly (1, 3, 4 and 7).

Workflow (section 2.3/2.4 and 3.2 of the paper):
  1. Build a Q5 PCR master mix and set up seven 25 uL PCRs from j5-designed
     primers and linearized plasmid templates.
  2. PAUSE - the operator seals the reactions and runs them on an external
     gradient thermocycler (the OT-2 module has no gradient capability), then
     returns them to the deck.
  3. DpnI digestion of residual plasmid template, in place, in the PCR wells.
  4. PAUSE - off-deck Zymo DNA Clean & Concentrator-5 clean-up of every
     fragment (residual polymerase fills in the BsaI sticky ends), eluates
     returned to their original wells.
  5. Golden Gate assembly: a volume of each cleaned fragment proportional to
     fragment length (roughly equimolar, assuming equal PCR yield) plus T4
     ligase buffer and Golden Gate Enzyme Mix, in 20 uL reactions.
  6. PAUSE - Golden Gate thermocycling, then clean-up/elution of the assemblies.
  7. Transformation of the eluates into chemically competent E. coli TOP10,
     with LB + 0.2% dextrose recovery medium added by the robot.
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - four chromoprotein plasmids',
    'author': 'Generated from doi:10.1093/synbio/ysac032',
    'description': 'Four four-fragment Golden Gate chromoprotein assemblies, '
                   'from fragment PCR through transformation into E. coli TOP10.',
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Reaction parameters, taken from the paper (section 2.3) unless noted.
# ---------------------------------------------------------------------------

# PCRs are 25 uL with 0.1 uM primers and 0.5 ng linearized template.
PCR_VOL = 25.0
PRIMER_VOL = 2.5          # 2.5 uL of a 1 uM stock in 25 uL = 0.1 uM final
TEMPLATE_VOL = 1.0        # 1 uL of 0.5 ng/uL = 0.5 ng template

# Standard Q5 High-Fidelity set-up (NEB) at the paper's 25 uL scale. The paper
# names the reagents but not their per-reaction volumes, so the manufacturer's
# standard ratios are used: 1X Q5 buffer, 200 uM dNTPs, 0.02 U/uL polymerase.
Q5_BUFFER_VOL = 5.0       # 5X buffer -> 1X
DNTP_VOL = 0.5            # 10 mM dNTPs -> 200 uM each
Q5_POL_VOL = 0.25
MM_WATER_VOL = PCR_VOL - (Q5_BUFFER_VOL + DNTP_VOL + Q5_POL_VOL
                          + 2 * PRIMER_VOL + TEMPLATE_VOL)   # 13.25 uL
MM_PER_RXN = Q5_BUFFER_VOL + DNTP_VOL + Q5_POL_VOL + MM_WATER_VOL  # 19 uL
MM_RXNS = 8               # 7 fragments + 1 reaction of excess for dead volume

# DpnI digestion of residual template: 19 uL water, 5 uL rCutSmart, 1 uL DpnI
# added to each finished PCR, 30 min at 37 C then 20 min at 65 C.
DPNI_WATER_VOL = 19.0
RCUTSMART_VOL = 5.0
DPNI_VOL = 1.0

# Golden Gate reactions are 20 uL. The paper specifies the fragment volumes
# (proportional to fragment length, 10 uL of fragments in total) and the
# reagents; the buffer/enzyme volumes are the standard NEB Golden Gate
# Assembly Kit (BsaI-HFv2) amounts for a 20 uL reaction.
GG_VOL = 20.0
T4_BUFFER_VOL = 2.0       # 10X T4 DNA Ligase Buffer -> 1X
GG_ENZYME_VOL = 1.0       # Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase)

# Transformation (section 2.3): assemblies are column-cleaned and eluted in
# 10 uL water; 5 uL is transformed into 50 uL of TOP10 cells and the other
# 5 uL is used for NanoDrop quantification. Recovery is in 250 uL of
# LB + 0.2% (w/v) dextrose at 37 C for 60 min.
ELUTION_VOL = 10.0
DNA_INTO_CELLS_VOL = 5.0
RECOVERY_MEDIUM_VOL = 250.0

# Fragments are eluted in 20 uL after the clean-up step. The paper does not
# give a fragment elution volume; 20 uL is chosen because fragments 2 and 6
# each need 12 uL across the four assemblies, which 10 uL would not cover.
FRAGMENT_ELUTION_VOL = 20.0

# ---------------------------------------------------------------------------
# The j5 / AssemblyTron fragment and assembly design.
# ---------------------------------------------------------------------------

# fragment number -> (pcr well, forward primer well, reverse primer well, template well)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1'),   # tsPurple chromoprotein
    2: ('B1', 'B1', 'B2', 'A1'),   # backbone
    3: ('C1', 'C1', 'C2', 'B1'),   # YukonOFP chromoprotein
    4: ('D1', 'D1', 'D2', 'C1'),   # aeBlue chromoprotein
    5: ('E1', 'E1', 'E2', 'A1'),   # backbone / KanR
    6: ('F1', 'F1', 'F2', 'A1'),   # backbone
    7: ('G1', 'G1', 'G2', 'D1'),   # fuGFP chromoprotein
}
FRAGMENT_ORDER = [1, 2, 3, 4, 5, 6, 7]

# Shared backbone parts, added to every assembly, with their length-proportional volumes.
SHARED_PARTS = [(2, 3.0), (5, 2.0), (6, 3.0)]

# assembly well -> (name, chromoprotein fragment, its volume, competent cell well)
ASSEMBLIES = [
    ('A1', 'tsPurple', 1, 2.0, 'A1'),
    ('B1', 'YukonOFP', 3, 2.0, 'B1'),
    ('C1', 'aeBlue',   4, 2.0, 'C1'),
    ('D1', 'fuGFP',    7, 2.0, 'D1'),
]

# Fragments (10 uL) + T4 buffer + enzyme leave this much water per reaction.
GG_WATER_VOL = GG_VOL - (sum(v for _, v in SHARED_PARTS) + ASSEMBLIES[0][3]
                         + T4_BUFFER_VOL + GG_ENZYME_VOL)   # 7 uL


def run(protocol):
    # -----------------------------------------------------------------------
    # Deck
    # -----------------------------------------------------------------------
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    tubes_50ml = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml = protocol.load_labware(
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
    tubes_15ml = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    water = tubes_50ml['A1']
    q5_buffer = tubes_1_5ml['A1']
    dntp = tubes_1_5ml['B1']
    q5_pol = tubes_1_5ml['C1']
    pcr_mm = tubes_1_5ml['D1']
    rcutsmart = tubes_1_5ml['A2']
    dpni = tubes_1_5ml['B2']
    t4_buffer = tubes_1_5ml['C2']
    gg_enzyme = tubes_1_5ml['D2']
    lb_dextrose = tubes_15ml['A1']

    pcr_wells = [pcr_plate[FRAGMENTS[f][0]] for f in FRAGMENT_ORDER]

    def pipette_for(volume):
        """20 uL pipette handles 1-20 uL, 300 uL pipette handles 20-300 uL."""
        return p20 if volume <= 20.0 else p300

    def fresh_tips():
        """Tips are unlimited; the operator reloads racks at each pause."""
        p20.reset_tipracks()
        p300.reset_tipracks()

    # =======================================================================
    # Step 1 - Q5 PCR master mix for 8 reactions (7 fragments + 1 excess)
    # =======================================================================
    protocol.comment(
        'Step 1: building the Q5 PCR master mix for {} reactions in tubes_1_5ml_1 D1 '
        '({} uL of 5X Q5 buffer, {} uL 10 mM dNTPs, {} uL Q5 polymerase, {} uL water).'
        .format(MM_RXNS, Q5_BUFFER_VOL * MM_RXNS, DNTP_VOL * MM_RXNS,
                Q5_POL_VOL * MM_RXNS, MM_WATER_VOL * MM_RXNS))

    # Water first, then buffer, then dNTPs, then the polymerase last.
    p300.transfer(MM_WATER_VOL * MM_RXNS, water, pcr_mm, new_tip='once')
    p300.transfer(Q5_BUFFER_VOL * MM_RXNS, q5_buffer, pcr_mm, new_tip='once')
    p20.transfer(DNTP_VOL * MM_RXNS, dntp, pcr_mm, new_tip='once')
    p20.transfer(Q5_POL_VOL * MM_RXNS, q5_pol, pcr_mm, new_tip='once')

    p300.pick_up_tip()
    p300.mix(8, 100.0, pcr_mm)   # gentle: the mix contains polymerase
    p300.drop_tip()

    # =======================================================================
    # Step 2 - 25 uL PCRs: master mix, primers, template
    # =======================================================================
    protocol.comment(
        'Step 2: setting up seven {} uL PCRs in pcr_plate A1:G1 '
        '({} uL master mix + {} uL each primer (0.1 uM final) + {} uL template (0.5 ng)).'
        .format(PCR_VOL, MM_PER_RXN, PRIMER_VOL, TEMPLATE_VOL))

    # Master mix: one tip, the source is clean and every destination is empty.
    p20.transfer(MM_PER_RXN, pcr_mm, pcr_wells, new_tip='once')

    # Primers and templates: a fresh tip per fragment, each source differs.
    for frag in FRAGMENT_ORDER:
        pcr_well, fwd, rev, template = FRAGMENTS[frag]
        p20.transfer(PRIMER_VOL, primer_plate[fwd], pcr_plate[pcr_well], new_tip='always')
        p20.transfer(PRIMER_VOL, primer_plate[rev], pcr_plate[pcr_well], new_tip='always')
        # Templates are shared between fragments, so always use a fresh tip.
        p20.transfer(TEMPLATE_VOL, template_plate[template], pcr_plate[pcr_well],
                     new_tip='always', mix_after=(3, 15.0))

    # =======================================================================
    # Step 3 - OFF-DECK: gradient thermocycling
    # =======================================================================
    fresh_tips()
    protocol.pause(
        'Seal pcr_plate and move the seven reactions to the external gradient '
        'thermocycler, following the AssemblyTron reactions_setup.txt tube placement. '
        'Then return the reactions to pcr_plate A1:G1 and resume.')
    protocol.comment(
        'OFF-DECK: gradient PCR. 98 C 30 s; 34 cycles of [98 C 10 s, 30 s at the '
        'j5/AssemblyTron optimal annealing temperature for that tube position, '
        '72 C for the AssemblyTron-calculated extension time]; 72 C 5 min; hold 4 C. '
        'The OT-2 thermocycler module has no gradient capability, so this step must be '
        'run on a separate gradient thermocycler (e.g. Bio-Rad C1000). '
        'Take a small sample of each reaction for gel electrophoresis to confirm '
        'fragment sizes, then return pcr_plate to slot 5.')

    # =======================================================================
    # Step 4 - DpnI digestion of residual plasmid template
    # =======================================================================
    protocol.comment(
        'Step 4: DpnI digestion - adding {} uL water, {} uL rCutSmart Buffer and {} uL '
        'DpnI to each PCR (50 uL final).'
        .format(DPNI_WATER_VOL, RCUTSMART_VOL, DPNI_VOL))

    p20.transfer(DPNI_WATER_VOL, water, pcr_wells, new_tip='once')
    p20.transfer(RCUTSMART_VOL, rcutsmart, pcr_wells, new_tip='once')
    # DpnI last, with a fresh tip per well and mixing so the enzyme is not
    # carried between reactions.
    for well in pcr_wells:
        p20.transfer(DPNI_VOL, dpni, well, new_tip='always', mix_after=(3, 20.0))

    # =======================================================================
    # Step 5 - OFF-DECK: DpnI incubation and fragment clean-up
    # =======================================================================
    fresh_tips()
    protocol.pause(
        'Seal pcr_plate and incubate the DpnI digests off-deck, then clean up each '
        'fragment and return the eluates to pcr_plate A1:G1 before resuming.')
    protocol.comment(
        'OFF-DECK: incubate pcr_plate A1:G1 at 37 C for 30 min, then inactivate DpnI '
        'at 65 C for 20 min.')
    protocol.comment(
        'OFF-DECK: clean and concentrate all seven fragments on Zymo DNA Clean & '
        'Concentrator-5 columns to remove the polymerase, which otherwise fills in the '
        'BsaI sticky ends. Elute each fragment in {} uL nuclease-free water and return '
        'it to its original well: fragment 1 -> A1, 2 -> B1, 3 -> C1, 4 -> D1, '
        '5 -> E1, 6 -> F1, 7 -> G1.'.format(FRAGMENT_ELUTION_VOL))

    # =======================================================================
    # Step 6 - Golden Gate assembly reactions
    # =======================================================================
    protocol.comment(
        'Step 6: setting up four {} uL Golden Gate reactions in assembly_plate A1:D1 '
        '({} uL water + {} uL 10X T4 DNA Ligase Buffer + 10 uL of cleaned fragments '
        '(volume proportional to fragment length) + {} uL Golden Gate Enzyme Mix).'
        .format(GG_VOL, GG_WATER_VOL, T4_BUFFER_VOL, GG_ENZYME_VOL))

    assembly_wells = [assembly_plate[well] for well, _, _, _, _ in ASSEMBLIES]

    p20.transfer(GG_WATER_VOL, water, assembly_wells, new_tip='once')
    p20.transfer(T4_BUFFER_VOL, t4_buffer, assembly_wells, new_tip='once')

    # Shared backbone fragments, then the chromoprotein that defines each assembly.
    # A fresh tip per dispense: the tip enters wells that already hold other DNA.
    for frag, volume in SHARED_PARTS:
        source = pcr_plate[FRAGMENTS[frag][0]]
        for well in assembly_wells:
            p20.transfer(volume, source, well, new_tip='always')

    for well_name, name, frag, volume, _ in ASSEMBLIES:
        p20.transfer(volume, pcr_plate[FRAGMENTS[frag][0]], assembly_plate[well_name],
                     new_tip='always')

    # Enzyme mix last, mixing each reaction once it is complete.
    for well in assembly_wells:
        p20.transfer(GG_ENZYME_VOL, gg_enzyme, well, new_tip='always',
                     mix_after=(5, 10.0))

    # =======================================================================
    # Step 7 - Golden Gate thermocycling and assembly clean-up
    # =======================================================================
    fresh_tips()
    protocol.pause(
        'Seal assembly_plate and run the Golden Gate cycling programme, then clean up '
        'the assemblies and return the eluates to assembly_plate A1:D1 before resuming.')
    protocol.comment(
        'OFF-DECK (or on the Opentrons thermocycler module): Golden Gate cycling. '
        '30 cycles of [37 C 1 min, 16 C 1 min]; 60 C 5 min; hold 4 C, lid 105 C. '
        'The paper does not state the cycling parameters, so the standard NEB Golden '
        'Gate Assembly Kit (BsaI-HFv2) programme for 4-6 fragment assemblies is used.')
    protocol.comment(
        'OFF-DECK: clean and concentrate each of the four assemblies on a Zymo DNA '
        'Clean & Concentrator-5 column and elute in {} uL molecular grade water. '
        'Return the eluates to assembly_plate A1:D1.'.format(ELUTION_VOL))

    # =======================================================================
    # Step 8 - Transformation into E. coli TOP10
    # =======================================================================
    protocol.comment(
        'Step 8: adding {} uL of each cleaned assembly to {} uL of chemically '
        'competent E. coli TOP10 in cells_plate A1:D1.'
        .format(DNA_INTO_CELLS_VOL, 50.0))

    for assembly_well, name, _, _, cell_well in ASSEMBLIES:
        protocol.comment('  {} assembly ({}) -> cells_plate {}'
                         .format(name, assembly_well, cell_well))
        # Dispense slowly and do not mix: competent cells are shear-sensitive.
        p20.transfer(DNA_INTO_CELLS_VOL, assembly_plate[assembly_well],
                     cells_plate[cell_well], new_tip='always')

    protocol.comment(
        'OFF-DECK: use the remaining {} uL of each eluate to measure DNA concentration '
        'on a NanoDrop-2000c for the transformation efficiency (CFU/ug) calculation.'
        .format(ELUTION_VOL - DNA_INTO_CELLS_VOL))

    fresh_tips()
    protocol.pause(
        'Transformation: incubate cells_plate A1:D1 on ice for 30 min, heat shock at '
        '42 C for 60 s, return to ice for 2 min, then put cells_plate back in slot 7 '
        'and resume so the robot can add the recovery medium.')
    protocol.comment(
        'OFF-DECK: 30 min on ice, 42 C heat shock for 60 s, then back on ice.')

    # Recovery medium: LB + 0.2% (w/v) dextrose (catabolite repression).
    protocol.comment(
        'Step 9: adding {} uL LB + 0.2% (w/v) dextrose to each transformation.'
        .format(RECOVERY_MEDIUM_VOL))
    cell_wells = [cells_plate[cw] for _, _, _, _, cw in ASSEMBLIES]
    p300.transfer(RECOVERY_MEDIUM_VOL, lb_dextrose, cell_wells, new_tip='once')

    protocol.comment(
        'OFF-DECK: recover the transformations at 37 C for 60 min with shaking.')
    protocol.comment(
        'OFF-DECK: plate 50-200 uL of each recovery, neat or as a 10x dilution '
        'depending on the predicted assembly efficiency, on LB agar with 50 ug/mL '
        'kanamycin; incubate at 37 C overnight.')
    protocol.comment(
        'OFF-DECK: count colonies, report CFU/ug of assembly DNA transformed, and '
        'score chromoprotein expression (purple = tsPurple, orange = YukonOFP, '
        'blue = aeBlue, green = fuGFP). Confirm assemblies by Sanger or whole-plasmid '
        'sequencing.')

    # No tip is left on either pipette at the end of the run.
