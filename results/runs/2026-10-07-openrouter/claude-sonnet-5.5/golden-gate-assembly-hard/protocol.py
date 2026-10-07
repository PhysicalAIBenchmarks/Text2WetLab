from opentrons import protocol_api

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: four 4-fragment chromoprotein plasmids',
    'description': 'PCR of 7 fragments, DpnI, clean-up, Golden Gate assembly and TOP10 transformation (OT-2).',
    'apiLevel': '2.13',
}

# ---- Design (fixed) ---------------------------------------------------------
# fragment: (pcr well, fwd primer well, rev primer well, template well)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1'),
    2: ('B1', 'B1', 'B2', 'A1'),
    3: ('C1', 'C1', 'C2', 'B1'),
    4: ('D1', 'D1', 'D2', 'C1'),
    5: ('E1', 'E1', 'E2', 'A1'),
    6: ('F1', 'F1', 'F2', 'A1'),
    7: ('G1', 'G1', 'G2', 'D1'),
}
# assembly well: [(fragment, uL of cleaned fragment)]
ASSEMBLIES = {
    'A1': [(2, 3), (5, 2), (6, 3), (1, 2)],
    'B1': [(2, 3), (5, 2), (6, 3), (3, 2)],
    'C1': [(2, 3), (5, 2), (6, 3), (4, 2)],
    'D1': [(2, 3), (5, 2), (6, 3), (7, 2)],
}

# ---- PCR (paper: 25 uL reactions, 0.1 uM primers, 0.5 ng template, Q5) -------
PCR_VOL = 25.0
PRIMER_STOCK_UM = 1.0
PRIMER_FINAL_UM = 0.1
PRIMER_VOL = PCR_VOL * PRIMER_FINAL_UM / PRIMER_STOCK_UM   # 2.5 uL each
TEMPLATE_VOL = 1.0                                         # 0.5 ng at 0.5 ng/uL
# Q5 recipe scaled to 25 uL (NEB): 1X buffer, 200 uM dNTP, 0.02 U/uL polymerase
BUF_VOL = PCR_VOL / 5.0       # 5 uL of 5X buffer
DNTP_VOL = 0.5                # 10 mM -> 200 uM
POL_VOL = 0.25                # 0.5 uL per 50 uL reaction
WATER_VOL = PCR_VOL - BUF_VOL - DNTP_VOL - POL_VOL - 2 * PRIMER_VOL - TEMPLATE_VOL  # 13.25
MM_REACTIONS = 8              # master mix for 8 reactions (7 used, 1 overage)
MM_PER_RXN = BUF_VOL + DNTP_VOL + POL_VOL + WATER_VOL      # 19 uL

# ---- DpnI (paper): 19 uL water + 5 uL rCutSmart + 1 uL DpnI per PCR ---------
DPN_WATER, DPN_BUF, DPN_ENZ = 19.0, 5.0, 1.0

# ---- Golden Gate (20 uL): 1X T4 ligase buffer, 1 uL enzyme mix, 10 uL fragments
GG_VOL = 20.0
GG_BUF = 2.0
GG_ENZ = 1.0
GG_FRAG_TOTAL = 10.0
GG_WATER = GG_VOL - GG_BUF - GG_ENZ - GG_FRAG_TOTAL        # 7 uL

# ---- Transformation (paper) --------------------------------------------------
CLEAN_ELUTE_FRAG = 20.0  # uL elution for fragment clean-up (see comment below)
CLEAN_ELUTE_GG = 10.0    # paper: 10 uL elution of cleaned Golden Gate reaction
DNA_TO_CELLS = 5.0       # paper: 5 uL to cells, other 5 uL kept for NanoDrop
LB_VOL = 250.0


