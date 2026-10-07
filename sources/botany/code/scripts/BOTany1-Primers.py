from opentrons import protocol_api

import csv
import json
import math

#-------(Modify) Change name and description to suit your needs (1)
metadata = {
    "apiLevel": "2.20",
    "protocolName": "BOTany1-Primers",
    "description": """A small volume transfer program for PCR, has all current options. To use, find the areas where 
    it says (Modify) in the code and modify.""",
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
                       display_name="BOTany1-Primer-Table CSV File",
                       description="Import the csv (.xslx) file for this protocol. Make sure to modify the values within first."
                       )
    
    #Parameter for number of samples, 1-24
    parameters.add_int(
        variable_name="num_samples",
        display_name="Number of Samples",
        description="Choose how many samples to run",
        minimum=1,
        maximum=24,
        default=24
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
    display_name="P300 Pipette Location",
    description="The location of the required P300 pipette, left or right",
    choices=[
        {"display_name": "Left", "value": "left"},
        {"display_name": "Right", "value": "right"},
    ],
    default="right"
    )

    #Parameter to choose type of pipette, will not be used in the code, only to allow user to attach other pipettes besides the required P300
    parameters.add_str(
        variable_name="pipette_ext_choice",
        display_name="Other Pipette Mounted",
        description="If you attached another pipette on the robot, won't be used in protocol",
        choices=[
            {"display_name": "P20", "value": "p20_single_gen2"},
            {"display_name": "P1000", "value": "p1000_single_gen2"},
            {"display_name": "8-channel P20", "value": "p20_multi_gen2"},
            {"display_name": "8-channel P300", "value": "p300_multi_gen2"},
            {"display_name": "None", "value": "none"},
        ],
        default="p20_single_gen2"
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
    default="left"
    )


