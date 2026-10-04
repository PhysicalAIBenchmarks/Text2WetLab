"""
Golden Gate assembly of four four-fragment chromoprotein expression plasmids
with the AssemblyTron workflow on an Opentrons OT-2.

Method source: Bryant J.A. et al., "AssemblyTron: flexible automation of DNA
assembly with Opentrons OT-2 lab robots", Synthetic Biology 7(1), 2022,
doi:10.1093/synbio/ysac032 (CC BY).  All volumes, times and temperatures below
are taken from the paper's "Materials and methods" and "Results > Golden Gate
assembly" sections; every place where the paper leaves a value open is marked
with a "CHOICE:" comment giving the value used and the reason.

Workflow (Figure 1 of the paper):
  1.  Build a Q5 PCR master mix and set up seven 25 uL fragment PCRs.
  2.  PAUSE - off-deck gradient thermocycling (the OT-2 thermocycler module has
      no gradient capability, so the paper transfers the tubes to a Bio-Rad
      C100 gradient cycler and returns them).
  3.  DpnI digestion of residual plasmid template, on deck.
  4.  PAUSE - off-deck 37 C / 65 C incubation, then column clean-up of every
      fragment (the paper found residual polymerase fills in the BsaI sticky
      ends, so each fragment must be cleaned before assembly).
  5.  Four 20 uL Golden Gate reactions, fragment volumes proportional to
      fragment length (the paper's equimolar approximation).
  6.  PAUSE - Golden Gate thermocycling, then clean-and-concentrate the
      assemblies and elute in 10 uL water.
  7.  Transformation of E. coli TOP10 chemically competent cells: add DNA,
      PAUSE for the ice / 42 C heat-shock, add LB + 0.2% dextrose, PAUSE for
      the 37 C recovery and plating.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - four chromoprotein plasmids',
    'author': 'Generated from doi:10.1093/synbio/ysac032',
    'description': (
        'Seven fragment PCRs, DpnI digestion, four four-fragment Golden Gate '
        'assemblies and transformation into E. coli TOP10.'
    ),
    'apiLevel': '2.13',
}

# ---------------------------------------------------------------------------
# Reaction parameters, all from the paper unless marked CHOICE
# ---------------------------------------------------------------------------

# "PCRs were performed in 25 uL volumes using ... Q5 High-Fidelity DNA
# Polymerase (NEB) with 0.1 uM primers and 0.5 ng linearized plasmid template."
PCR_VOLUME = 25.0
PRIMER_VOL = 2.5          # 1 uM stock -> 0.1 uM in 25 uL
TEMPLATE_VOL = 1.0        # 0.5 ng/uL stock -> 0.5 ng per reaction
# Standard Q5 reaction composition (NEB, the polymerase the paper used):
# 1X Q5 buffer, 200 uM dNTPs, 0.02 U/uL Q5.
Q5_BUFFER_PER_RXN = 5.0   # 5X buffer -> 1X
DNTP_PER_RXN = 0.5        # 10 mM stock -> 200 uM
Q5_POL_PER_RXN = 0.25
MM_PER_RXN = Q5_BUFFER_PER_RXN + DNTP_PER_RXN + Q5_POL_PER_RXN  # + water below
WATER_PER_RXN = PCR_VOLUME - PRIMER_VOL * 2 - TEMPLATE_VOL - MM_PER_RXN
MASTER_MIX_PER_RXN = MM_PER_RXN + WATER_PER_RXN                 # 19.0 uL
# Seven fragments; the master mix tube is prepared for 8 reactions so there is
# one reaction of dead volume, as stated in the deck description.
MM_REACTIONS = 8

# "For plasmid template digestion, 19 uL water, 5 uL rCutSmart Buffer (NEB) and
# 1 uL DpnI (NEB) were added and incubated for 30 min at 37 C prior to
# deactivation at 65 C for 20 min."
DPNI_WATER = 19.0
DPNI_BUFFER = 5.0
DPNI_ENZYME = 1.0

# CHOICE: the paper gives a 10 uL elution only for the final assemblies.  It
# does not state the elution volume for the cleaned fragments.  Backbone
# fragments 2 and 6 are each consumed four times at 3 uL (12 uL total), so a
# 10 uL elution would run the wells dry.  Eluting each cleaned fragment in
# 25 uL leaves comfortable headroom while staying within the Zymo DNA Clean &
# Concentrator-5 working range.
FRAGMENT_ELUTION_VOL = 25.0

# Golden Gate: 20 uL reactions (stated in the task design tables).  Fragment
# volumes sum to 10 uL per assembly, leaving 10 uL for buffer, enzyme, water.
# Standard NEB Golden Gate composition, which is what the BsaI-HFv2 + T4 ligase
# mix calls for: 1X T4 DNA Ligase Buffer and 1 uL enzyme mix per 20 uL.
GG_VOLUME = 20.0
GG_BUFFER = 2.0           # 10X T4 DNA Ligase Buffer -> 1X
GG_ENZYME = 1.0

# "DNA was eluted with 10 uL molecular grade water.  This elution was
# transformed into 50 uL of TOP10-competent cells.  The other 5 uL was used to
# measure DNA concentration" -> 5 uL of the 10 uL elution goes into the cells.
ASSEMBLY_ELUTION_VOL = 10.0
DNA_INTO_CELLS = 5.0
# "recovered at 37 C for 60 min with 250 uL LB with catabolite repression
# (LB + 0.2% (w/v) dextrose) medium added."
RECOVERY_MEDIUM_VOL = 250.0

# ---------------------------------------------------------------------------
# j5 / AssemblyTron design tables (fixed)
# ---------------------------------------------------------------------------

# fragment number -> (pcr well, forward primer well, reverse primer well,
#                     template well, description)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1', 'tsPurple chromoprotein'),
    2: ('B1', 'B1', 'B2', 'A1', 'backbone'),
    3: ('C1', 'C1', 'C2', 'B1', 'YukonOFP chromoprotein'),
    4: ('D1', 'D1', 'D2', 'C1', 'aeBlue chromoprotein'),
    5: ('E1', 'E1', 'E2', 'A1', 'backbone / KanR'),
    6: ('F1', 'F1', 'F2', 'A1', 'backbone'),
    7: ('G1', 'G1', 'G2', 'D1', 'fuGFP chromoprotein'),
}
FRAGMENT_ORDER = [1, 2, 3, 4, 5, 6, 7]

# assembly well -> (name, [(fragment number, volume uL), ...], cells well)
ASSEMBLIES = [
    ('A1', 'tsPurple',  [(2, 3.0), (5, 2.0), (6, 3.0), (1, 2.0)], 'A1'),
    ('B1', 'YukonOFP',  [(2, 3.0), (5, 2.0), (6, 3.0), (3, 2.0)], 'B1'),
    ('C1', 'aeBlue',    [(2, 3.0), (5, 2.0), (6, 3.0), (4, 2.0)], 'C1'),
    ('D1', 'fuGFP',     [(2, 3.0), (5, 2.0), (6, 3.0), (7, 2.0)], 'D1'),
]


def run(protocol: protocol_api.ProtocolContext):

    # -- Labware -----------------------------------------------------------
    tubes_50ml = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml = protocol.load_labware(
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
    tubes_15ml = protocol.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips300])

    # -- Reagent positions -------------------------------------------------
    water = tubes_50ml['A1']
    q5_buffer = tubes_1_5ml['A1']
    dntp = tubes_1_5ml['B1']
    q5_pol = tubes_1_5ml['C1']
    pcr_mm = tubes_1_5ml['D1']          # empty at the start
    rcutsmart = tubes_1_5ml['A2']
    dpni = tubes_1_5ml['B2']
    t4_buffer = tubes_1_5ml['C2']
    gg_enzyme = tubes_1_5ml['D2']
    lb_dextrose = tubes_15ml['A1']

    plate_labware = (primer_plate, template_plate, pcr_plate,
                     assembly_plate, cells_plate)

    # -- Tip bookkeeping ---------------------------------------------------
    # Tips are unlimited; reset the rack once all 96 positions are consumed so
    # the run never raises OutOfTipsError and never moves without a tip.
    tips_used = {'left': 0, 'right': 0}

    def pick_up(pipette):
        mount = 'left' if pipette is p20 else 'right'
        if tips_used[mount] >= 96:
            pipette.reset_tipracks()
            tips_used[mount] = 0
        pipette.pick_up_tip()
        tips_used[mount] += 1

    # -- Liquid handling helpers ------------------------------------------
    def pipette_for(volume):
        """p20 covers 1-20 uL, p300 covers 20-300 uL."""
        return p20 if volume <= p20.max_volume else p300

    def bottom_of(well, is_source):
        """Aspirate/dispense height.

        Flat 96-well plates hold as little as 10 uL (about 0.3 mm deep), so
        work very close to the bottom there; tube racks are deep, so keep a
        larger clearance.
        """
        if well.parent in plate_labware:
            return well.bottom(z=0.5 if is_source else 1.0)
        return well.bottom(z=2.0)

    def transfer(volume, source, dest, mix_volume=None, mix_reps=3):
        """Single source -> single dest with a fresh tip, never over capacity."""
        if volume <= 0:
            return
        pipette = pipette_for(volume)
        pick_up(pipette)
        remaining = volume
        while remaining > 1e-6:
            step = min(remaining, pipette.max_volume)
            pipette.aspirate(step, bottom_of(source, True))
            pipette.dispense(step, bottom_of(dest, False))
            pipette.blow_out(dest.top(z=-2))
            remaining -= step
        if mix_volume:
            mixer = pipette_for(mix_volume)
            if mixer is pipette:
                pipette.mix(mix_reps, min(mix_volume, pipette.max_volume),
                            bottom_of(dest, False))
                pipette.blow_out(dest.top(z=-2))
            else:
                pipette.drop_tip()
                pick_up(mixer)
                mixer.mix(mix_reps, min(mix_volume, mixer.max_volume),
                          bottom_of(dest, False))
                mixer.blow_out(dest.top(z=-2))
                mixer.drop_tip()
                return
        pipette.drop_tip()

    def mix_well(volume, well, reps=5):
        pipette = pipette_for(volume)
        pick_up(pipette)
        pipette.mix(reps, min(volume, pipette.max_volume), bottom_of(well, False))
        pipette.blow_out(well.top(z=-2))
        pipette.drop_tip()

    # =====================================================================
    # Step 1 - PCR master mix for 8 reactions in tubes_1_5ml_1 D1
    # =====================================================================
    protocol.comment(
        'STEP 1: build the Q5 PCR master mix for {} reactions in tubes_1_5ml_1 '
        'D1 ({} uL water, {} uL 5X Q5 buffer, {} uL 10 mM dNTPs, {} uL Q5 '
        'polymerase).'.format(
            MM_REACTIONS, WATER_PER_RXN * MM_REACTIONS,
            Q5_BUFFER_PER_RXN * MM_REACTIONS, DNTP_PER_RXN * MM_REACTIONS,
            Q5_POL_PER_RXN * MM_REACTIONS))

    transfer(WATER_PER_RXN * MM_REACTIONS, water, pcr_mm)       # 106.0 uL
    transfer(Q5_BUFFER_PER_RXN * MM_REACTIONS, q5_buffer, pcr_mm)  # 40.0 uL
    transfer(DNTP_PER_RXN * MM_REACTIONS, dntp, pcr_mm)         # 4.0 uL
    # Polymerase last and at the bottom of the tube, so it is never pipetted
    # into an empty tube on its own.
    transfer(Q5_POL_PER_RXN * MM_REACTIONS, q5_pol, pcr_mm)     # 2.0 uL
    mix_well(100.0, pcr_mm, reps=5)

    # =====================================================================
    # Step 2 - seven 25 uL fragment PCRs in pcr_plate A1:G1
    # =====================================================================
    protocol.comment(
        'STEP 2: set up seven {} uL fragment PCRs in pcr_plate A1:G1 '
        '({} uL master mix + {} uL forward primer + {} uL reverse primer + '
        '{} uL template each).'.format(
            PCR_VOLUME, MASTER_MIX_PER_RXN, PRIMER_VOL, PRIMER_VOL,
            TEMPLATE_VOL))

    for frag in FRAGMENT_ORDER:
        pcr_well, fwd, rev, tmpl, name = FRAGMENTS[frag]
        protocol.comment(
            '  Fragment {} ({}): pcr_plate {} <- primers {}/{}, template '
            '{}.'.format(frag, name, pcr_well, fwd, rev, tmpl))
        transfer(MASTER_MIX_PER_RXN, pcr_mm, pcr_plate[pcr_well])
        transfer(PRIMER_VOL, primer_plate[fwd], pcr_plate[pcr_well])
        transfer(PRIMER_VOL, primer_plate[rev], pcr_plate[pcr_well])
        transfer(TEMPLATE_VOL, template_plate[tmpl], pcr_plate[pcr_well],
                 mix_volume=15.0)

    # =====================================================================
    # Step 3 - MANUAL: gradient thermocycling off deck
    # =====================================================================
    protocol.comment(
        'STEP 3 (MANUAL): seal pcr_plate / cap the 100 uL PCR tubes, spin '
        'them down and move them to the gradient thermocycler in the tube '
        'positions given by the AssemblyTron reactions_setup file. The OT-2 '
        'thermocycler module has no gradient capability, so the paper uses a '
        'separate Bio-Rad C100 gradient cycler here.')
    protocol.comment(
        '  Cycling: 98 C 30 s; 34 cycles of [98 C 10 s, 30 s at the '
        'AssemblyTron/j5 optimal annealing temperature for that tube position '
        '(fragment 5 sits at the hot end of the gradient), extension at 72 C '
        'for the AssemblyTron-calculated time]; final 72 C 5 min; hold at '
        '4 C. CHOICE: 34 cycles, the lower of the two cycle numbers the paper '
        'reports, which is sufficient for 0.5 ng of linearized template.')
    protocol.comment(
        '  Then run a sample of each reaction on a 1% agarose gel to confirm '
        'fragment sizes, and return pcr_plate to slot 5.')
    protocol.pause(
        'Gradient PCR: remove pcr_plate, thermocycle as described, check the '
        'fragments on a gel, then return pcr_plate to slot 5 and resume.')

    # =====================================================================
    # Step 4 - DpnI digestion of residual template
    # =====================================================================
    protocol.comment(
        'STEP 4: DpnI digestion of residual plasmid template. Add {} uL '
        'water, {} uL rCutSmart Buffer and {} uL DpnI to each 25 uL PCR '
        '(50 uL final).'.format(DPNI_WATER, DPNI_BUFFER, DPNI_ENZYME))

    for frag in FRAGMENT_ORDER:
        pcr_well = FRAGMENTS[frag][0]
        transfer(DPNI_WATER, water, pcr_plate[pcr_well])
        transfer(DPNI_BUFFER, rcutsmart, pcr_plate[pcr_well])
        transfer(DPNI_ENZYME, dpni, pcr_plate[pcr_well], mix_volume=30.0)

    # =====================================================================
    # Step 5 - MANUAL: DpnI incubation and column clean-up of every fragment
    # =====================================================================
    protocol.comment(
        'STEP 5 (MANUAL): incubate the seven digests at 37 C for 30 min, then '
        'inactivate DpnI at 65 C for 20 min.')
    protocol.comment(
        '  Then clean and concentrate every fragment on DNA Clean & '
        'Concentrator-5 columns (Zymo). The paper found residual polymerase '
        'fills in the BsaI overhangs and blocks the assembly, so this '
        'clean-up is required before Golden Gate.')
    protocol.comment(
        '  Elute each cleaned fragment in {} uL nuclease-free water and '
        'return it to its own well of pcr_plate (fragment 1 -> A1 ... '
        'fragment 7 -> G1), then put pcr_plate back in slot 5. CHOICE: {} uL '
        'elution rather than the 10 uL the paper uses for final assemblies, '
        'because backbone fragments 2 and 6 are each drawn on four times at '
        '3 uL.'.format(FRAGMENT_ELUTION_VOL, FRAGMENT_ELUTION_VOL))
    protocol.pause(
        'DpnI incubation (37 C 30 min, 65 C 20 min) and column clean-up: '
        'elute each fragment in {} uL water, return it to its original '
        'pcr_plate well, replace pcr_plate in slot 5 and '
        'resume.'.format(FRAGMENT_ELUTION_VOL))

    # =====================================================================
    # Step 6 - four 20 uL Golden Gate reactions in assembly_plate A1:D1
    # =====================================================================
    protocol.comment(
        'STEP 6: assemble four {} uL Golden Gate reactions in assembly_plate '
        'A1:D1. Fragment volumes are proportional to fragment length, the '
        "paper's approximation to an equimolar mix given similar PCR "
        'yields.'.format(GG_VOLUME))

    for well, name, parts, _cells_well in ASSEMBLIES:
        fragment_total = sum(volume for _f, volume in parts)
        water_vol = GG_VOLUME - fragment_total - GG_BUFFER - GG_ENZYME
        protocol.comment(
            '  Assembly {} ({}): {} uL water + {} uL 10X T4 ligase buffer + '
            '{} uL fragments + {} uL Golden Gate Enzyme Mix.'.format(
                well, name, water_vol, GG_BUFFER, fragment_total, GG_ENZYME))

        # Water first into the empty well, then buffer, then the DNA, with the
        # BsaI/ligase mix added last.
        transfer(water_vol, water, assembly_plate[well])
        transfer(GG_BUFFER, t4_buffer, assembly_plate[well])
        for frag, volume in parts:
            pcr_well = FRAGMENTS[frag][0]
            protocol.comment(
                '    fragment {} ({}): {} uL from pcr_plate {}.'.format(
                    frag, FRAGMENTS[frag][4], volume, pcr_well))
            transfer(volume, pcr_plate[pcr_well], assembly_plate[well])
        transfer(GG_ENZYME, gg_enzyme, assembly_plate[well], mix_volume=12.0)

    # =====================================================================
    # Step 7 - MANUAL: Golden Gate thermocycling and clean-up
    # =====================================================================
    protocol.comment(
        'STEP 7 (MANUAL): seal assembly_plate and run the Golden Gate '
        'cycling. The paper runs this on the Opentrons thermocycler module '
        'but pauses so the reactions can be moved to a standalone cycler if '
        'the module is not available; this deck has no thermocycler module '
        'loaded, so run it off deck.')
    protocol.comment(
        '  CHOICE: the paper cites Engler et al. without listing the cycling '
        'parameters. Use the NEB protocol for the BsaI-HFv2 + T4 ligase '
        'Golden Gate Enzyme Mix with 2-4 inserts: 30 cycles of [37 C 1 min, '
        '16 C 1 min], then 60 C 5 min, hold at 4 C.')
    protocol.comment(
        '  Then clean and concentrate each assembly on a DNA Clean & '
        'Concentrator-5 column, elute in {} uL molecular grade water and '
        'return each eluate to its own assembly_plate well (A1:D1). Use {} uL '
        'of each eluate on the NanoDrop for the transformation efficiency '
        'calculation; the other {} uL is transformed '
        'below.'.format(ASSEMBLY_ELUTION_VOL, ASSEMBLY_ELUTION_VOL - DNA_INTO_CELLS,
                        DNA_INTO_CELLS))
    protocol.pause(
        'Golden Gate cycling (30 x [37 C 1 min / 16 C 1 min], 60 C 5 min), '
        'then column clean-up into {} uL water. Return assembly_plate to slot '
        '6, put the chilled cells_plate back in slot 7 and '
        'resume.'.format(ASSEMBLY_ELUTION_VOL))

    # =====================================================================
    # Step 8 - transformation into E. coli TOP10
    # =====================================================================
    protocol.comment(
        'STEP 8: add {} uL of each cleaned assembly to 50 uL of chemically '
        'competent TOP10 cells in cells_plate. Keep the cells on a cold block '
        'for this step.'.format(DNA_INTO_CELLS))

    for well, name, _parts, cells_well in ASSEMBLIES:
        protocol.comment(
            '  {} assembly: assembly_plate {} -> cells_plate {}.'.format(
                name, well, cells_well))
        # Stir gently rather than mixing hard: competent cells are fragile.
        transfer(DNA_INTO_CELLS, assembly_plate[well], cells_plate[cells_well],
                 mix_volume=10.0, mix_reps=2)

    protocol.comment(
        'STEP 9 (MANUAL): incubate the transformation mixes on ice for '
        '30 min, heat shock at 42 C for 60 s, then return them to ice for '
        '2 min. CHOICE: the 2 min post-shock ice step is standard practice '
        'and is not spelled out in the paper. Put cells_plate back in slot 7 '
        'and resume.')
    protocol.pause(
        'Transformation: 30 min on ice, 42 C heat shock for 60 s, 2 min back '
        'on ice. Return cells_plate to slot 7 and resume.')

    # =====================================================================
    # Step 10 - recovery medium
    # =====================================================================
    protocol.comment(
        'STEP 10: add {} uL LB + 0.2% (w/v) dextrose (catabolite repression) '
        'to each transformation.'.format(RECOVERY_MEDIUM_VOL))

    for _well, name, _parts, cells_well in ASSEMBLIES:
        protocol.comment(
            '  {}: {} uL LB + dextrose -> cells_plate {}.'.format(
                name, RECOVERY_MEDIUM_VOL, cells_well))
        transfer(RECOVERY_MEDIUM_VOL, lb_dextrose, cells_plate[cells_well],
                 mix_volume=150.0, mix_reps=2)

    protocol.comment(
        'STEP 11 (MANUAL): recover the four transformations at 37 C with '
        'shaking for 60 min. Then plate 50-200 uL of each mix, or of a 10X '
        'dilution, on LB agar with 50 ug/mL kanamycin (the assembled plasmids '
        'carry KanR from fragment 5) and incubate overnight at 37 C.')
    protocol.comment(
        '  Score colonies by chromoprotein colour (tsPurple, YukonOFP, '
        'aeBlue, fuGFP), count CFU/ug of DNA plated and confirm the '
        'assemblies by Sanger or whole-plasmid sequencing.')
    protocol.comment(
        'Run complete. Collect the remaining fragment and assembly stocks '
        'from pcr_plate and assembly_plate.')
