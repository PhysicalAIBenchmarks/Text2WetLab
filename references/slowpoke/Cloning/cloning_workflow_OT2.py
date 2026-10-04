
# Golden Gate Cloning, Transformation, and Plating protocol
# Written by Fankang Meng, and Koray Malci, Imperial College London
from opentrons import protocol_api, types
import time
import math

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Cloning Protocol - Golden Gate assembly, Transformation and Plating',
    'description': 'GG & Transformation & plating using an OT-2 for genetic toolkits.'}

num_rxns = len(combinations_to_make)

def run(protocol: protocol_api.ProtocolContext):
    # Load in 1 10ul tiprack and 2 300ul tipracks
    tr_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    tr_20 = protocol.load_labware('opentrons_96_tiprack_20ul', '4')

    # Load in pipettes
    p10_single = protocol.load_instrument('p10_single', 'right', tip_racks=[tr_20])
    p300_single = protocol.load_instrument('p300_single', 'left', tip_racks=[tr_300])

    # Load in Bio-Rad 96 Well Plate on Thermocycler Module for GG Assembly, transformation, and outgrowth.
    tc_mod = protocol.load_module('Thermocycler Module')
    reaction_plate = tc_mod.load_labware('biorad_96_wellplate_200ul_pcr')
    tc_mod.open_lid()
    tc_mod.set_block_temperature(4)

    # Load in Water & Enzymer+ Buffer, wash water, dilution water, and wash trough (USA Scientific 12 Well Reservoir 22ml)
    temp_mod = protocol.load_module('Temperature Module', '3')
    trough = temp_mod.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap', '3')
    typeII_enzyme_buffer_mix = trough.wells()[0]  # Well A1
    water = trough.wells()[1]  # Well B1
    dilution_water = trough.wells()[2]  # Well C1
    competent_cell = trough.wells()[3]  # Well D1
    liquid_waste = trough.wells()[4]  # Well A2

    # Load in Input DNA Plate
    dna_plate_dict = {}
    plate_name = list(dna_plate_map_dict.keys())
    dna_plate_dict[plate_name[0]] = protocol.load_labware('biorad_96_wellplate_200ul_pcr', '1', 'Input DNA Plate')
    dna_plate_dict[plate_name[1]] = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '2', 'Input DNA Plate2')

    # Load in Agar plate
    agar_plate = protocol.load_labware('corning_6_wellplate_16.8ml_flat', '5', 'Agar Plate')


    # This function checks the existance of DNA parts and returns for well location of the parts
    def find_dna(name, dna_plate_map_dict, dna_plate_dict):
        """Return a well containing the named DNA."""
        well_num=None
        for plate_name, plate_map in dna_plate_map_dict.items():
            for i, row in enumerate(plate_map):
                for j, dna_name in enumerate(row):
                    if dna_name == name:
                        if plate_name == 'fixed_input_dna_map':
                            well_num = 8 * j + i
                        elif plate_name == 'customised_input_dna_map':
                            well_num = 4 * j + i
                         # Check if well_num is assigned a value
        if well_num is not None:
            return dna_plate_dict[plate_name].wells()[well_num]

        # Handle the case where the name is not found
        print(f"DNA with name '{name}' not found.")
        return None  # or raise an exception, depending on your requirements   
                        #return dna_plate_dict[plate_name].wells()[well_num]
        raise ValueError("Could not find dna piece named \"{0}\"".format(name))

    # This function checks if the DNA parts exist in the DNA plates and returns for well locaion of output DNA combinations
    def find_combination(name, combinations_to_make):
        """Return a well containing the named combination."""
        for i, combination in enumerate(combinations_to_make):
            if combination["name"] == name:
                return reaction_plate.wells()[i]
        raise ValueError("Could not find combination \"{0}\".".format(name))

    combinations_by_part = {}
    for i in combinations_to_make:
        name = i["name"]
        for j in i["parts"]:
            if j in combinations_by_part.keys():
                combinations_by_part[j].append(name)
            else:
                combinations_by_part[j] = [name]

    # This section will take the GG buffer and water into the designation wells
    p10_single.pick_up_tip()
    for i in range(num_rxns):
        N = len(combinations_to_make[i]['parts'])
        p10_single.consolidate(
            [2, 8 - N],
            [trough.wells_by_name()[well_name] for well_name in ['A1', 'B1']],
            reaction_plate.wells()[i].bottom(z=0.5), new_tip='never')
        # p10_single.blow_out()
    p10_single.drop_tip()

    # This section of the code combines and mix the DNA parts according to the combination list
    for part, combinations in combinations_by_part.items():
        part_well = find_dna(part, dna_plate_map_dict, dna_plate_dict)
        combination_wells = [find_combination(x, combinations_to_make) for x in combinations]
        p10_single.pick_up_tip()
        while combination_wells:
            if len(combination_wells) > 10:
                current_wells = combination_wells[0:10]
                combination_wells = combination_wells[10:]
            else:
                current_wells = combination_wells
                combination_wells = []
            p10_single.aspirate(1 * len(current_wells), part_well)
            for i in current_wells:
                p10_single.dispense(1, i.bottom(z=0.5))
            if combination_wells:
                # One washing steps are added to allow recycling of the tips
                p10_single.mix(2, 10, water.bottom(z=0.5))
                p10_single.blow_out()
        p10_single.drop_tip()

    # Seal the Reaction Plate with adhesive film and conduct the GG program
    protocol.pause( 'Please seal the PCR plates and resume run to conduct GG program.')

    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    profile1 = [
            {'temperature': 37, 'hold_time_seconds': 120},
            {'temperature': 16, 'hold_time_seconds': 300}]
    tc_mod.execute_profile(steps=profile1, repetitions=25, block_max_volume=20)
    profile2 = [
            {'temperature': 60, 'hold_time_seconds': 300}]
    tc_mod.execute_profile(steps=profile2, repetitions=1, block_max_volume=20)
    tc_mod.set_block_temperature(4)
    tc_mod.open_lid()
    #temp_mod.set_temperature(4) #Optional
    protocol.pause('Place remove the seal film of the PCR plates and resume run to conduct heat shock program.')

    # Add competent cells
    for i in range(0, num_rxns):
            p300_single.pick_up_tip()
            p300_single.transfer(50, competent_cell.bottom(z=0.5), reaction_plate.wells()[i].bottom(z=0.5), new_tip='never')
            p300_single.mix(1, 25, reaction_plate.wells()[i].bottom(z=0.5))
            p300_single.blow_out()
            p300_single.drop_tip()
    temp_mod.deactivate()
    protocol.pause('Place seal the PCR paltes again and resume run to conduct the heat-shock program.')

     # Incubate at 4℃, then heat shock.
    tc_mod.close_lid()
    profile1 = [
            {'temperature': 4, 'hold_time_seconds': 600},
            {'temperature': 42, 'hold_time_seconds': 90},
            {'temperature': 4, 'hold_time_seconds': 120},
            {'temperature': 37, 'hold_time_seconds': 3600}]
    tc_mod.execute_profile(steps=profile1, repetitions=1, block_max_volume=40)
    tc_mod.set_block_temperature(37)
    tc_mod.open_lid()
    protocol.pause('Please remove the seal and resume for plating')

    # Plating
    a = len(agar_plate.wells())
    for i in range(0, num_rxns):
        if i <a:
            p300_single.pick_up_tip()
            p300_single.mix(1, 25, reaction_plate.wells()[i].bottom(z=0.5))
            p300_single.distribute(4.5, reaction_plate.wells()[i].bottom(z=0.5),
                               [agar_plate.wells()[i].bottom(z=6).move(position) for position in
                                [types.Point(x=0, y=0),
                                 types.Point(x=0, y=4), types.Point(x=4, y=0), types.Point(x=0, y=-4), types.Point(x=-4, y=0),
                                 types.Point(x=0, y=8), types.Point(x=5.5, y=5.5), types.Point(x=8, y=0),
                                 types.Point(x=5.5, y=-5.5), types.Point(x=0, y=-8), types.Point(x=-5.5, y=-5.5),
                                 types.Point(x=-8, y=0), types.Point(x=-5.5, y=5.5)]],
                               disposal_volume=1.5, new_tip='never')
            p300_single.blow_out()
            p300_single.drop_tip()
        if i >= a:
            if i % a == 0:
               protocol.pause('Please change a new agar plates')    
            p300_single.pick_up_tip()
            p300_single.mix(1, 25, reaction_plate.wells()[i].bottom(z=0.5))
            p300_single.distribute(4.5, reaction_plate.wells()[i].bottom(z=0.5),
                                   [agar_plate.wells()[i%a].bottom(z=6).move(position) for position in
                                    [types.Point(x=0, y=0),
                                     types.Point(x=0, y=4), types.Point(x=4, y=0), types.Point(x=0, y=-4),
                                     types.Point(x=-4, y=0),
                                     types.Point(x=0, y=8), types.Point(x=5.5, y=5.5), types.Point(x=8, y=0),
                                     types.Point(x=5.5, y=-5.5), types.Point(x=0, y=-8), types.Point(x=-5.5, y=-5.5),
                                     types.Point(x=-8, y=0), types.Point(x=-5.5, y=5.5)]],
                                   disposal_volume=1.5, new_tip='never')
            p300_single.blow_out()
            p300_single.drop_tip()
    tc_mod.deactivate()
