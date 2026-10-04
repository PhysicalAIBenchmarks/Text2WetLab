"""AssemblyTron Golden Gate assembly of four four-fragment chromoprotein plasmids.

Implements the Golden Gate workflow from "AssemblyTron: flexible automation of DNA
assembly with Opentrons OT-2 lab robots" (Synth. Biol. 2022, ysac032) for the
chromoprotein assemblies of Figure 3: seven fragment PCRs -> DpnI digestion of
residual template -> column clean-up -> four 20 uL Golden Gate reactions ->
transformation into E. coli TOP10.

Steps the OT-2 cannot do itself (sealing, gradient thermocycling, the Golden Gate
thermocycler programme, Zymo column clean-ups, ice incubations, heat shock, 37 C
recovery and plating) are announced with protocol.comment() at the point they happen
and the deck is paused so the operator can perform them.
"""

from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - four chromoprotein plasmids',
    'author': 'AssemblyTron workflow (Synth. Biol. 2022, doi:10.1093/synbio/ysac032)',
    'description': ('PCR of 7 fragments, DpnI digestion, 4x four-fragment Golden Gate '
                    'assembly and transformation into E. coli TOP10.'),
    'apiLevel': '2.13',
}

# --- Reaction design (fixed j5 / AssemblyTron output) -------------------------------
# fragment -> (pcr_plate well, fwd primer well, rev primer well, template well)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1'),   # tsPurple chromoprotein
    2: ('B1', 'B1', 'B2', 'A1'),   # backbone
    3: ('C1', 'C1', 'C2', 'B1'),   # YukonOFP chromoprotein
    4: ('D1', 'D1', 'D2', 'C1'),   # aeBlue chromoprotein
    5: ('E1', 'E1', 'E2', 'A1'),   # backbone / KanR
    6: ('F1', 'F1', 'F2', 'A1'),   # backbone
    7: ('G1', 'G1', 'G2', 'D1'),   # fuGFP chromoprotein
}

# assembly well -> list of (fragment, uL of cleaned fragment); volumes are proportional
# to fragment length, which gives a roughly equimolar mix assuming equal PCR yields.
ASSEMBLIES = {
    'A1': [(2, 3.0), (5, 2.0), (6, 3.0), (1, 2.0)],   # tsPurple
    'B1': [(2, 3.0), (5, 2.0), (6, 3.0), (3, 2.0)],   # YukonOFP
    'C1': [(2, 3.0), (5, 2.0), (6, 3.0), (4, 2.0)],   # aeBlue
    'D1': [(2, 3.0), (5, 2.0), (6, 3.0), (7, 2.0)],   # fuGFP
}

# --- Volumes -----------------------------------------------------------------------
# PCR: 25 uL Q5 reactions with 0.1 uM primers and 0.5 ng linearised template (paper,
# Methods). Primers are 1 uM, so 2.5 uL of each gives 0.1 uM in 25 uL; template is
# 0.5 ng/uL, so 1 uL gives 0.5 ng. The remaining 19 uL per reaction is master mix.
PCR_RXN_VOL = 25.0
PRIMER_VOL = 2.5
TEMPLATE_VOL = 1.0
MM_PER_RXN = 19.0
# Standard Q5 composition per 25 uL reaction (NEB): 5 uL 5X Q5 buffer, 0.5 uL 10 mM
# dNTPs (200 uM final), 0.25 uL Q5 polymerase, water to volume.
MM_BUFFER_PER_RXN = 5.0
MM_DNTP_PER_RXN = 0.5
MM_POL_PER_RXN = 0.25
MM_WATER_PER_RXN = MM_PER_RXN - MM_BUFFER_PER_RXN - MM_DNTP_PER_RXN - MM_POL_PER_RXN
MM_RXNS = 8  # 7 fragments + 1 reaction of dead volume, as set up by the operator

# DpnI digestion of residual template (paper, Methods): 19 uL water, 5 uL rCutSmart
# Buffer and 1 uL DpnI are added to the 25 uL PCR, giving 50 uL.
DPNI_WATER_VOL = 19.0
DPNI_BUFFER_VOL = 5.0
DPNI_ENZYME_VOL = 1.0

