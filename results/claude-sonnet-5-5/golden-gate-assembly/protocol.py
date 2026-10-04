from opentrons import protocol_api
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': 'AssemblyTron Golden Gate: four 4-fragment chromoprotein plasmids',
    'apiLevel': '2.15',
}

# Fragment -> (PCR well, fwd primer, rev primer, template well)
FRAGMENTS = {
    1: ('A1', 'A1', 'A2', 'A1'),
    2: ('B1', 'B1', 'B2', 'A1'),
    3: ('C1', 'C1', 'C2', 'B1'),
    4: ('D1', 'D1', 'D2', 'C1'),
    5: ('E1', 'E1', 'E2', 'A1'),
    6: ('F1', 'F1', 'F2', 'A1'),
    7: ('G1', 'G1', 'G2', 'D1'),
}
# Assembly well -> [(fragment, volume uL)]
ASSEMBLIES = {
    'A1': [(2, 3), (5, 2), (6, 3), (1, 2)],
    'B1': [(2, 3), (5, 2), (6, 3), (3, 2)],
    'C1': [(2, 3), (5, 2), (6, 3), (4, 2)],
    'D1': [(2, 3), (5, 2), (6, 3), (7, 2)],
}
CELL_WELLS = ['A1', 'B1', 'C1', 'D1']

# PCR (paper: 25 uL, 0.1 uM primers from 1 uM stocks, 0.5 ng template from 0.5 ng/uL)
PCR_VOL = 25
PRIMER_VOL = 2.5
TEMPLATE_VOL = 1
MM_PER_RXN = PCR_VOL - 2 * PRIMER_VOL - TEMPLATE_VOL  # 19 uL
# Per-reaction master mix (Q5 standard 1X recipe, my choice; paper gives none):
# 5 uL 5X buffer, 0.5 uL 10 mM dNTP (200 uM), 0.25 uL Q5, 13.25 uL water
MM_N = 8  # tube D1 is made for 8 reactions
MM_BUFFER, MM_DNTP, MM_POL = 5 * MM_N, 0.5 * MM_N, 0.25 * MM_N
MM_WATER = (MM_PER_RXN - 5 - 0.5 - 0.25) * MM_N  # 106 uL

# DpnI digest (paper): 19 uL water + 5 uL rCutSmart + 1 uL DpnI per 25 uL PCR
# Golden Gate 20 uL: 10 uL fragments (sum of volumes), 2 uL 10X T4 buffer,
# 2 uL enzyme mix (NEB-recommended amount; paper doesn't state), 6 uL water.
GG_BUFFER, GG_ENZYME = 2, 2


