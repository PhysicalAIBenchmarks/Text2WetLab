from opentrons import protocol_api

metadata = {
    'protocolName': 'Golden Gate Assembly of Four Chromoprotein Plasmids',
    'author': 'AssemblyTron',
    'description': 'PCR of 7 DNA fragments, DpnI digestion, and Golden Gate assembly of 4 chromoprotein expression plasmids',
    'apiLevel': '2.15'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tubes_50ml_1 = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 1, label='tubes_50ml_1')
    tubes_1_5ml_1 = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', 2, label='tubes_1_5ml_1')
    primer_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 3, label='primer_plate')
    template_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 4, label='template_plate')
    pcr_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 5, label='pcr_plate')
    assembly_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6, label='assembly_plate')
    cells_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 7, label='cells_plate')
    tubes_15ml_1 = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 8, label='tubes_15ml_1')

    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 10)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 11)

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Reagent locations
    water = tubes_50ml_1['A1']
    q5_buffer = tubes_1_5ml_1['A1']
    dntp = tubes_1_5ml_1['B1']
    q5_pol = tubes_1_5ml_1['C1']
    pcr_mm = tubes_1_5ml_1['D1']
    rcutsmart = tubes_1_5ml_1['A2']
    dpni = tubes_1_5ml_1['B2']
    t4_buffer = tubes_1_5ml_1['C2']
    gg_enzyme = tubes_1_5ml_1['D2']

    # ========== Step 1: Prepare PCR master mix ==========
    # Q5 PCR per 25 µL reaction: 5 µL 5X buffer, 0.5 µL 10 mM dNTPs, 0.25 µL polymerase, 19.25 µL water
    # For 7 reactions with 10% overage (7.7 reactions): scale volumes accordingly
    # Using 7.7× volumes: 38.5 µL buffer, 3.85 µL dNTPs, 1.925 µL polymerase, 148.25 µL water

    protocol.comment('Preparing PCR master mix (buffer, dNTPs, polymerase, water) in tubes_1_5ml_1 D1')

    p300.pick_up_tip()
    p300.aspirate(38.5, q5_buffer)
    p300.dispense(38.5, pcr_mm)
    p300.drop_tip()

    p20.pick_up_tip()
    p20.aspirate(3.85, dntp)
    p20.dispense(3.85, pcr_mm)
    p20.drop_tip()

    p20.pick_up_tip()
    p20.aspirate(1.925, q5_pol)
    p20.dispense(1.925, pcr_mm)
    p20.drop_tip()

    p300.pick_up_tip()
    p300.aspirate(148.25, water)
    p300.dispense(148.25, pcr_mm)
    p300.drop_tip()

    # ========== Step 2: Aliquot master mix to PCR wells ==========
    # 19.25 µL master mix to each of pcr_plate wells A1:G1
    protocol.comment('Distributing PCR master mix (19.25 µL each) to pcr_plate wells A1:G1')

    p20.pick_up_tip()
    for row_index in range(7):
        well = pcr_plate[f'{chr(65 + row_index)}1']
        p20.aspirate(19.25, pcr_mm)
        p20.dispense(19.25, well)
    p20.drop_tip()

    # ========== Step 3: Add forward and reverse primers ==========
    # Fragment 1: fwd primer A1, rev primer A2, template A1
    # Fragment 2: fwd primer B1, rev primer B2, template A1
    # Fragment 3: fwd primer C1, rev primer C2, template B1
    # Fragment 4: fwd primer D1, rev primer D2, template C1
    # Fragment 5: fwd primer E1, rev primer E2, template A1
    # Fragment 6: fwd primer F1, rev primer F2, template A1
    # Fragment 7: fwd primer G1, rev primer G2, template D1
    # Each primer is 1 µM, add 2.5 µL to get 0.1 µM final

    protocol.comment('Adding forward and reverse primers (2.5 µL each) to pcr_plate')

    primer_pairs = [
        ('A1', 'A2'),
        ('B1', 'B2'),
        ('C1', 'C2'),
        ('D1', 'D2'),
        ('E1', 'E2'),
        ('F1', 'F2'),
        ('G1', 'G2'),
    ]

    p20.pick_up_tip()
    for frag_index, (fwd_primer, rev_primer) in enumerate(primer_pairs):
        pcr_well = pcr_plate[f'{chr(65 + frag_index)}1']
        p20.aspirate(2.5, primer_plate[fwd_primer])
        p20.dispense(2.5, pcr_well)
        p20.aspirate(2.5, primer_plate[rev_primer])
        p20.dispense(2.5, pcr_well)
    p20.drop_tip()

    # ========== Step 4: Add templates ==========
    # Fragment 1: template A1 (tsPurple)
    # Fragment 2: template A1 (backbone)
    # Fragment 3: template B1 (YukonOFP)
    # Fragment 4: template C1 (aeBlue)
    # Fragment 5: template A1 (backbone/KanR)
    # Fragment 6: template A1 (backbone)
    # Fragment 7: template D1 (fuGFP)
    # Template concentration is 0.5 ng/µL, add 1 µL to get 0.5 ng

    protocol.comment('Adding templates (1 µL each, 0.5 ng) to pcr_plate')

    templates = ['A1', 'A1', 'B1', 'C1', 'A1', 'A1', 'D1']

    p20.pick_up_tip()
    for frag_index, template_well in enumerate(templates):
        pcr_well = pcr_plate[f'{chr(65 + frag_index)}1']
        p20.aspirate(1, template_plate[template_well])
        p20.dispense(1, pcr_well)
    p20.drop_tip()

    # ========== Step 5: Manual PCR thermocycling ==========
    protocol.comment('PCR setup complete. Operator must manually transfer pcr_plate to Bio-Rad C100 gradient thermocycler.')
    protocol.comment('PCR program: 98°C for 30 s initial denaturation, 35 cycles of (98°C 10 s, 65°C 30 s annealing, 72°C 90 s extension), 72°C 5 min final extension.')
    protocol.comment('Note: Annealing temperature 65°C and extension time 90 s are suitable for 1-3 kb fragments. Adjust based on actual fragment sizes.')
    protocol.comment('Return pcr_plate to slot 5 after thermocycling.')

    # ========== Step 6: Add DpnI digestion reagents ==========
    # Add 19 µL water, 5 µL rCutSmart buffer, 1 µL DpnI to each PCR product
    protocol.comment('Adding DpnI digestion mix to digest template DNA in pcr_plate wells A1:G1')

    p300.pick_up_tip()
    for row_index in range(7):
        well = pcr_plate[f'{chr(65 + row_index)}1']
        p300.aspirate(19, water)
        p300.dispense(19, well)
    p300.drop_tip()

    p20.pick_up_tip()
    for row_index in range(7):
        well = pcr_plate[f'{chr(65 + row_index)}1']
        p20.aspirate(5, rcutsmart)
        p20.dispense(5, well)
    p20.drop_tip()

    p20.pick_up_tip()
    for row_index in range(7):
        well = pcr_plate[f'{chr(65 + row_index)}1']
        p20.aspirate(1, dpni)
        p20.dispense(1, well)
    p20.drop_tip()

    # ========== Step 7: DpnI digestion incubation ==========
    protocol.comment('Incubating DpnI digestion reaction: 37°C for 30 min, then 65°C for 20 min for enzyme inactivation.')

    # ========== Step 8: Manual fragment cleanup ==========
    protocol.comment('Operator must remove pcr_plate and perform DNA cleanup using Zymo DNA Clean and Concentrator-5 columns:')
    protocol.comment('  1. Add equal volume of DNA Binding Buffer to each well')
    protocol.comment('  2. Transfer to spin column and centrifuge 12000g for 15 s')
    protocol.comment('  3. Discard flow-through; add 200 µL Wash Buffer to column')
    protocol.comment('  4. Centrifuge 12000g for 15 s; discard flow-through')
    protocol.comment('  5. Repeat wash step')
    protocol.comment('  6. Centrifuge empty column 12000g for 30 s')
    protocol.comment('  7. Transfer column to clean microcentrifuge tube')
    protocol.comment('  8. Add 10 µL Molecular Grade Water to column')
    protocol.comment('  9. Centrifuge 12000g for 30 s to elute purified DNA')
    protocol.comment('Return cleaned and eluted fragments (10 µL each) to pcr_plate wells A1:G1')

    # ========== Step 9: Golden Gate assembly setup ==========
    # Assemble fragments into assembly_plate wells A1:D1
    # A1 (tsPurple): frag2(3µL) + frag5(2µL) + frag6(3µL) + frag1(2µL)
    # B1 (YukonOFP): frag2(3µL) + frag5(2µL) + frag6(3µL) + frag3(2µL)
    # C1 (aeBlue): frag2(3µL) + frag5(2µL) + frag6(3µL) + frag4(2µL)
    # D1 (fuGFP): frag2(3µL) + frag5(2µL) + frag6(3µL) + frag7(2µL)

    assemblies = [
        {
            'name': 'tsPurple',
            'well': 'A1',
            'fragments': [(1, 3), (4, 2), (5, 3), (0, 2)]
        },
        {
            'name': 'YukonOFP',
            'well': 'B1',
            'fragments': [(1, 3), (4, 2), (5, 3), (2, 2)]
        },
        {
            'name': 'aeBlue',
            'well': 'C1',
            'fragments': [(1, 3), (4, 2), (5, 3), (3, 2)]
        },
        {
            'name': 'fuGFP',
            'well': 'D1',
            'fragments': [(1, 3), (4, 2), (5, 3), (6, 2)]
        },
    ]

    protocol.comment('Setting up Golden Gate assembly reactions in assembly_plate wells A1:D1')

    for assembly in assemblies:
        protocol.comment(f'Assembling {assembly["name"]} construct in assembly_plate {assembly["well"]}')

        p20.pick_up_tip()
        for frag_index, volume in assembly['fragments']:
            frag_well = pcr_plate[f'{chr(65 + frag_index)}1']
            p20.aspirate(volume, frag_well)
            p20.dispense(volume, assembly_plate[assembly['well']])
        p20.drop_tip()

    # ========== Step 10: Add Golden Gate master mix ==========
    # Each 20 µL Golden Gate reaction contains 10 µL fragments + 10 µL enzyme mix
    # Enzyme mix: 2 µL 10X T4 Ligase Buffer (1X final), 1 µL Golden Gate Enzyme Mix, 7 µL water

    protocol.comment('Adding Golden Gate master mix (2 µL 10X T4 buffer + 1 µL enzyme mix + 7 µL water) to each assembly')

    for assembly in assemblies:
        p20.pick_up_tip()
        p20.aspirate(2, t4_buffer)
        p20.dispense(2, assembly_plate[assembly['well']])
        p20.aspirate(1, gg_enzyme)
        p20.dispense(1, assembly_plate[assembly['well']])
        p20.aspirate(7, water)
        p20.dispense(7, assembly_plate[assembly['well']])
        p20.drop_tip()

    # ========== Step 11: Golden Gate thermocycler ==========
    protocol.comment('Golden Gate assembly reactions prepared (20 µL each). Operator must manually transfer assembly_plate to a thermocycler.')
    protocol.comment('Golden Gate thermocycler program:')
    protocol.comment('  20 cycles of: 37°C for 2 min (BsaI digestion), 16°C for 5 min (T4 ligase ligation)')
    protocol.comment('  Final: 60°C for 5 min (optional heat inactivation)')
    protocol.comment('Return assembly_plate to slot 6 after thermocycling.')

    # ========== Step 12: Manual transformation ==========
    protocol.comment('Golden Gate assembly complete. Operator must:')
    protocol.comment('  1. Remove assembly_plate from thermocycler')
    protocol.comment('  2. Perform column purification on each assembly (DNA Clean and Concentrator-5)')
    protocol.comment('  3. Measure DNA concentration of each assembly with NanoDrop')
    protocol.comment('  4. Transform 5-10 µL purified DNA into 50 µL E. coli TOP10 competent cells (cells_plate wells A1:D1)')
    protocol.comment('Transformation procedure:')
    protocol.comment('  - Mix DNA with competent cells, incubate on ice for 30 min')
    protocol.comment('  - Heat shock at 42°C for 60 s')
    protocol.comment('  - Place on ice for 2 min')
    protocol.comment('  - Add 250 µL LB + 0.2% (w/v) dextrose (tubes_15ml_1 A1)')
    protocol.comment('  - Recover at 37°C for 60 min')
    protocol.comment('  - Plate on LB agar with 50 µg/mL kanamycin')
    protocol.comment('  - Incubate plates at 37°C overnight')
    protocol.comment('  - Count colonies and verify by chromoprotein color expression')