# Golden Gate: 20 uL reactions. 10 uL of that is cleaned fragments (3+2+3+2), leaving
# 2 uL 10X T4 DNA Ligase Buffer, 1 uL Golden Gate Enzyme Mix and 7 uL water.
GG_RXN_VOL = 20.0
GG_BUFFER_VOL = 2.0
GG_ENZYME_VOL = 1.0
GG_FRAGMENT_VOL = 10.0
GG_WATER_VOL = GG_RXN_VOL - GG_BUFFER_VOL - GG_ENZYME_VOL - GG_FRAGMENT_VOL

# Transformation (paper, Methods): the cleaned assembly is eluted in 10 uL water, of
# which 5 uL is transformed into 50 uL of TOP10 cells and 5 uL kept for NanoDrop
# quantification. Recovery is in 250 uL LB + 0.2% (w/v) dextrose.
ASSEMBLY_ELUTION_VOL = 10.0
TRANSFORM_DNA_VOL = 5.0
RECOVERY_VOL = 250.0

# The fragment clean-up elution volume is not given in the paper for fragments (only
# the 10 uL used for final assemblies). Fragment 2 and fragment 6 are each needed at
# 3 uL in all four assemblies (12 uL), so we elute fragments in 20 uL to leave a
# workable excess over the 12 uL maximum draw.
FRAGMENT_ELUTION_VOL = 20.0