#Protocol context - https://docs.opentrons.com/v2/tutorial.html
def run(protocol: protocol_api.ProtocolContext):

    #Parser for the csv runtime parameter. Note that this gets a list where each item is a row in the csv file
    #Each item in the child lists corresponds to a single cell within its row. Data is represented as string.
    csv_data_list = protocol.params.svt_csv.parse_as_csv()

    #Loading tip rack, after the api name, put comma and then which slot it is in on the Opentron
    tip_rack_300 = protocol.load_labware(load_name="opentrons_96_tiprack_300ul", location=9)
    #Loading pipette, 20uL single tip
    s_300_pip = protocol.load_instrument(instrument_name="p300_single_gen2", mount=protocol.params.pipette_loc, tip_racks=[tip_rack_300])

    #Load the extraneous pipette
    if protocol.params.pipette_ext_choice != "none":
        #Load in the extraneous pipette, although it's not used.
        protocol.load_instrument(instrument_name=protocol.params.pipette_ext_choice, mount=protocol.params.pipette_ext_loc)


    #Load the labware with its api name, look it up in labware library - https://labware.opentrons.com/
    #Add labware to dictionary
    labware_dict = dict([('Falcon_Water_Rack', protocol.load_labware("opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical", 2)), 
                         ('10uM_SnapCaps', protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)),
                         ('100uM_ScrewCaps', protocol.load_labware("opentrons_24_tuberack_generic_2ml_screwcap", 4))])

    #----------End of modifications (2)

    #Code to read from csv to "define intial volumes"
    #Discard the first row of csv, since that's all the titles of the columns.
    csv_iv_data = csv_data_list[2:]
    
    #Define the liquid "water"
    water = protocol.define_liquid(
                name='Hyclone Water',
                description='Hyclone Water',
                display_color='#00FF00'
            )
    
    #Load water into the falcon rack
    getLabwareObject(labware_dict, 'Falcon_Water_Rack')['A4'].load_liquid(liquid=water, volume=25000)

    #Get which tip to start with
    starting_tip = str(protocol.params.starting_tip_let) + str(protocol.params.starting_tip_num)
    s_300_pip.starting_tip = tip_rack_300.well(starting_tip)
    #Set first_transfer to false initially because we'll transfer 180uL before using the CSV
    first_transfer = False

    #Define var for remainder of num samples, check if it's perfectly filling rows of 6 wells
    remainder = 0

    #If there's a remainder in the number of samples, aka not perfectly filling up a row
    if (protocol.params.num_samples % 6) != 0:
        num_rows = (protocol.params.num_samples // 6) + 1
        remainder = protocol.params.num_samples % 6
    #Else, get the perfect amt of rows
    else:
        num_rows = protocol.params.num_samples // 6   

    protocol.comment(f'Remainder = {remainder}')
    protocol.comment(f'Rows = {num_rows}') 

    #----------------------------------------Step 1----------------------------------------#

    #Pick up the tip, to transfer water
    s_300_pip.pick_up_tip()

    #First, automatically transfer 180uL water to each sample of working solution
    for row in range(num_rows):
        #If we're at the last row
        if row == (num_rows - 1):
            #If the last row is not full
            if remainder != 0:
                for col in range(remainder):
                    #Aspirate/dispense the liquid
                    s_300_pip.aspirate(180, getLabwareObject(labware_dict, 'Falcon_Water_Rack')["A4"], rate=2.0)
                    s_300_pip.dispense(180, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col],rate=2.0)
                    s_300_pip.blow_out()
            else:
                for col in range(6):
                    #Aspirate/dispense the liquid
                    s_300_pip.aspirate(180, getLabwareObject(labware_dict, 'Falcon_Water_Rack')["A4"], rate=2.0)
                    s_300_pip.dispense(180, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col], rate=2.0)
                    s_300_pip.blow_out()

        #If we're at any other row (aka, a full row)
        else:
            for col in range(6):
                #Aspirate/dispense the liquid
                s_300_pip.aspirate(180, getLabwareObject(labware_dict, 'Falcon_Water_Rack')["A4"], rate=2.0)
                s_300_pip.dispense(180, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col], rate=2.0)
                s_300_pip.blow_out()

    #Change the pipette dispense speed for this chunk of code to 15uL/s
    s_300_pip.flow_rate.dispense = 50

    #----------------------------------------Step 2----------------------------------------#
    for csv_row in csv_iv_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[1] != "":
            #Define variables from CSV columns
            source_labware = csv_row[1]
            source_well = csv_row[2]
            destination_labware = csv_row[3]
            destination_well = csv_row[4]
            transfer_volume = float(csv_row[5])
            pick_up_tip = str(csv_row[6])

            curr_source_labware = getLabwareObject(labware_dict, source_labware)
            curr_destination_labware = getLabwareObject(labware_dict, destination_labware)

            if pick_up_tip == 'TRUE':

                if first_transfer == True:
                    #Pick up the first tip
                    s_300_pip.pick_up_tip()
                    first_transfer = False
                else:
                    #Touch tip first, in the previous well to prevent liquid from falling while pipette is moving
                    s_300_pip.touch_tip()
                    #Discard the previous tip
                    s_300_pip.drop_tip()
                    #Pick up the next tip, will always pick up the next available tip
                    s_300_pip.pick_up_tip()

                
                #Now, start the volume transfer
                
                #Aspirate [take in] liquid, with this format (amount in microliters, well location)
                s_300_pip.aspirate(transfer_volume, curr_source_labware[source_well], rate=2.0)
                #Dispense liquid, with this format (amount in microliters, well location)
                s_300_pip.dispense(transfer_volume, curr_destination_labware[destination_well].top())
                s_300_pip.blow_out()


            elif pick_up_tip == 'FALSE':
                if first_transfer == True:
                    #Pick up the first tip
                    s_300_pip.pick_up_tip()
                    first_transfer = False

                #Aspirate [take in] liquid, with this format (amount in microliters, well location)
                s_300_pip.aspirate(transfer_volume, curr_source_labware[source_well], rate=2.0)
                #Dispense liquid, with this format (amount in microliters, well location)
                s_300_pip.dispense(transfer_volume, curr_destination_labware[destination_well].top())
                s_300_pip.blow_out()

            else:

                protocol.comment('Please specify whether to use new or same tip')

    #Return the pipette dispense speed to default uL/sec
    s_300_pip.flow_rate.dispense = 92.86

    #Touch tip first, in the previous well to prevent liquid from falling while pipette is moving
    s_300_pip.touch_tip()
    #Discard the previous tip
    s_300_pip.drop_tip()

    #----------------------------------------Step 3----------------------------------------#

    #First, automatically transfer 180uL water to each sample of working solution
    for row in range(num_rows):
        #If we're at the last row
        protocol.comment(f'Current row: {row}')
        
        if row == (num_rows - 1):
            #If the last row is not full
            if remainder != 0:
                protocol.comment(f'Last row: {num_rows - 1} and num_rows: {num_rows}')
                for col in range(remainder):
                    #Pick up a new tip
                    s_300_pip.pick_up_tip()
                    #Do a mix before aspiration, to make sure the powder is evenly distributed within the well
                    s_300_pip.mix(3, 100, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col], rate=2.0)
                    #Aspirate/dispense the liquid
                    s_300_pip.aspirate(20, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col])
                    s_300_pip.dispense(20, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col], rate=2.0)
                    #Blow out first, to prevent liquid from falling while pipette is moving
                    s_300_pip.blow_out()
                    #Drop the tip, since we need a new tip each time
                    s_300_pip.drop_tip()
            #If the last row is only partially full
            else:
                for col in range(6):
                    #Pick up a new tip
                    s_300_pip.pick_up_tip()
                    #Do a mix before aspiration, to make sure the powder is evenly distributed within the well
                    s_300_pip.mix(3, 100, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col], rate=2.0)
                    #Aspirate/dispense the liquid
                    s_300_pip.aspirate(20, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col])
                    s_300_pip.dispense(20, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col], rate=2.0)
                    #Blow out first, to prevent liquid from falling while pipette is moving
                    s_300_pip.blow_out()
                    #Drop the tip, since we need a new tip each time
                    s_300_pip.drop_tip()
        #If we're at any other row (aka, a full row)
        else:
            for col in range(6):
                #Pick up a new tip
                s_300_pip.pick_up_tip()
                #Do a mix before aspiration, to make sure the powder is evenly distributed within the well
                s_300_pip.mix(3, 100, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col], rate=2.0)
                #Aspirate/dispense the liquid
                s_300_pip.aspirate(20, getLabwareObject(labware_dict, '100uM_ScrewCaps').rows()[row][col])
                s_300_pip.dispense(20, getLabwareObject(labware_dict, '10uM_SnapCaps').rows()[row][col], rate=2.0)
                #Blow out first, to prevent liquid from falling while pipette is moving
                s_300_pip.blow_out()
                #Drop the tip, since we need a new tip each time
                s_300_pip.drop_tip()



        
