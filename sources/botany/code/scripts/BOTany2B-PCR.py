from opentrons import protocol_api

import csv
import json
import math

#-------(Modify) Change name and description to suit your needs (1)
metadata = {
    "apiLevel": "2.20",
    "protocolName": "BOTany2B-PCR",
    "description": """A small volume transfer program for PCR setup and off-deck thermocycler reactions.""",
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
                       display_name="BOTany2-PCR-Table CSV File",
                       description="Import the csv (.xslx) file for this protocol. Make sure to modify the values within first."
                       )
    #Starting tip rack location parameter, either 1 or 9
    parameters.add_str(
    variable_name="starting_tip_slot",
    display_name="Starting Tip Rack Location",
    description="The location of the starting tip rack, slot 1 or slot 9. Slot 1 always gets uesed before slot 9",
    choices=[
        {"display_name": "Slot 1", "value": "1"},
        {"display_name": "Slot 9", "value": "9"},
    ],
    default="1"
    )


    #Parameter for starting tip, letter part (ex. "A"1)
    parameters.add_str(
    variable_name="starting_tip_let",
    display_name="Starting Tip Letter",
    description="The letter of the tip location you want the robot to start with, when picking up tips",
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

    #Parameter for starting tip, number part (ex. A"1")
    parameters.add_str(
    variable_name="starting_tip_num",
    display_name="Starting Tip Number",
    description="The number of the tip location you want the robot to start with, when picking up tips",
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

    #Pipette location parameter, either left or right
    parameters.add_str(
    variable_name="pipette_loc",
    display_name="P20 Pipette Location",
    description="The location of the required P20 pipette, left or right",
    choices=[
        {"display_name": "Left", "value": "left"},
        {"display_name": "Right", "value": "right"},
    ],
    default="left"
    )

    #Parameter to choose type of pipette, will not be used in the code, only to allow user to attach other pipettes besides P20
    parameters.add_str(
        variable_name="pipette_ext_choice",
        display_name="Other Pipette Mounted",
        description="If you attached another pipette on the robot, won't be used in protocol",
        choices=[
            {"display_name": "P300", "value": "p300_single_gen2"},
            {"display_name": "P1000", "value": "p1000_single_gen2"},
            {"display_name": "8-channel P20", "value": "p20_multi_gen2"},
            {"display_name": "8-channel P300", "value": "p300_multi_gen2"},
            {"display_name": "None", "value": "none"},
        ],
        default="p300_single_gen2"
    )
    
    #Parameter to choose the location of the additional mounted pipette that will not be used in this protocol
    parameters.add_str(
    variable_name="pipette_ext_loc",
    display_name="Other Pipette Location",
    description="The location of the other pipette mounted, left or right",
    choices=[
        {"display_name": "Left", "value": "left"},
        {"display_name": "Right", "value": "right"},
    ],
    default="right"
    )

    #Allows user to prevent a long temperature module cooling period at the start of the protocol, when the robot cannot simultaneously pipette
    parameters.add_bool(
        variable_name="temp_mod_cooling",
        display_name="Temperature Module Cooling",
        description="True = cool, False = don't cool - liquid transfer doesn't start until cooling finishes",
        default=False
    )

    


#Protocol context - https://docs.opentrons.com/v2/tutorial.html
def run(protocol: protocol_api.ProtocolContext):

    #Parser for the csv runtime parameter. Note that this gets a list where each item is a row in the csv file
    #Each item in the child lists corresponds to a single cell within its row. Data is represented as string.
    csv_data_list = protocol.params.svt_csv.parse_as_csv()

    #---------(Modify) Load the needed Modules, Labware, Tip racks, Pipettes  (2)
    #Load the temperature module
    temp_mod = protocol.load_module(
        module_name="temperature module gen2", location="3"
    )

    #Whether to cool the temperature block in the beginning, according to the user from runtime parameters
    if protocol.params.temp_mod_cooling == True: temp_mod.set_temperature(celsius=14)


    #Loading tip rack, after the api name, put comma and then which slot it is in on the Opentron
    tiprack_slots = ['1', '9']
    # load tipracks into a dict keyed by slot for easy lookup
    tip_racks = [
        protocol.load_labware(load_name="opentrons_96_filtertiprack_20ul",location=slot)
            for slot in tiprack_slots]

    s_20_pip = protocol.load_instrument(instrument_name="p20_single_gen2",
                                        mount=protocol.params.pipette_loc,
                                        tip_racks=tip_racks)

    starting_tip_name = str(protocol.params.starting_tip_let) + str(protocol.params.starting_tip_num)
    start_slot = protocol.params.starting_tip_slot
    start_rack = tip_racks[tiprack_slots.index(start_slot)]
    # choose which rack to start in; add this param in your app/config, default to first slot
    s_20_pip.starting_tip = start_rack.wells_by_name()[starting_tip_name]

    if protocol.params.pipette_ext_choice != "none":
        #Load in the extraneous pipette, although it's not used.
        protocol.load_instrument(instrument_name=protocol.params.pipette_ext_choice, mount=protocol.params.pipette_ext_loc)


    #Load the labware with its api name, look it up in labware library - https://labware.opentrons.com/
    #Add labware to dictionary
    labware_dict = dict([('tube_rack1', protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)), 
                         ('tube_rack2', protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)),
                         ('tube_rack3', protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 6)),
                         ('tube_rack4', protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)),
                         ('pcr_strip', protocol.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul", 7)),
                         ('temp_tubes', temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap"))])

    #----------End of modifications (2)


    #Code to read from csv to "define intial volumes"
    #Discard the first row of csv, since that's all the titles of the columns.
    csv_iv_data = csv_data_list[2:]

    for csv_row in csv_iv_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[1] != "":
            #Define variables from CSV columns
            labware = csv_row[1] #Start from 1, because index 0 column is the instructions
            liquid_well = csv_row[2]
            liquid_volume = float(csv_row[3])
            liquid_name = csv_row[4]
            liquid_description = csv_row[5]
            liquid_color = csv_row[6]

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


    first_transfer = True

    for csv_row in csv_iv_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[8] != "":
            # Define variables from CSV columns
            source_labware = csv_row[8]
            source_well = csv_row[9]
            destination_labware = csv_row[10]
            destination_well = csv_row[11]
            transfer_volume = float(csv_row[12])
            pick_up_tip = str(csv_row[13])

            curr_source_labware = getLabwareObject(labware_dict, source_labware)
            curr_destination_labware = getLabwareObject(labware_dict, destination_labware)

            if pick_up_tip == 'TRUE':

                if first_transfer == True:
                    #Pick up the first tip
                    s_20_pip.pick_up_tip()
                    first_transfer = False
                else:
                    #Discard the previous tip
                    s_20_pip.drop_tip()
                    #Pick up the next tip, will always pick up the next available tip
                    s_20_pip.pick_up_tip()

                
                #Now, start the volume transfer
                
                #Aspirate [take in] liquid, with this format (amount in microliters, well location)
                s_20_pip.aspirate(transfer_volume, curr_source_labware[source_well])
                #Dispense liquid, with this format (amount in microliters, well location)
                s_20_pip.dispense(transfer_volume, curr_destination_labware[destination_well])

            elif pick_up_tip == 'FALSE':
                if first_transfer == True:
                    #Pick up the first tip
                    s_20_pip.pick_up_tip()
                    first_transfer = False

                # Aspirate [take in] liquid, with this format (amount in microliters, well location)
                s_20_pip.aspirate(transfer_volume, curr_source_labware[source_well])
                # Dispense liquid, with this format (amount in microliters, well location)
                s_20_pip.dispense(transfer_volume, curr_destination_labware[destination_well])

            else:

                protocol.comment('Please specify whether to use new or same tip')

    #Discard the previous tip
    s_20_pip.drop_tip()

    #Deactivate the temperature module
    temp_mod.deactivate() 


        
