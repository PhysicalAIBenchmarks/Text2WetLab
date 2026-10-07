from opentrons import protocol_api

import csv
import json
import math

#-------(Modify) Change name and description to suit your needs (1)
metadata = {
    "apiLevel": "2.20",
    "protocolName": "BOTany6-Universal",
    "description": """A general volume transfer protocol.""",
    "author": "Voiniciuc Lab"
    }
#-------End of modifications (1)

#Function that gets labware object to use given the string name of variable
def getLabwareObject(labware_dict, labware_name):
    for key, value in labware_dict.items():
        if str(key) == str(labware_name):
            return value
    return

#Runtime parameter definitions
def add_parameters(parameters):
    parameters.add_csv_file(variable_name="svt_csv",
                       display_name="BOTany6-Universal-Table CSV",
                       description="Import the csv file for the volume transfer/labware definitions."
                       )
    
    #Parameter for left starting tip, letter part (ex. "A"1)
    parameters.add_str(
    variable_name="left_starting_tip_let",
    display_name="Left Pip Start Tip Letter",
    description="The letter of the left pipette tip location you want the robot to start with, when picking up tips",
    default="A",
    choices=[
        {"display_name": "A", "value": "A"},
        {"display_name": "B", "value": "B"},
        {"display_name": "C", "value": "C"},
        {"display_name": "D", "value": "D"},
        {"display_name": "E", "value": "E"},
        {"display_name": "F", "value": "F"},
        {"display_name": "G", "value": "G"},
        {"display_name": "H", "value": "H"},
    ]
    )

    #Parameter for left starting tip, number part (ex. A"1")
    parameters.add_str(
    variable_name="left_starting_tip_num",
    display_name="Left Pip Start Tip Number",
    description="The number of the left pipette tip location you want the robot to start with, when picking up tips",
    default="1",
    choices=[
        {"display_name": "1", "value": "1"},
        {"display_name": "2", "value": "2"},
        {"display_name": "3", "value": "3"},
        {"display_name": "4", "value": "4"},
        {"display_name": "5", "value": "5"},
        {"display_name": "6", "value": "6"},
        {"display_name": "7", "value": "7"},
        {"display_name": "8", "value": "8"},
        {"display_name": "9", "value": "9"},
        {"display_name": "10", "value": "10"},
        {"display_name": "11", "value": "11"},
        {"display_name": "12", "value": "12"},
    ]
    )

    #Parameter for right starting tip, letter part (ex. "A"1)
    parameters.add_str(
    variable_name="right_starting_tip_let",
    display_name="Right Pip Start Tip Letter",
    description="The letter of the right pipette tip location you want the robot to start with, when picking up tips",
    default="A",
    choices=[
        {"display_name": "A", "value": "A"},
        {"display_name": "B", "value": "B"},
        {"display_name": "C", "value": "C"},
        {"display_name": "D", "value": "D"},
        {"display_name": "E", "value": "E"},
        {"display_name": "F", "value": "F"},
        {"display_name": "G", "value": "G"},
        {"display_name": "H", "value": "H"},
    ]
    )

    #Parameter for right starting tip, number part (ex. A"1")
    parameters.add_str(
    variable_name="right_starting_tip_num",
    display_name="Right Pip Start Tip Number",
    description="The number of the right pipette tip location you want the robot to start with, when picking up tips",
    default="1",
    choices=[
        {"display_name": "1", "value": "1"},
        {"display_name": "2", "value": "2"},
        {"display_name": "3", "value": "3"},
        {"display_name": "4", "value": "4"},
        {"display_name": "5", "value": "5"},
        {"display_name": "6", "value": "6"},
        {"display_name": "7", "value": "7"},
        {"display_name": "8", "value": "8"},
        {"display_name": "9", "value": "9"},
        {"display_name": "10", "value": "10"},
        {"display_name": "11", "value": "11"},
        {"display_name": "12", "value": "12"},
    ]
    )

    #Parameter to choose type of pipette on the left
    parameters.add_str(
        variable_name="pipette_left_choice",
        display_name="Left Pipette Choice",
        description="The type of pipette to load and use on the left",
        choices=[
            {"display_name": "P20", "value": "p20_single_gen2"},
            {"display_name": "P300", "value": "p300_single_gen2"},
            {"display_name": "P1000", "value": "p1000_single_gen2"},
            {"display_name": "8-Channel P20", "value": "20_unused"},
            {"display_name": "8-Channel P300", "value": "300_unused"},
            {"display_name": "None", "value": "none"},
        ],
        default="p20_single_gen2"
    )

    #Parameter to choose type of pipette on the right
    parameters.add_str(
        variable_name="pipette_right_choice",
        display_name="Right Pipette Choice",
        description="The type of pipette to load and use on the right",
        choices=[
            {"display_name": "P20", "value": "p20_single_gen2"},
            {"display_name": "P300", "value": "p300_single_gen2"},
            {"display_name": "P1000", "value": "p1000_single_gen2"},
            {"display_name": "8-Channel P20", "value": "20_unused"},
            {"display_name": "8-Channel P300", "value": "300_unused"},
            {"display_name": "None", "value": "none"},
        ],
        default="p300_single_gen2"
    )

