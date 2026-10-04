from opentrons import protocol_api

metadata = {
    'apiLevel': '2.15',
    'protocolName': 'APEX Protocol 1: Heat Shock Transformation',
    'description': 'Automated heat shock transformation of 8 plasmids into E. coli DH5α using OT-2 thermocycler',
    'author': 'APEX'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plasmid_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 1, label='plasmid_plate')
    soc_reservoir = protocol.load_labware('nest_12_reservoir_15ml', 2, label='soc_reservoir')

    # Load thermocycler module with transformation plate
    tc = protocol.load_module('thermocycler')
    transformation_plate = tc.load_labware('biorad_96_wellplate_200ul_pcr', label='transformation_plate')

    # Load pipette tips
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)
    tiprack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 5)

    # Load pipettes
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_300])

    # Define wells for 8 transformations (pEX01-pEX08)
    plasmid_wells = [plasmid_plate[well] for well in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']]
    transformation_wells = [transformation_plate[well] for well in ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']]
    soc_well = soc_reservoir['A1']

    # Step 1: Add 1 µL of plasmid DNA to pre-chilled competent cells (10 µL each)
    # Using Low Volume (LV) configuration as selected by APEX optimization
    for plasmid_well, transformation_well in zip(plasmid_wells, transformation_wells):
        p20.pick_up_tip()
        p20.aspirate(1, plasmid_well)
        p20.dispense(1, transformation_well)
        p20.drop_tip()

    # Step 2: Pre-incubation at 4°C for 30 minutes
    # Cells and DNA are held together on ice for binding
    tc.set_block_temperature(4, hold_time_minutes=30)

    # Step 3: Heat shock at 42°C for 30 seconds
    # Rapid temperature increase enables DNA uptake across the cell membrane
    tc.set_block_temperature(42, hold_time_seconds=30)

    # Step 4: Add 50 µL of SOC medium to each well
    # SOC provides nutrients for recovery and allows expression of antibiotic resistance genes
    for transformation_well in transformation_wells:
        p300.pick_up_tip()
        p300.aspirate(50, soc_well)
        p300.dispense(50, transformation_well)
        p300.drop_tip()

    # Step 5: Recovery at 37°C for 1 hour
    # Cells recover in SOC medium at optimal growth temperature (37°C)
    tc.set_block_temperature(37, hold_time_minutes=60)
