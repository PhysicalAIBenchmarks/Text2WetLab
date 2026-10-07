
# Colony PCR Protocol V3.0
# Written by Fankang Meng and Koray Malci Imperial College London
#2024

from opentrons import protocol_api, types
import math

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Colony_PCR_Protocol_V3.0',
    'description': 'Colony PCR Protocol'}

#####################################
#PCR cycles and extension time；change this!!!
pcr_cycles = [
    {'temperature': 98, 'hold_time_seconds': 15},
    {'temperature': 55 , 'hold_time_seconds': 30},
    {'temperature': 72, 'hold_time_seconds': 200}]#change this!!!
pcr_cycles_number = 30 #change this!!!
reaction_volume = 10 #change this!!!
#####################################


#number of ractions
num_rxns = len(pcr_recipe_to_make)

def run(protocol: protocol_api.ProtocolContext):
    # loading pipette and tips
    tr_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    tr_20 = protocol.load_labware('opentrons_96_tiprack_20ul', '3')
    p10_single = protocol.load_instrument('p10_single', 'right', tip_racks=[tr_20])
    p300_single = protocol.load_instrument('p300_single', 'left', tip_racks=[tr_300])

    # loading thermocycler
    tc_mod = protocol.load_module('Thermocycler Module')
    reaction_plate = tc_mod.load_labware('biorad_96_wellplate_200ul_pcr')
    addition_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', '4')
    tc_mod.open_lid()

    # loading plate with picked colonies in 80ul medium
    colony_template_deck= protocol.load_labware('biorad_96_wellplate_200ul_pcr', '2', 'colony_template_plate')

    # loading rack with PCR recipe tubes
    pcr_deck = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '9', ' pcr_deck')
    pcr_mix_deck = protocol.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '5', ' pcr_deck')

#Calculate how many PCR reaction systems there are in total
    combinations = []
    name_1 = pcr_recipe_to_make[0]["name"]
    part_1 = pcr_recipe_to_make[0]["parts"][0:-1]
    combinations.append({"name": [name_1], "parts": part_1})
    for i in pcr_recipe_to_make[1:]:
        name = i["name"]
        part = i["parts"][0:-1]
        j = 0
        a = len(combinations)
        while j < a:
            # If the parts of j are different from i["parts"], set a new dictionary in combinations
            name_j = combinations[j]["name"]
            parts_j = combinations[j]["parts"]
            if part == parts_j:
                name_j.append(name)
                break
                # If the parts of j are the same as i["parts"], insert the name corresponding to i["parts"] into the 
                #the dictionary corresponding to this part.
            elif j == a - 1:
                combinations.append({"name": [name], "parts": part})
            j = j + 1

    # This function checks the existance of pcr raw materials and returns for well location of the raw materials
    def find_rawpcr(name, pcr_plate_map_dict, pcr_deck):
        """Return a well containing the named DNA."""
        for plate_name, plate_map in pcr_plate_map_dict.items():
            for i, row in enumerate(plate_map):
                for j, dna_name in enumerate(row):
                    if dna_name == name:
                        well_num = 4 * j + i
                        return pcr_deck.wells()[well_num]
        raise ValueError("Could not find dna piece named \"{0}\"".format(name))

    # This function checks if the DNA parts exist in the DNA plates and returns for well locaion of output DNA combinations
    def find_combination(name, combinations_to_make):
        """Return a well containing the named combination."""
        for i, combination in enumerate(combinations_to_make):
            if combination["name"] == name:
                if i < 96:
                    return reaction_plate.wells()[i]
                else:
                    return addition_plate.wells()[i-96]
        raise ValueError("Could not find combination \"{0}\".".format(name))

    #According to the type of PCR reaction, add different PCR raw materials and distribute them into the corresponding locations.
    for i, combination in enumerate(combinations):
        name_i = combination["name"]
        part_i = combination["parts"]
        pcr_sample_number = len(name_i) + 2
        pcr_plate_map_dict_list = pcr_deck_colony_template_maps_dict["pcr_deck_map"]
        pcr_plate_map_dict_number = sum([len(count) for count in pcr_plate_map_dict_list])

        for j, part in enumerate(part_i):
            if j == 0:
                a = reaction_volume/2-3
            elif j == 1:
                a = reaction_volume/2
            elif j == 2 or 3:
                a = 1
            rawpcr_well = find_rawpcr(part, pcr_deck_colony_template_maps_dict, pcr_deck)
            p300_single.pick_up_tip()
            p300_single.transfer(pcr_sample_number * a,
                                 rawpcr_well.bottom(z=2),
                                 pcr_mix_deck.wells()[i].bottom(z=3),
                                 blow_out=True, blowout_location='destination well',
                                 new_tip='never')
            p300_single.drop_tip()

        p300_single.pick_up_tip()
        p300_single.mix(2, 2 * (pcr_sample_number + 4), pcr_mix_deck.wells()[i].bottom(z=1))
        pcr_combination_wells = [find_combination(x, pcr_recipe_to_make) for x in name_i]
        p300_single.distribute(reaction_volume-1,
                               pcr_mix_deck.wells()[i].bottom(z=1),
                               pcr_combination_wells,
                               disposal_volume=5, new_tip='never')
        p300_single.drop_tip()

    # This function checks the existance of pcr raw materials and returns for well location of the raw materials
    def find_template(name, pcr_deck_colony_template_maps_dict, colony_template_deck):
        """Return a well containing the named DNA."""
        for plate_name, plate_map in pcr_deck_colony_template_maps_dict.items():
            for i, row in enumerate(plate_map):
                for j, colony_name in enumerate(row):
                    if colony_name == name:
                        well_num = 8 * j + i
                        return colony_template_deck.wells()[well_num]
        raise ValueError("Could not find colony template named \"{0}\"".format(name))

    combinations_by_colony_template = {}
    for i in pcr_recipe_to_make:
        name = i["name"]
        template = i["parts"][-1]
        if template in combinations_by_colony_template.keys():
            combinations_by_colony_template[template].append(name)
        else:
            combinations_by_colony_template[template] = [name]

    for part, combination_template in combinations_by_colony_template.items():
        template_well = find_template(part, pcr_deck_colony_template_maps_dict, colony_template_deck)
        colony_combination_wells = [find_combination(x, pcr_recipe_to_make) for x in combination_template]
        p10_single.pick_up_tip()
        p10_single.distribute(1,
                              template_well.bottom(z=1),
                              colony_combination_wells,
                              disposal_volume=1.5, new_tip='never')
        p10_single.drop_tip()

    # seal the pcr plate with adhesive film and conduct the GG program
    protocol.pause( 'Please seal the PCR plates and resume run to conduct PCR program.')

    # PCR steps
    tc_mod.close_lid()
    tc_mod.set_lid_temperature(105)
    # denaturation
    pre_denaturation_step = [{'temperature': 98, 'hold_time_seconds': 300}]
    tc_mod.execute_profile(steps=pre_denaturation_step, repetitions=1, block_max_volume=reaction_volume)
    # amplification cycles
    j = 0
    while j < pcr_cycles_number:
        tc_mod.execute_profile(steps=pcr_cycles, repetitions=1, block_max_volume=reaction_volume)
        j = j + 1
    # further  extension step
    extension_step = [{'temperature': 72, 'hold_time_seconds': 300}]
    tc_mod.execute_profile(steps=extension_step, repetitions=1, block_max_volume=reaction_volume)
    tc_mod.set_block_temperature(25)


    tc_mod.open_lid()
    tc_mod.deactivate()