def run(protocol: protocol_api.ProtocolContext):
    tubes50 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes15e = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes15 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')
    tr20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tr300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tr20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tr300])

    water = tubes50['A1']
    q5_buffer, dntp, q5_pol, pcr_mm = (tubes15e[w] for w in ('A1', 'B1', 'C1', 'D1'))
    rcutsmart, dpni, t4_buffer, gg_enzyme = (tubes15e[w] for w in ('A2', 'B2', 'C2', 'D2'))
    lb = tubes15['A1']

    def pick(p):
        try:
            p.pick_up_tip()
        except OutOfTipsError:
            p.reset_tipracks()
            p.pick_up_tip()

    def move(p, vol, src, dst, mix_after=0, new_tip=True):
        """Single transfer with a fresh tip; blow out and touch tip to avoid carry-over."""
        pick(p)
        p.aspirate(vol, src)
        p.dispense(vol, dst)
        if mix_after:
            p.mix(3, mix_after, dst)
        p.blow_out(dst.top() if mix_after == 0 else dst)
        p.drop_tip()

    pcr_wells = [pcr[v[0]] for v in FRAGMENTS.values()]

    # ---- 1. PCR master mix in tube D1 (8 reactions) ----
    protocol.comment('Step 1: make PCR master mix (5X Q5 buffer, dNTPs, Q5 polymerase, water) for 8 reactions in tube D1')
    move(p300, MM_WATER, water, pcr_mm)
    move(p300, MM_BUFFER, q5_buffer, pcr_mm)
    move(p20, MM_DNTP, dntp, pcr_mm)
    move(p20, MM_POL, q5_pol, pcr_mm)
    pick(p300)
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # ---- 2. PCR set-up ----
    protocol.comment('Step 2: dispense 19 uL master mix, 2.5 uL each primer (0.1 uM final) and 1 uL template (0.5 ng) per 25 uL PCR')
    for frag, (pw, fw, rv, tp) in FRAGMENTS.items():
        dest = pcr[pw]
        move(p20, MM_PER_RXN, pcr_mm, dest)
        move(p20, PRIMER_VOL, primer[fw], dest)
        move(p20, PRIMER_VOL, primer[rv], dest)
        move(p20, TEMPLATE_VOL, template[tp], dest, mix_after=10)

    protocol.comment('Seal pcr_plate. Move PCR tubes/plate by hand to a gradient thermocycler (annealing temps and '
                     'extension time from AssemblyTron/j5; thermocycler cannot be done by the OT-2 gradient-wise). '
                     'Cycling: 98 C 30 s; 34-36 cycles of 98 C 10 s, annealing 30 s, 72 C extension; final 72 C 5 min.')
    protocol.pause('Run the PCR off-deck, then return the unsealed plate to slot 5 and resume.')

    # ---- 3. DpnI digestion ----
    protocol.comment('Step 3: DpnI digestion of template: add 19 uL water, 5 uL rCutSmart, 1 uL DpnI to each 25 uL PCR')
    for w in pcr_wells:
        move(p20, 19, water, w)
        move(p20, 5, rcutsmart, w)
        move(p20, 1, dpni, w, mix_after=15)
    protocol.comment('Seal pcr_plate; incubate 30 min at 37 C then heat-inactivate 20 min at 65 C (thermocycler block).')
    protocol.pause('After DpnI digest/inactivation, unseal the plate. Clean and concentrate each fragment with a '
                   'column kit (Zymo DNA Clean & Concentrator-5; polymerase must be removed). Elute in 15 uL water '
                   '(assumption: fragments 2 and 6 need 12 uL each, more than the 10 uL elution in the paper) and '
                   'return the cleaned fragments to their pcr_plate wells A1:G1. Then resume.')

    # ---- 4. Golden Gate assembly ----
    protocol.comment('Step 4: Golden Gate reactions (20 uL): fragments proportional to length, 2 uL 10X T4 ligase buffer, '
                     '2 uL BsaI-HFv2/T4 ligase mix, water to 20 uL')
    for aw, parts in ASSEMBLIES.items():
        dest = assembly[aw]
        frag_total = sum(v for _, v in parts)
        water_vol = 20 - frag_total - GG_BUFFER - GG_ENZYME
        move(p20, water_vol, water, dest)
        move(p20, GG_BUFFER, t4_buffer, dest)
        for frag, vol in parts:
            move(p20, vol, pcr[FRAGMENTS[frag][0]], dest)
        move(p20, GG_ENZYME, gg_enzyme, dest, mix_after=10)

    protocol.comment('Seal assembly_plate and run Golden Gate on the OT-2 thermocycler module (my choice, after Engler '
                     'et al.): lid 85 C, 30 cycles of 37 C 5 min / 16 C 5 min, then 60 C 5 min final digest/inactivation, hold 4 C.')
    protocol.comment('Clean and concentrate each assembly with a column (Zymo DNA Clean & Concentrator-5), eluting in 15 uL '
                     'water; place the eluates back in assembly_plate A1:D1.')
    protocol.pause('Complete the thermocycler run and assembly clean-up (elute 15 uL), unseal and resume.')

    # ---- 5. Transformation ----
    protocol.comment('Step 5: transform 10 uL of each cleaned assembly into 50 uL TOP10 cells (5 uL left for quantification)')
    for aw, cw in zip(ASSEMBLIES, CELL_WELLS):
        move(p20, 10, assembly[aw], cells[cw], mix_after=0)
    protocol.comment('Seal cells_plate and incubate 30 min on ice.')
    protocol.pause('Incubate on ice 30 min, heat shock at 42 C for 60 s, return to ice briefly, place on deck and resume.')

    protocol.comment('Step 6: add 250 uL LB + 0.2% dextrose to each transformation')
    for cw in CELL_WELLS:
        move(p300, 250, lb, cells[cw], mix_after=0)
    protocol.comment('Seal cells_plate and recover 60 min at 37 C; then plate 50-200 uL (or 10X dilution) on LB + '
                     '50 ug/mL kanamycin agar and incubate at 37 C overnight.')
