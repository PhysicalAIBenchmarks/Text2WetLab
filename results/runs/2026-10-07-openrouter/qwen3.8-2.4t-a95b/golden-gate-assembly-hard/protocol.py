"""
Golden Gate assembly of four four-fragment chromoprotein expression plasmids
with the AssemblyTron workflow on the OT-2.

Based on: Bradley et al., "AssemblyTron: flexible automation of DNA assembly
with Opentrons OT-2 lab robots", Synth. Biol. 2022, doi:10.1093/synbio/ysac032
(Golden Gate script "based on Engler et al. (8)"; methods section 2.3).

Workflow:
  1. Build a Q5 PCR master mix (buffer, dNTPs, polymerase, water) in
     tubes_1_5ml_1 D1 and dispense it into pcr_plate A1:G1.
  2. Add primers (0.1 uM final, per paper) and linearized template (0.5 ng,
     per paper) to give 25 uL PCRs for fragments 1-7.
  3. [manual] Gradient PCR in an off-deck thermocycler (the OT-2 thermocycler
     has no gradient capability - paper section 3.1).
  4. DpnI digestion of the PCRs (19 uL water + 5 uL rCutSmart + 1 uL DpnI,
     30 min 37 C, 20 min 65 C - paper section 2.3).
  5. [manual] Zymo DNA Clean & Concentrator-5 cleanup of each fragment;
     eluates returned to their pcr_plate wells.
  6. Set up four 20 uL Golden Gate reactions in assembly_plate A1:D1 with
     fragment volumes proportional to length (fixed j5/AssemblyTron design).
  7. [manual] Golden Gate thermocycling (Engler-style program).
  8. [manual] Zymo cleanup of assemblies, eluted in 10 uL water (paper).
  9. Transform eluates into 50 uL TOP10 competent cells (cells_plate A1:D1),
     30 min on ice, 60 s heat shock at 42 C, +250 uL LB + 0.2% dextrose,
     recover 60 min at 37 C, plate on LB + kanamycin (paper section 2.3).

Volume choices derived from the paper:
  * 25 uL PCR (paper 2.3): 5 uL 5X Q5 buffer (1X), 0.5 uL 10 mM dNTPs
    (0.2 mM, Q5 standard), 2.5 uL each 1 uM primer (0.1 uM final, paper),
    1 uL template at 0.5 ng/uL (0.5 ng, paper), 0.25 uL Q5 polymerase
    (0.5 U, NEB standard for 25 uL), water to 25 uL (13.25 uL).
    Master mix = 19 uL/reaction, made for 8 reactions (7 fragments + 1
    spare, as stated on the deck) = water 106 uL, buffer 40 uL, dNTPs 4 uL,
    polymerase 2 uL (152 uL total in D1).
  * DpnI step exactly as paper 2.3: +19 uL water, +5 uL rCutSmart, +1 uL
    DpnI per 25 uL PCR -> 50 uL.
  * 20 uL Golden Gate reaction (fixed design gives 3+2+3+2 = 10 uL of
    fragments). The paper does not tabulate the remaining 10 uL, so a sound
    standard choice is made here: 2 uL 10X T4 DNA Ligase Buffer (1X final),
    1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase), 7 uL water.
"""

metadata = {
    'protocolName': 'AssemblyTron Golden Gate - 4x chromoprotein plasmids',
    'author': 'OT-2 protocol',
    'description': 'PCR of 7 fragments, DpnI, cleanup, 4-part Golden Gate '
                   'assembly x4, transformation into TOP10 (per AssemblyTron '
                   'paper, doi:10.1093/synbio/ysac032).',
}

requirements = {'apiLevel': '2.13'}


