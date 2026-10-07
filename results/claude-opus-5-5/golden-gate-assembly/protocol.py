"""Golden Gate assembly of four four-fragment chromoprotein expression plasmids.

AssemblyTron-style workflow (Synth. Biol. 2022, doi:10.1093/synbio/ysac032):
  PCR setup -> gradient PCR -> DpnI digest -> column cleanup ->
  Golden Gate (BsaI-HFv2 + T4 ligase) -> cleanup -> transformation into TOP10.

Seven fragments are amplified from four linearized pIDMv5K chromoprotein
plasmids.  Fragments 2, 5 and 6 are the shared backbone pieces; fragments
1, 3, 4 and 7 are the tsPurple / aeBlue / fuGFP / YukonOFP chromoprotein
pieces that make the four assemblies distinct.  Fragment volumes into each
Golden Gate reaction are proportional to fragment length.
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - 4 chromoprotein plasmids',
    'author': 'AssemblyTron workflow',
    'description': ('Four-fragment Golden Gate assembly of four chromoprotein '
                    'expression plasmids, from PCR setup through transformation.'),
    'apiLevel': '2.13',
}

# Column-1 wells of the PCR plate, one per fragment (fragments 1-7).
FRAGMENT_WELLS = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']
# Golden Gate reactions / transformations, one per chromoprotein.
ASSEMBLY_WELLS = ['A1', 'B1', 'C1', 'D1']


def run(protocol):
    # ------------------------------------------------------------------ deck
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

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

    # ---------------------------------------------------------------- reagents
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

    fragments = [pcr_plate[w] for w in FRAGMENT_WELLS]
    assemblies = [assembly_plate[w] for w in ASSEMBLY_WELLS]
    transformations = [cells_plate[w] for w in ASSEMBLY_WELLS]

    # Tip bookkeeping: tips are unlimited, so reset a rack once it is used up.
    used = {p20: 0, p300: 0}

    def pipette_for(volume):
        return p20 if volume <= 20 else p300

    def take_tips(pipette, count):
        """Reserve `count` tips, resetting the rack if it would run out."""
        if used[pipette] + count > 96:
            pipette.reset_tipracks()
            used[pipette] = 0
        used[pipette] += count

    def move(volume, sources, dests, new_tip='once', mix_after=None):
        """Transfer `volume` from source(s) to destination(s), pairing in order.

        A single source is reused for every destination; a list of sources is
        zipped with the destinations one-to-one.
        """
        if not isinstance(sources, list):
            sources = [sources]
        pipette = pipette_for(volume)
        take_tips(pipette, len(dests) if new_tip == 'always' else 1)
        pipette.transfer(volume, sources if len(sources) > 1 else sources[0],
                         dests, new_tip=new_tip, mix_after=mix_after)

    def mix_wells(volume, wells, repetitions):
        pipette = pipette_for(volume)
        take_tips(pipette, len(wells))
        for well in wells:
            pipette.pick_up_tip()
            pipette.mix(repetitions, volume, well)
            pipette.drop_tip()

    # ================================================================ PCR setup
    # Steps 1-5: build a PCR master mix for 8 reactions (7 fragments + overage)
    # in tubes_1_5ml_1 D1: water, 5X Q5 buffer, dNTPs, Q5 polymerase.
    protocol.comment('Step 1-5: assembling Q5 PCR master mix for 8 reactions.')
    move(106, water, [pcr_mm])                      # step 1: nuclease-free water
    move(40, q5_buffer, [pcr_mm])                   # step 2: 5X Q5 buffer
    move(4, dntp, [pcr_mm])                         # step 3: 10 mM dNTPs
    move(2, q5_pol, [pcr_mm])                       # step 4: Q5 polymerase
    mix_wells(100, [pcr_mm], 5)                     # step 5

    # Step 6: 19 uL master mix into each fragment reaction.
    protocol.comment('Step 6: distributing PCR master mix to pcr_plate A1:G1.')
    move(19, pcr_mm, fragments)

    # Steps 7-8: j5-designed primers, 2.5 uL each at 1 uM (0.1 uM final in 25 uL).
    protocol.comment('Step 7-8: adding forward and reverse primers.')
    fwd_primers = [primer_plate[w] for w in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1']]
    rev_primers = [primer_plate[w] for w in ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2']]
    move(2.5, fwd_primers, fragments, new_tip='always')      # step 7
    move(2.5, rev_primers, fragments, new_tip='always')      # step 8

    # Step 9: 1 uL linearized template at 0.5 ng/uL = 0.5 ng per reaction.
    # Fragments 1, 2, 5, 6 come off the tsPurple plasmid (template A1); the
    # other chromoprotein fragments come off their own plasmids.
    protocol.comment('Step 9: adding 0.5 ng linearized template to each reaction.')
    templates = [template_plate[w] for w in ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']]
    move(1, templates, fragments, new_tip='always')

    mix_wells(15, fragments, 3)                     # step 10

    # Step 11: gradient PCR off-deck.
    protocol.comment(
        'Step 11 (manual): Seal pcr_plate (or move the PCR tubes) and transfer '
        'manually to the Bio-Rad C100 gradient thermocycler. Run: 98C 30 s; '
        '34 cycles of 98C 10 s, annealing 30 s at the AssemblyTron/j5 '
        'optimal-gradient temperature for each fragment, 72C extension at the '
        'time set by AssemblyTron (about 20-30 s/kb); final extension 72C 5 min; '
        'hold 4C. Take a sample of each reaction for gel electrophoresis, then '
        'return to the OT-2.')

    # ============================================================ DpnI digestion
    # Steps 12-15: bring each 25 uL PCR to 50 uL with water, rCutSmart buffer
    # and DpnI to chew up the methylated template plasmid.
    protocol.comment('Step 12-15: setting up DpnI digests (50 uL each).')
    move(19, water, fragments)                      # step 12
    move(5, rcutsmart, fragments)                   # step 13
    move(1, dpni, fragments)                        # step 14
    mix_wells(30, fragments, 3)                     # step 15

    protocol.comment(
        'Step 16 (manual): Incubate pcr_plate A1:G1 at 37C for 30 min, then 65C '
        'for 20 min (DpnI inactivation) on the thermocycler block.')

    protocol.comment(
        'Step 17 (manual): Pause the protocol. Clean and concentrate each of the '
        '7 fragments with a Zymo DNA Clean & Concentrator-5 column: 5:1 DNA '
        'Binding Buffer to sample (250 uL per 50 uL), spin 30 s, wash 2 x 200 uL '
        'DNA Wash Buffer (30 s spins), elute in 20 uL water after 1 min at room '
        'temperature (30 s spin). Return the eluted fragments to their original '
        'positions pcr_plate A1:G1 (fragments 1-7) and resume the protocol.')

    # ====================================================== Golden Gate assembly
    # Steps 18-24: 20 uL reactions, fragment volumes proportional to length.
    protocol.comment('Step 18-19: water and 10X T4 DNA Ligase Buffer into assemblies.')
    move(7, water, assemblies)                      # step 18
    move(2, t4_buffer, assemblies)                  # step 19

    protocol.comment('Step 20-22: shared backbone fragments 2, 5 and 6.')
    move(3, pcr_plate['B1'], assemblies)            # step 20: fragment 2
    move(2, pcr_plate['E1'], assemblies)            # step 21: fragment 5 (KanR)
    move(3, pcr_plate['F1'], assemblies)            # step 22: fragment 6

    # Step 23: one distinct chromoprotein fragment per assembly.
    protocol.comment('Step 23: chromoprotein fragments 1, 3, 4 and 7.')
    chromoproteins = [pcr_plate[w] for w in ['A1', 'C1', 'D1', 'G1']]
    move(2, chromoproteins, assemblies, new_tip='always')

    # Step 24: BsaI-HFv2 + T4 ligase, mixed in after dispensing.
    protocol.comment('Step 24: Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase).')
    move(1, gg_enzyme, assemblies, mix_after=(5, 10))

    protocol.comment(
        'Step 25 (manual): Run Golden Gate program on assembly_plate in the '
        'Opentrons thermocycler module: 30 cycles of 37C 5 min then 16C 5 min; '
        'then 60C 5 min; hold at 4C. Lid about 85C. If no module is available, '
        'pause and move reactions to another thermocycler.')

    protocol.comment(
        'Step 26 (manual): Clean and concentrate each assembly with a Zymo DNA '
        'Clean & Concentrator-5 column (5:1 binding buffer, 2 x 200 uL wash) and '
        'elute in 10 uL molecular grade water; return the eluates to '
        'assembly_plate A1:D1.')

    # ============================================================ transformation
    # Step 27: half of each 10 uL eluate into chemically competent TOP10 cells.
    protocol.comment('Step 27: adding purified assemblies to competent TOP10 cells.')
    move(5, assemblies, transformations, new_tip='always')

    protocol.comment(
        'Step 28 (manual): Measure DNA concentration of the remaining 5 uL of '
        'each eluate with a NanoDrop-2000c for CFU/ug calculation.')

    protocol.comment(
        'Step 29 (manual): Incubate cells_plate A1:D1 for 30 min on ice, heat '
        'shock at 42C for 60 s, then return to ice for about 2 min.')

    # Step 30: outgrowth medium.
    protocol.comment('Step 30: adding LB + 0.2% dextrose for recovery.')
    move(250, lb_dextrose, transformations)

    protocol.comment(
        'Step 31 (manual): Recover cells at 37C for 60 min with shaking '
        '(about 250 rpm).')

    protocol.comment(
        'Step 32 (manual): Plate 50-200 uL of each recovery (neat or a 10x '
        'dilution, depending on predicted efficiency) onto separate LB agar '
        'plates containing kanamycin 50 ug/mL; incubate at 37C overnight.')

    protocol.comment(
        'Step 33 (manual): Manually count colonies per plate and score the '
        'fraction showing the expected chromoprotein colour (purple, orange, '
        'blue, green); report CFU/ug of DNA plated.')