#Protocol context - https://docs.opentrons.com/v2/tutorial.html
def run(protocol: protocol_api.ProtocolContext):

    #Parser for the csv runtime parameter. Note that this gets a list where each item is a row in the csv file
    #Each item in the child lists corresponds to a single cell within its row. Data is represented as string.
    csv_data_list = protocol.params.svt_csv.parse_as_csv()

    #Discard the first row of csv, since that's all the titles of the columns.
    csv_trunc_data = csv_data_list[2:]

    p20_rack_list = []
    p300_rack_list = []
    p1000_rack_list = []

    #Create dictionary to store the loaded tip rack definitions
    tip_rack_dict = dict()
    #Create a dictionary to store the loaded labware definitions
    labware_dict = dict()

    #Table for tip racks
    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[1] != "":
            rack_name = csv_row[1] #Start from 1, because index 0 column is the instructions
            rack_api = csv_row[2]
            rack_loc = csv_row[3]

            #Append the current tip rack to the dictionary of tip racks
            tip_rack_dict[str(rack_name)] = protocol.load_labware(load_name=str(rack_api), location=int(rack_loc))


            #Depending on the tip size, append the tip rack objects to their respective lists.
            if str(rack_api) == "opentrons_96_filtertiprack_20ul" or str(rack_api) == "opentrons_96_tiprack_20ul":
                p20_rack_list.append(getLabwareObject(tip_rack_dict, str(rack_name)))
            elif str(rack_api) == "opentrons_96_tiprack_300ul":
                p300_rack_list.append(getLabwareObject(tip_rack_dict, str(rack_name)))
            elif str(rack_api) == "opentrons_96_filtertiprack_1000ul" or str(rack_api) == "opentrons_96_tiprack_1000ul":
                p1000_rack_list.append(getLabwareObject(tip_rack_dict, str(rack_name)))

    #Get the names of the left and right pipettes as strings, ex. p20, p300
    if (protocol.params.pipette_left_choice != "none") and (protocol.params.pipette_left_choice != "20_unused" and protocol.params.pipette_left_choice != "300_unused"):
        left_pip_name = protocol.params.pipette_left_choice.split("_")[0]
    if (protocol.params.pipette_right_choice != "none") and (protocol.params.pipette_right_choice != "20_unused" and protocol.params.pipette_right_choice != "300_unused"):
        right_pip_name = protocol.params.pipette_right_choice.split("_")[0]
    

    if ((protocol.params.pipette_left_choice != "none")) and (protocol.params.pipette_left_choice != "20_unused" and protocol.params.pipette_left_choice != "300_unused"):
        if left_pip_name == "p20":
            left_rack_list = p20_rack_list
        elif left_pip_name == "p300":
            left_rack_list = p300_rack_list
        elif left_pip_name == "p1000":
            left_rack_list = p1000_rack_list

    if (protocol.params.pipette_right_choice != "none") and (protocol.params.pipette_right_choice != "20_unused" and protocol.params.pipette_right_choice != "300_unused"):
        if right_pip_name == "p20":
            right_rack_list = p20_rack_list
        elif right_pip_name == "p300":
            right_rack_list = p300_rack_list
        elif right_pip_name == "p1000":
            right_rack_list = p1000_rack_list

    #Table for base labware
    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[5] != "":
            labware_name = csv_row[5] #Start from 1, because index 0 column is the instructions
            labware_api = csv_row[6]
            labware_loc = csv_row[7]

            #Append the current labware to the dictionary of labware
            labware_dict[str(labware_name)] = protocol.load_labware(str(labware_api), int(labware_loc))

    #Table for modules
    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[9] != "":
            module_name = csv_row[9] #Start from 1, because index 0 column is the instructions
            module_api = csv_row[10]
            module_location = csv_row[11]

            if module_api == "thermocyclerModuleV2": #Because thermocycler is the only module that can't have its location defined.
                #Also append the current module to the dictionary of labware, to simplify
                labware_dict[str(module_name)] = protocol.load_module(str(module_api))
                getLabwareObject(labware_dict, module_name).open_lid()
            else:
                #Also append the current module to the dictionary of labware, to simplify
                labware_dict[str(module_name)] = protocol.load_module(str(module_api), int(module_location))

    #Table for labware loaded on top of other (base) labware, instead of directly on the robot's deck
    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[13] != "":
            base_lab_name = csv_row[13] #Start from 1, because index 0 column is the instructions
            top_lab_name = csv_row[14]
            top_lab_api = csv_row[15]

            labware_dict[str(top_lab_name)] = getLabwareObject(labware_dict, base_lab_name).load_labware(str(top_lab_api))

    #Make a dictionary to store the loaded pipette objects
    pipette_dict = dict()

    if (protocol.params.pipette_left_choice != "none") and (protocol.params.pipette_left_choice != "20_unused" and protocol.params.pipette_left_choice != "300_unused"):
        left_pip_key = f'{left_pip_name}_pip'
    if (protocol.params.pipette_right_choice != "none") and (protocol.params.pipette_right_choice != "20_unused" and protocol.params.pipette_right_choice != "300_unused"):
        right_pip_key = f'{right_pip_name}_pip'

    #If the user has chosen values for the left/right pipettes in the runtime parameters, load the respective pipettes in
    if (protocol.params.pipette_left_choice != "none"):
        #If the user chose to load in a multichannel
        if protocol.params.pipette_left_choice == "20_unused":
            pipette_dict["multichannel"] = protocol.load_instrument(instrument_name="p20_multi_gen2", mount="left")
        elif protocol.params.pipette_left_choice == "300_unused":
            pipette_dict["multichannel"] = protocol.load_instrument(instrument_name="p300_multi_gen2", mount="left")
        elif left_pip_name == "p20":
            pipette_dict[left_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_left_choice), mount="left", tip_racks=p20_rack_list)
            left_pip_obj = getLabwareObject(pipette_dict, left_pip_key)
        elif left_pip_name == "p300":
            pipette_dict[left_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_left_choice), mount="left", tip_racks=p300_rack_list)
            left_pip_obj = getLabwareObject(pipette_dict, left_pip_key)
        elif left_pip_name == "p1000":
            pipette_dict[left_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_left_choice), mount="left", tip_racks=p1000_rack_list)
            left_pip_obj = getLabwareObject(pipette_dict, left_pip_key)
    if (protocol.params.pipette_right_choice != "none"):
        #If the user chose to load in a multichannel
        if protocol.params.pipette_right_choice == "20_unused":
            pipette_dict["multichannel"] = protocol.load_instrument(instrument_name="p20_multi_gen2", mount="right")
        elif protocol.params.pipette_right_choice == "300_unused":
            pipette_dict["multichannel"] = protocol.load_instrument(instrument_name="p300_multi_gen2", mount="right")
        elif right_pip_name == "p20":
            pipette_dict[right_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_right_choice), mount="right", tip_racks=p20_rack_list)
            right_pip_obj = getLabwareObject(pipette_dict, right_pip_key)
        elif right_pip_name == "p300":
            pipette_dict[right_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_right_choice), mount="right", tip_racks=p300_rack_list)
            right_pip_obj = getLabwareObject(pipette_dict, right_pip_key)
        elif right_pip_name == "p1000":
            pipette_dict[right_pip_key] = protocol.load_instrument(instrument_name=str(protocol.params.pipette_right_choice), mount="right", tip_racks=p1000_rack_list)
            right_pip_obj = getLabwareObject(pipette_dict, right_pip_key)

    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[17] != "":
            #Define variables from CSV columns
            labware = csv_row[17] #Start from 1, because index 0 column is the instructions
            liquid_well = csv_row[18]
            liquid_volume = float(csv_row[19])
            liquid_name = csv_row[20]
            liquid_description = csv_row[21]
            liquid_color = csv_row[22]

            #Now, configure the liquids in the protocol *Note for future can also add description/color
            current_liquid = protocol.define_liquid(
                name=liquid_name,
                description=liquid_description,
                display_color=liquid_color
            )

            #Get object of current labware given the variable name
            curr_labware = getLabwareObject(labware_dict, labware)
            #Add the liquids to the current labware
            curr_labware[liquid_well].load_liquid(liquid=current_liquid, volume=liquid_volume)

    #Get the value, ex "A3" of the starting tip for the left/right pipette, and also tell the respective pipette to use that as the starting tip
    if (protocol.params.pipette_left_choice != "none") and (protocol.params.pipette_left_choice != "20_unused" and protocol.params.pipette_left_choice != "300_unused"):
        if len(left_rack_list) > 0:
            left_starting_tip = str(protocol.params.left_starting_tip_let) + str(protocol.params.left_starting_tip_num)
            curr_tip_rack = left_rack_list[0]
            pipette_dict[str(left_pip_key)].starting_tip = curr_tip_rack.well(left_starting_tip)
        else:
            protocol.pause(f'Please add an appropriate tip rack for the left pipette in the excel file')
    if (protocol.params.pipette_right_choice != "none") and (protocol.params.pipette_right_choice != "20_unused" and protocol.params.pipette_right_choice != "300_unused"):
        if len(right_rack_list) > 0:
            right_starting_tip = str(protocol.params.right_starting_tip_let) + str(protocol.params.right_starting_tip_num)
            curr_tip_rack = right_rack_list[0]
            pipette_dict[str(right_pip_key)].starting_tip = curr_tip_rack.well(right_starting_tip)
        else:
            protocol.pause(f'Please add an appropriate tip rack for the left pipette in the excel file')

    first_transfer_left = True
    first_transfer_right = True

    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[24] != "":
            # Define variables from CSV columns
            source_labware = csv_row[24]
            source_well = csv_row[25]
            destination_labware = csv_row[26]
            destination_well = csv_row[27]
            transfer_volume = float(csv_row[28])
            pick_up_tip = str(csv_row[29])
            pipette_choice = str(csv_row[30])

            curr_source_labware = getLabwareObject(labware_dict, source_labware)
            curr_destination_labware = getLabwareObject(labware_dict, destination_labware)

            valid_pipette = False

            #Make sure the chosen pipette for this step from the CSV is valid, aka not a multichannel or none
            if pipette_choice == "Left" and (protocol.params.pipette_left_choice == "none" or protocol.params.pipette_left_choice == "20_unused" or protocol.params.pipette_left_choice == "300_unused"):
                protocol.pause("Please review the liquid transfer steps and choose a valid pipette")
            elif pipette_choice == "Left":
                curr_pip = left_pip_obj
                valid_pipette = True
            if pipette_choice == "Right" and (protocol.params.pipette_right_choice == "none" or protocol.params.pipette_right_choice == "20_unused" or protocol.params.pipette_right_choice == "300_unused"):
                protocol.pause("Please review the liquid transfer steps and choose a valid pipette")
            elif pipette_choice == "Right":
                curr_pip = right_pip_obj
                valid_pipette = True

            if valid_pipette == True:
                if pick_up_tip == 'TRUE':
                    if pipette_choice == "Left" and first_transfer_left == True:
                        #Pick up the first tip
                        curr_pip.pick_up_tip()
                        first_transfer_left = False
                    elif pipette_choice == "Right" and first_transfer_right == True:
                        #Pick up the first tip
                        curr_pip.pick_up_tip()
                        first_transfer_right = False
                    else:
                        #Discard the previous tip
                        curr_pip.drop_tip()
                        #Pick up the next tip, will always pick up the next available tip
                        curr_pip.pick_up_tip()

                    #Aspirate [take in] liquid, with this format (amount in microliters, well location)
                    curr_pip.aspirate(transfer_volume, curr_source_labware[source_well])
                    #Dispense liquid, with this format (amount in microliters, well location)
                    curr_pip.dispense(transfer_volume, curr_destination_labware[destination_well])

                elif pick_up_tip == 'FALSE':
                    if pipette_choice == "Left" and first_transfer_left == True:
                        #Pick up the first tip
                        curr_pip.pick_up_tip()
                        first_transfer_left = False
                    elif pipette_choice == "Right" and first_transfer_right == True:
                        #Pick up the first tip
                        curr_pip.pick_up_tip()
                        first_transfer_right = False

                    #Aspirate [take in] liquid, with this format (amount in microliters, well location)
                    curr_pip.aspirate(transfer_volume, curr_source_labware[source_well])
                    #Dispense liquid, with this format (amount in microliters, well location)
                    curr_pip.dispense(transfer_volume, curr_destination_labware[destination_well])

                else:

                    protocol.comment('Please specify whether to use new or same tip')

    if valid_pipette == True:
        #Discard the previous tip
        curr_pip.drop_tip()