def run(protocol):
    protocol.set_rail_lights(True)

    # ---- labware (fixed deck) ----
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

    # ---- reagent locations ----
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']      # 5X Q5 reaction buffer
    dntp = tubes_1_5ml_1['B1']           # 10 mM dNTPs
    q5_pol = tubes_1_5ml_1['C1']         # Q5 High-Fidelity DNA Polymerase
    pcr_mm = tubes_1_5ml_1['D1']         # empty at start -> master mix here
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']      # 10X T4 DNA Ligase Buffer
    gg_enzyme = tubes_1_5ml_1['D2']      # Golden Gate Enzyme Mix
    lb_dextrose = tubes_15ml_1['A1']     # LB + 0.2% (w/v) dextrose

    # ---- fixed j5/AssemblyTron design ----
    # fragment number: (pcr well, fwd primer, rev primer, template well)
    fragments = {
        1: ('A1', 'A1', 'A2', 'A1'),   # tsPurple chromoprotein
        2: ('B1', 'B1', 'B2', 'A1'),   # backbone
        3: ('C1', 'C1', 'C2', 'B1'),   # YukonOFP chromoprotein
        4: ('D1', 'D1', 'D2', 'C1'),   # aeBlue chromoprotein
        5: ('E1', 'E1', 'E2', 'A1'),   # backbone / KanR
        6: ('F1', 'F1', 'F2', 'A1'),   # backbone
        7: ('G1', 'G1', 'G2', 'D1'),   # fuGFP chromoprotein
    }
    pcr_wells = [pcr_plate[fragments[f][0]] for f in range(1, 8)]

    # assemblies: well -> [(fragment number, volume uL), ...], 20 uL total
    # (fragment volumes from the fixed design; reagents make up the rest:
    #  7 uL water + 2 uL 10X T4 buffer + 1 uL GG enzyme mix)
    assemblies = {
        'A1': [(2, 3.0), (5, 2.0), (6, 3.0), (1, 2.0)],   # tsPurple
        'B1': [(2, 3.0), (5, 2.0), (6, 3.0), (3, 2.0)],   # YukonOFP
        'C1': [(2, 3.0), (5, 2.0), (6, 3.0), (4, 2.0)],   # aeBlue
        'D1': [(2, 3.0), (5, 2.0), (6, 3.0), (7, 2.0)],   # fuGFP
    }

    # ==================================================================
    # STEP 1 - PCR master mix in tubes_1_5ml_1 D1 (for 8 reactions)
    # 19 uL/reaction: 13.25 uL water + 5 uL 5X Q5 buffer + 0.5 uL 10 mM
    # dNTPs + 0.25 uL Q5 polymerase. x8 = 106 + 40 + 4 + 2 = 152 uL.
    # ==================================================================
    protocol.comment('--- STEP 1: build Q5 PCR master mix (8 reactions) '
                       'in tubes_1_5ml_1 D1 ---')
    p20.reset_tipracks()
    p300.reset_tipracks()
    p300.transfer(106, water, pcr_mm, new_tip='once')            # water
    p300.transfer(40, q5_buffer, pcr_mm, new_tip='once')         # 5X buffer
    p20.transfer(4, dntp, pcr_mm, new_tip='once')                # dNTPs
    p20.transfer(2, q5_pol, pcr_mm, new_tip='once')              # Q5 pol
    p300.pick_up_tip()
    p300.mix(5, 100, pcr_mm)
    p300.drop_tip()

    # ==================================================================
    # STEP 2 - dispense master mix, primers and template -> 25 uL PCRs
    # ==================================================================
    protocol.comment('--- STEP 2: set up 7 x 25 uL PCRs in pcr_plate '
                       'A1:G1 ---')
    p20.reset_tipracks()
    # 19 uL master mix per reaction (p20; one tip, source is a common mix)
    p20.transfer(19, pcr_mm, pcr_wells, new_tip='once')

    # 2.5 uL of each 1 uM primer -> 0.1 uM final (paper 2.3);
    # fresh tip per primer to avoid cross-contamination
    for f in range(1, 8):
        pcr_w, fwd, rev, _ = fragments[f]
        p20.transfer(2.5, primer_plate[fwd], pcr_plate[pcr_w],
                     new_tip='always')
        p20.transfer(2.5, primer_plate[rev], pcr_plate[pcr_w],
                     new_tip='always')

    # 1 uL of 0.5 ng/uL linearized template -> 0.5 ng (paper 2.3)
    for f in range(1, 8):
        pcr_w, _, _, tmpl = fragments[f]
        p20.transfer(1, template_plate[tmpl], pcr_plate[pcr_w],
                     new_tip='always')

    # mix each 25 uL reaction
    p20.reset_tipracks()
    for w in pcr_wells:
        p20.pick_up_tip()
        p20.mix(3, 15, w)
        p20.drop_tip()

    # ==================================================================
    # STEP 3 - [manual] gradient PCR off-deck (paper 2.3 & 3.1: the OT-2
    # thermocycler cannot do the annealing gradient, so tubes are moved to
    # a Bio-Rad C100 gradient thermocycler; pcr_plate column 1 stands in
    # for the 100 uL PCR tubes)
    # ==================================================================
    protocol.comment(
        'MANUAL - gradient PCR: seal pcr_plate / move the PCR tubes to a '
        'gradient thermocycler (e.g. Bio-Rad C100) positioned per the '
        'AssemblyTron instructions file. Run: 98 C 30 s; then 36 cycles of '
        '[98 C 10 s, 30 s at the AssemblyTron/j5 gradient annealing '
        'temperature for each fragment, 72 C extension for the '
        'AssemblyTron-calculated time (~20-30 s/kb)]; final extension 72 C '
        '5 min; hold 4 C. (Paper allows 34 or 36 cycles; 36 chosen as the '
        'more robust option for 4-part assembly fragments.) Optionally take '
        'a sample of each reaction for gel electrophoresis. Return the '
        'reactions to the OT-2 deck (pcr_plate A1:G1) and resume.')
    protocol.pause('Off-deck gradient PCR - see comment. Resume when the '
                   'PCR products are back in pcr_plate A1:G1.')

    # ==================================================================
    # STEP 4 - DpnI digestion to destroy residual methylated template
    # (paper 2.3: +19 uL water, +5 uL rCutSmart Buffer, +1 uL DpnI;
    #  30 min 37 C, then 65 C 20 min inactivation)
    # ==================================================================
    protocol.comment('--- STEP 4: DpnI digestion of the 7 PCRs ---')
    p20.reset_tipracks()
    p20.transfer(19, water, pcr_wells, new_tip='once')
    p20.transfer(5, rcutsmart, pcr_wells, new_tip='once')
    p20.transfer(1, dpni, pcr_wells, new_tip='once')
    # mix each 50 uL digestion
    for w in pcr_wells:
        p20.pick_up_tip()
        p20.mix(5, 20, w)
        p20.drop_tip()

    protocol.comment(
        'MANUAL - DpnI incubation: seal pcr_plate and incubate 30 min at '
        '37 C, then inactivate DpnI 20 min at 65 C (thermocycler block or '
        'heat block; the robot cannot thermocycle this plate). Each well '
        'now holds 50 uL.')
    protocol.pause('DpnI: 30 min 37 C + 20 min 65 C off-deck. Resume when '
                   'done and the plate is back at ~room temperature.')

    # ==================================================================
    # STEP 5 - [manual] Zymo column cleanup of each fragment
    # Paper 2.3: DNA Clean and Concentrator-5, water elution. The paper
    # elutes in 10 uL, but fragments 2 and 6 each donate 3 uL to four
    # assemblies (12 uL total), so 15 uL elutions are specified here -
    # a sound deviation guaranteeing enough cleaned fragment plus dead
    # volume.
    # ==================================================================
    protocol.comment(
        'MANUAL - fragment cleanup: clean and concentrate each of the 7 '
        'DpnI-treated fragments (50 uL each) with a Zymo DNA Clean & '
        'Concentrator-5 column per the manufacturer protocol (binding '
        'buffer, 2 washes) to remove polymerase, which interferes with '
        'Golden Gate (paper 3.3). Elute each fragment in 15 uL '
        'nuclease-free water (15 uL rather than the paper\'s 10 uL because '
        'fragments 2 and 6 must each supply 4 x 3 uL = 12 uL to the four '
        'assemblies). Return each eluate to its original well pcr_plate '
        'A1:G1 and resume.')
    protocol.pause('Zymo cleanup of fragments 1-7; eluates (15 uL each) '
                   'returned to pcr_plate A1:G1.')

    # ==================================================================
    # STEP 6 - Golden Gate assembly setup (20 uL reactions, Engler-style)
    # assembly_plate A1:D1. Reagents first, then fragments proportional to
    # length (fixed design), enzyme mix last.
    # ==================================================================
    protocol.comment('--- STEP 6: set up 4 x 20 uL Golden Gate reactions '
                       'in assembly_plate A1:D1 ---')
    p20.reset_tipracks()
    asm_wells = [assembly_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]

    # 7 uL water per reaction (choice documented in the module docstring)
    p20.transfer(7, water, asm_wells, new_tip='once')
    # 2 uL 10X T4 DNA Ligase Buffer -> 1X final
    p20.transfer(2, t4_buffer, asm_wells, new_tip='once')
    # fragments: shared fragments (2, 5, 6) distributed with one tip each
    # (same source -> different destinations is contamination-safe);
    # the unique chromoprotein fragment gets a fresh tip per assembly.
    for frag, vol in [(2, 3.0), (5, 2.0), (6, 3.0)]:
        src = pcr_plate[fragments[frag][0]]
        p20.transfer(vol, src, asm_wells, new_tip='once')
    for well_name, frags in assemblies.items():
        chromo_frag, chromo_vol = frags[3]
        p20.transfer(chromo_vol, pcr_plate[fragments[chromo_frag][0]],
                     assembly_plate[well_name], new_tip='always')
    # 1 uL Golden Gate Enzyme Mix (BsaI-HFv2 + T4 ligase) last, then mix
    p20.transfer(1, gg_enzyme, asm_wells, new_tip='once',
                 mix_after=(5, 15))

    # ==================================================================
    # STEP 7 - [manual] Golden Gate thermocycling (paper 3.3: run in the
    # Opentrons thermocycler module; the deck layout here has no module
    # slot free, so this is recorded as a manual/off-deck step). Program
    # based on Engler et al., as the AssemblyTron GG script is.
    # ==================================================================
    protocol.comment(
        'MANUAL - Golden Gate thermocycling: seal assembly_plate and run '
        'in a thermocycler (Opentrons thermocycler module if available): '
        '30 cycles of [37 C 1 min, 16 C 1 min], then 60 C 5 min (BsaI/'
        'ligase heat inactivation), hold 4 C (program per Engler et al., '
        'on which the AssemblyTron Golden Gate script is based; 30 cycles '
        'suit a 4-fragment one-pot assembly). Return the plate to the deck '
        'and resume.')
    protocol.pause('Golden Gate thermocycling (30 x 37 C/16 C, 60 C 5 min, '
                   'hold 4 C). Resume when complete.')

    # ==================================================================
    # STEP 8 - [manual] cleanup of the four assemblies (paper 2.3:
    # Zymo DNA Clean and Concentrator-5, elute in 10 uL molecular grade
    # water; eluates transformed into 50 uL TOP10)
    # ==================================================================
    protocol.comment(
        'MANUAL - assembly cleanup: clean and concentrate each 20 uL '
        'Golden Gate reaction with a Zymo DNA Clean & Concentrator-5 '
        'column and elute in 10 uL molecular grade water (paper 2.3). '
        'Return each 10 uL eluate to its assembly_plate well A1:D1 and '
        'resume. (The paper reserves 5 uL for NanoDrop quantification for '
        'CFU/ug calculations; here the full 10 uL eluate is transformed - '
        'quantify a separate aliquot if transformation efficiencies are '
        'needed.)')
    protocol.pause('Zymo cleanup of the 4 assemblies; 10 uL eluates '
                   'returned to assembly_plate A1:D1.')

    # ==================================================================
    # STEP 9 - transformation into E. coli TOP10 (paper 2.3)
    # ==================================================================
    protocol.comment('--- STEP 9: transformation into TOP10 (cells_plate '
                       'A1:D1) ---')
    p20.reset_tipracks()
    p300.reset_tipracks()
    cell_wells = [cells_plate[w] for w in ['A1', 'B1', 'C1', 'D1']]
    for src, dst in zip(asm_wells, cell_wells):
        # gentle mix - competent cells are shear-sensitive
        p20.transfer(10, src, dst, new_tip='always', mix_after=(3, 10))

    protocol.comment(
        'MANUAL - transformation incubations: keep cells_plate A1:D1 on ice '
        '30 min, heat shock 42 C for 60 s, then return to ice (~2 min). '
        '(Paper 2.3: 30 min on ice, 60 s at 42 C.)')
    protocol.pause('Ice 30 min -> 42 C 60 s heat shock -> back on ice. '
                   'Resume with the plate back on the deck (slot 7).')

    # recovery medium: 250 uL LB + 0.2% dextrose per well (paper 2.3)
    p300.reset_tipracks()
    p300.transfer(250, lb_dextrose, cell_wells, new_tip='always',
                  mix_after=(3, 150))

    protocol.comment(
        'MANUAL - recovery and plating: incubate cells_plate A1:D1 at 37 C '
        'for 60 min with shaking (recovery in LB + 0.2% dextrose, paper '
        '2.3). Then plate 50-200 uL of each culture (neat or a 10x '
        'dilution, depending on expected efficiency) onto LB agar + '
        'kanamycin 50 ug/mL (fragment 5 carries KanR) and incubate at 37 C '
        'overnight. Score colonies by chromoprotein colour (purple, '
        'orange/Yukon, blue, green) and count CFU.')

    protocol.set_rail_lights(False)
    protocol.comment('Protocol complete. Remove plates; final tip state: '
                       'no tips on either pipette.')