def run(protocol: protocol_api.ProtocolContext):
    tubes50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes15e = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tips20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])

    water = tubes50['A1']
    q5_buffer = tubes15e['A1']
    dntp = tubes15e['B1']
    q5_pol = tubes15e['C1']
    pcr_mm = tubes15e['D1']
    rcutsmart = tubes15e['A2']
    dpni = tubes15e['B2']
    t4_buffer = tubes15e['C2']
    gg_enzyme = tubes15e['D2']
    lb = tubes15['A1']

    def src(w):
        return w.bottom(2)

    # =========================================================================
    # 1. PCR master mix (buffer, dNTPs, polymerase, water) for 8 reactions
    # =========================================================================
    protocol.comment('STEP 1: Prepare Q5 PCR master mix for 8 reactions in tubes_1_5ml_1 D1 '
                     '(per reaction: 5 uL 5X buffer, 0.5 uL 10 mM dNTP, 0.25 uL Q5, 13.25 uL water).')
    p300.pick_up_tip()
    p300.aspirate(WATER_VOL * MM_REACTIONS, src(water))
    p300.dispense(WATER_VOL * MM_REACTIONS, pcr_mm.bottom(2))
    p300.drop_tip()

    p300.pick_up_tip()
    p300.aspirate(BUF_VOL * MM_REACTIONS, src(q5_buffer))
    p300.dispense(BUF_VOL * MM_REACTIONS, pcr_mm.bottom(2))
    p300.drop_tip()

    p20.pick_up_tip()
    p20.aspirate(DNTP_VOL * MM_REACTIONS, src(dntp))
    p20.dispense(DNTP_VOL * MM_REACTIONS, pcr_mm.bottom(2))
    p20.drop_tip()

    # polymerase last (in glycerol), mixed in with a fresh tip
    p20.pick_up_tip()
    p20.aspirate(POL_VOL * MM_REACTIONS, src(q5_pol))
    p20.dispense(POL_VOL * MM_REACTIONS, pcr_mm.bottom(2))
    p20.drop_tip()

    p300.pick_up_tip()
    p300.mix(6, 100, pcr_mm.bottom(2))
    p300.drop_tip()

    # =========================================================================
    # 2. PCR setup: master mix, primers, template (25 uL each) in pcr_plate
    # =========================================================================
    protocol.comment('STEP 2: Dispense 19 uL master mix, 2.5 uL each primer (1 uM -> 0.1 uM) and '
                     '1 uL template (0.5 ng) into pcr_plate A1:G1.')
    p20.pick_up_tip()
    for frag, (pw, fw, rw, tw) in FRAGMENTS.items():
        p20.aspirate(MM_PER_RXN, src(pcr_mm))
        p20.dispense(MM_PER_RXN, pcr_plate[pw].bottom(1))
    p20.drop_tip()

    for frag, (pw, fw, rw, tw) in FRAGMENTS.items():
        dest = pcr_plate[pw]
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, primer_plate[fw].bottom(1))
        p20.dispense(PRIMER_VOL, dest.bottom(1))
        p20.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(PRIMER_VOL, primer_plate[rw].bottom(1))
        p20.dispense(PRIMER_VOL, dest.bottom(1))
        p20.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, template_plate[tw].bottom(0.5))
        p20.dispense(TEMPLATE_VOL, dest.bottom(1))
        p20.mix(3, 15, dest.bottom(1))
        p20.drop_tip()

    # =========================================================================
    # 3. Thermocycling of PCRs (off-robot, gradient needed)
    # =========================================================================
    protocol.comment('STEP 3 (manual): Seal pcr_plate A1:G1 (transfer the 25 uL reactions to 100 uL PCR tubes) and '
                     'run in a gradient thermocycler: 98 C 30 s; 34 cycles of [98 C 10 s, annealing 30 s at the '
                     'AssemblyTron/j5 gradient temperature for each fragment, 72 C for the AssemblyTron extension time]; '
                     'final extension 72 C 5 min; hold 4 C. Return reactions to pcr_plate A1:G1 and unseal.')
    protocol.pause('Run PCR in thermocycler, then return and unseal the PCR reactions.')

    # =========================================================================
    # 4. DpnI digestion of template
    # =========================================================================
    protocol.comment('STEP 4: DpnI digestion - add 19 uL water, 5 uL rCutSmart buffer and 1 uL DpnI to each PCR (50 uL total).')
    wells = [FRAGMENTS[f][0] for f in FRAGMENTS]
    # reagents are dispensed above the liquid so one tip per reagent can be shared
    for reagent, vol in ((water, DPN_WATER), (rcutsmart, DPN_BUF), (dpni, DPN_ENZ)):
        p20.pick_up_tip()
        for w in wells:
            p20.aspirate(vol, src(reagent))
            p20.dispense(vol, pcr_plate[w].top(-2))
        p20.drop_tip()
    for w in wells:
        p300.pick_up_tip()
        p300.mix(3, 30, pcr_plate[w].bottom(1))
        p300.drop_tip()

    protocol.comment('STEP 4b (off-robot): seal pcr_plate; incubate 30 min at 37 C (DpnI digestion), then '
                     'heat-inactivate 20 min at 65 C (thermocycler/heat block). Unseal afterwards.')
    protocol.pause('Incubate DpnI digestion 30 min 37 C then 20 min 65 C; unseal.')

    # =========================================================================
    # 5. Clean-up of fragments (polymerase interferes with Golden Gate)
    # =========================================================================
    protocol.comment('STEP 5 (manual): Remove the 50 uL DpnI-treated fragments from pcr_plate A1:G1 and clean/concentrate '
                     'each on a Zymo DNA Clean & Concentrator-5 column (the paper cleans fragments because residual '
                     'polymerase fills in sticky ends). Elution volume is not given for fragments in the paper; I chose '
                     '20 uL water so >=12 uL of the backbone fragments is available (the design takes up to 12 uL '
                     'of fragments 2 and 6). Return cleaned fragments to their pcr_plate wells A1:G1.')
    protocol.pause('Clean up fragments (column, elute in 20 uL) and return them to pcr_plate A1:G1.')

    # =========================================================================
    # 6. Golden Gate reactions (20 uL) in assembly_plate
    # =========================================================================
    protocol.comment('STEP 6: Golden Gate set-up, 20 uL per reaction: 7 uL water, 2 uL 10X T4 ligase buffer, '
                     '10 uL cleaned fragments (3/2/3/2 uL, proportional to length), 1 uL Golden Gate enzyme mix (BsaI-HFv2 + T4 ligase).')
    asm_wells = list(ASSEMBLIES)
    for reagent, vol in ((water, GG_WATER), (t4_buffer, GG_BUF)):
        p20.pick_up_tip()
        for aw in asm_wells:
            p20.aspirate(vol, src(reagent))
            p20.dispense(vol, assembly_plate[aw].top(-2))
        p20.drop_tip()

    for aw, parts in ASSEMBLIES.items():
        dest = assembly_plate[aw]
        for frag, vol in parts:
            p20.pick_up_tip()
            p20.aspirate(vol, pcr_plate[FRAGMENTS[frag][0]].bottom(0.5))
            p20.dispense(vol, dest.bottom(1))
            p20.drop_tip()
        # enzyme mix last, mixed in with the same tip
        p20.pick_up_tip()
        p20.aspirate(GG_ENZ, src(gg_enzyme))
        p20.dispense(GG_ENZ, dest.bottom(1))
        p20.mix(4, 10, dest.bottom(1))
        p20.drop_tip()

    protocol.comment('STEP 7: Seal assembly_plate and run Golden Gate on the thermocycler module (lid 40 C+): '
                     '30 cycles of [37 C 5 min, 16 C 5 min], then 60 C 5 min (enzyme inactivation), hold 4 C. '
                     'The paper does not give the cycling conditions, so these are the standard NEB/Engler '
                     'BsaI-HFv2 Golden Gate cycling conditions.')
    protocol.pause('Run Golden Gate thermocycler program, then unseal assembly_plate.')

    # =========================================================================
    # 8. Clean-up of assemblies and transformation
    # =========================================================================
    protocol.comment('STEP 8 (manual): Clean and concentrate each Golden Gate reaction on a Zymo DNA Clean & Concentrator-5 '
                     'column and elute in 10 uL water (paper); return the eluates to assembly_plate A1:D1.')
    protocol.pause('Clean up Golden Gate reactions (elute 10 uL) and return to assembly_plate A1:D1.')

    protocol.comment('STEP 9: Transformation - 5 uL of each 10 uL eluate into 50 uL TOP10 cells '
                     '(remaining 5 uL is for NanoDrop quantification).')
    for aw, cw in zip(asm_wells, ['A1', 'B1', 'C1', 'D1']):
        p20.pick_up_tip()
        p20.aspirate(DNA_TO_CELLS, assembly_plate[aw].bottom(0.5))
        p20.dispense(DNA_TO_CELLS, cells_plate[cw].bottom(1))
        p20.drop_tip()

    protocol.comment('STEP 9a (off-deck): keep cells_plate on ice 30 min, then heat shock 42 C for 60 s.')
    protocol.pause('Incubate cells on ice 30 min, then heat shock at 42 C for 60 s; return to deck.')

    protocol.comment('STEP 9b: Add 250 uL LB + 0.2% dextrose (catabolite repression) to each transformation.')
    for cw in ['A1', 'B1', 'C1', 'D1']:
        p300.pick_up_tip()
        p300.aspirate(LB_VOL, lb.bottom(2))
        p300.dispense(LB_VOL, cells_plate[cw].bottom(2))
        p300.drop_tip()

    protocol.comment('STEP 9c (off-deck): recover 60 min at 37 C. Then plate 50-200 uL (or a 10x dilution) on '
                     'LB + 50 ug/mL kanamycin agar and incubate at 37 C overnight.')