def run(protocol: protocol_api.ProtocolContext):
    # --- Labware (loaded by the operator exactly as labelled) ----------------------
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

    # --- Reagent positions ---------------------------------------------------------
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']          # empty, filled below
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']
    lb_dextrose = tubes_15ml_1['A1']

    # Tips are unlimited; reset both racks between stages so a stage can never run dry.
    def reset_tips():
        p20.reset_tipracks()
        p300.reset_tipracks()

    def pipette_for(volume):
        """20 uL pipette for 1-20 uL, 300 uL pipette for 20-300 uL."""
        return p20 if volume <= 20 else p300

    def xfer(volume, source, dest, mix_after=None, blow_out_dest=True):
        """Single transfer with a fresh tip, so no tip is ever carried between liquids."""
        pip = pipette_for(volume)
        pip.pick_up_tip()
        pip.aspirate(volume, source)
        pip.dispense(volume, dest)
        if mix_after is not None:
            # Never ask a pipette to mix more than it can hold.
            pip.mix(mix_after[0], min(mix_after[1], pip.max_volume), dest)
        if blow_out_dest:
            pip.blow_out(dest.top())
        pip.drop_tip()

    # ==================================================================================
    # Stage 1 - PCR master mix for 8 reactions in tubes_1_5ml_1 D1
    # ==================================================================================
    protocol.comment('STAGE 1: building the Q5 PCR master mix for {} reactions '
                     'in tubes_1_5ml_1 D1.'.format(MM_RXNS))
    xfer(MM_WATER_PER_RXN * MM_RXNS, water, pcr_mm, blow_out_dest=False)
    xfer(MM_BUFFER_PER_RXN * MM_RXNS, q5_buffer, pcr_mm)
    xfer(MM_DNTP_PER_RXN * MM_RXNS, dntp, pcr_mm)
    # Polymerase is viscous and goes in last; the 152 uL master mix is then mixed with
    # the 300 uL pipette, which can move enough volume to homogenise the whole tube.
    xfer(MM_POL_PER_RXN * MM_RXNS, q5_pol, pcr_mm)
    p300.pick_up_tip()
    p300.mix(8, 100, pcr_mm)
    p300.blow_out(pcr_mm.top())
    p300.drop_tip()

    # ==================================================================================
    # Stage 2 - assemble the seven 25 uL PCRs in pcr_plate column 1
    # ==================================================================================
    protocol.comment('STAGE 2: setting up seven 25 uL Q5 PCRs in pcr_plate A1:G1 '
                     '(0.1 uM each primer, 0.5 ng linearised template).')
    reset_tips()

    # Master mix first: one tip is enough, each destination well is empty and clean.
    p20.pick_up_tip()
    for frag in sorted(FRAGMENTS):
        pcr_well = FRAGMENTS[frag][0]
        p20.aspirate(MM_PER_RXN, pcr_mm)
        p20.dispense(MM_PER_RXN, pcr_plate[pcr_well])
        p20.blow_out(pcr_plate[pcr_well].top())
    p20.drop_tip()

    # Template, then primers, with a fresh tip for every DNA source.
    for frag in sorted(FRAGMENTS):
        pcr_well, fwd_well, rev_well, template_well = FRAGMENTS[frag]
        dest = pcr_plate[pcr_well]
        xfer(TEMPLATE_VOL, template_plate[template_well], dest)
        xfer(PRIMER_VOL, primer_plate[fwd_well], dest)
        xfer(PRIMER_VOL, primer_plate[rev_well], dest, mix_after=(5, 15))
        protocol.comment(
            'Fragment {}: pcr_plate {} = {} uL master mix + {} uL template ({}) + '
            '{} uL fwd primer ({}) + {} uL rev primer ({}) = {} uL.'.format(
                frag, pcr_well, MM_PER_RXN, TEMPLATE_VOL, template_well,
                PRIMER_VOL, fwd_well, PRIMER_VOL, rev_well, PCR_RXN_VOL))

    # --- Manual step: gradient thermocycling (off-deck) -------------------------------
    protocol.comment('MANUAL STEP: seal pcr_plate A1:G1, transfer the seven reactions '
                     'to 100 uL PCR tubes in the external gradient thermocycler at the '
                     'block positions given by the AssemblyTron reactions_setup file '
                     '(the OT-2 thermocycler module has no gradient capability).')
    protocol.comment('MANUAL STEP: run 30 s at 98 C; 34-36 cycles of 10 s at 98 C, 30 s '
                     'at the AssemblyTron/j5 gradient annealing temperatures, and the '
                     'AssemblyTron extension time at 72 C; then 5 min at 72 C.')
    protocol.comment('MANUAL STEP: return the finished PCRs to their original wells in '
                     'pcr_plate A1:G1, unseal, and resume.')
    protocol.pause('Run the gradient PCR off-deck, then return the reactions to '
                   'pcr_plate A1:G1 and resume.')

    # ==================================================================================
    # Stage 3 - DpnI digestion of residual plasmid template
    # ==================================================================================
    protocol.comment('STAGE 3: DpnI digestion - adding {} uL water, {} uL rCutSmart '
                     'Buffer and {} uL DpnI to each 25 uL PCR (50 uL total).'.format(
                         DPNI_WATER_VOL, DPNI_BUFFER_VOL, DPNI_ENZYME_VOL))
    reset_tips()

    for frag in sorted(FRAGMENTS):
        dest = pcr_plate[FRAGMENTS[frag][0]]
        xfer(DPNI_WATER_VOL, water, dest)
        xfer(DPNI_BUFFER_VOL, rcutsmart, dest)
        xfer(DPNI_ENZYME_VOL, dpni, dest, mix_after=(5, 15))

    protocol.comment('MANUAL STEP: seal pcr_plate A1:G1 and incubate the digests for '
                     '30 min at 37 C, then deactivate DpnI for 20 min at 65 C.')
    protocol.comment('MANUAL STEP: clean and concentrate each digested fragment on a '
                     'Zymo DNA Clean and Concentrator-5 column to remove the polymerase, '
                     'which otherwise fills in the BsaI sticky ends. Elute each fragment '
                     'in {} uL molecular-grade water and return it to its own well in '
                     'pcr_plate A1:G1.'.format(FRAGMENT_ELUTION_VOL))
    protocol.pause('Digest with DpnI, column-clean each fragment, return the {} uL '
                   'eluates to pcr_plate A1:G1 and resume.'.format(FRAGMENT_ELUTION_VOL))

    # ==================================================================================
    # Stage 4 - four 20 uL Golden Gate assemblies
    # ==================================================================================
    protocol.comment('STAGE 4: setting up four 20 uL Golden Gate reactions in '
                     'assembly_plate A1:D1.')
    reset_tips()

    # Water and buffer first, then the fragments, then the enzyme mix last so that
    # BsaI-HFv2 and T4 ligase are only ever in a complete, buffered reaction.
    for well in ['A1', 'B1', 'C1', 'D1']:
        dest = assembly_plate[well]
        xfer(GG_WATER_VOL, water, dest)
        xfer(GG_BUFFER_VOL, t4_buffer, dest)

    for well in ['A1', 'B1', 'C1', 'D1']:
        dest = assembly_plate[well]
        for frag, volume in ASSEMBLIES[well]:
            xfer(volume, pcr_plate[FRAGMENTS[frag][0]], dest)
        protocol.comment(
            'Assembly {}: {} uL water + {} uL 10X T4 ligase buffer + {} uL fragments '
            '({}) + {} uL Golden Gate Enzyme Mix = {} uL.'.format(
                well, GG_WATER_VOL, GG_BUFFER_VOL, GG_FRAGMENT_VOL,
                ', '.join('frag {} at {} uL'.format(f, v) for f, v in ASSEMBLIES[well]),
                GG_ENZYME_VOL, GG_RXN_VOL))

    for well in ['A1', 'B1', 'C1', 'D1']:
        xfer(GG_ENZYME_VOL, gg_enzyme, assembly_plate[well], mix_after=(5, 15))

    protocol.comment('MANUAL STEP: seal assembly_plate A1:D1 and run the Golden Gate '
                     'programme (Engler et al.): 30 cycles of 1 min at 37 C and 1 min at '
                     '16 C, then 5 min at 60 C, hold at 16 C. Reactions may be cycled in '
                     'the Opentrons thermocycler module or an external thermocycler; the '
                     'protocol pauses here either way, as the paper describes.')
    protocol.comment('MANUAL STEP: clean and concentrate each 20 uL assembly on a Zymo '
                     'DNA Clean and Concentrator-5 column, elute in {} uL '
                     'molecular-grade water and return each eluate to its own well in '
                     'assembly_plate A1:D1. Keep 5 uL of each for NanoDrop '
                     'quantification; the robot transforms the other {} uL.'.format(
                         ASSEMBLY_ELUTION_VOL, TRANSFORM_DNA_VOL))
    protocol.pause('Thermocycle the Golden Gate reactions, column-clean them, return the '
                   '{} uL eluates to assembly_plate A1:D1 and resume.'.format(
                       ASSEMBLY_ELUTION_VOL))

    # ==================================================================================
    # Stage 5 - transformation into E. coli TOP10
    # ==================================================================================
    protocol.comment('STAGE 5: transforming {} uL of each cleaned assembly into 50 uL '
                     'of chemically competent E. coli TOP10.'.format(TRANSFORM_DNA_VOL))
    reset_tips()

    for well in ['A1', 'B1', 'C1', 'D1']:
        # Cells are fragile: dispense gently and mix with a few slow, small strokes.
        p20.pick_up_tip()
        p20.aspirate(TRANSFORM_DNA_VOL, assembly_plate[well])
        p20.dispense(TRANSFORM_DNA_VOL, cells_plate[well])
        p20.mix(3, 10, cells_plate[well], rate=0.5)
        p20.blow_out(cells_plate[well].top())
        p20.drop_tip()
        protocol.comment('Transformation {}: {} uL assembly {} into 50 uL TOP10 cells '
                         'in cells_plate {}.'.format(well, TRANSFORM_DNA_VOL, well, well))

    protocol.comment('MANUAL STEP: incubate the four transformation mixes in '
                     'cells_plate A1:D1 on ice for 30 min, heat shock at 42 C for 60 s, '
                     'then return them to ice for 2 min before resuming.')
    protocol.pause('Ice 30 min, heat shock 42 C for 60 s, back on ice, then return '
                   'cells_plate to slot 7 and resume for the recovery medium.')

    protocol.comment('Adding {} uL LB + 0.2% (w/v) dextrose to each transformation for '
                     'recovery.'.format(RECOVERY_VOL))
    for well in ['A1', 'B1', 'C1', 'D1']:
        p300.pick_up_tip()
        p300.aspirate(RECOVERY_VOL, lb_dextrose)
        p300.dispense(RECOVERY_VOL, cells_plate[well])
        p300.mix(3, 100, cells_plate[well], rate=0.5)
        p300.blow_out(cells_plate[well].top())
        p300.drop_tip()

    protocol.comment('MANUAL STEP: recover the transformations at 37 C for 60 min with '
                     'shaking.')
    protocol.comment('MANUAL STEP: plate 50-200 uL of each recovery, or a 10x dilution, '
                     'on LB agar with 50 ug/mL kanamycin and incubate overnight at 37 C. '
                     'Score colonies for chromoprotein expression (tsPurple from A1, '
                     'YukonOFP from B1, aeBlue from C1, fuGFP from D1).')
    protocol.comment('Run complete: four Golden Gate chromoprotein assemblies '
                     'transformed into E. coli TOP10.')
