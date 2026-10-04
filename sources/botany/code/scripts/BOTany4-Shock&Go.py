from opentrons import protocol_api

import csv
import json
import math
from collections import defaultdict

#-------(Modify) Change name and description to suit your needs (1)
metadata = {
    "apiLevel": "2.20",
    "protocolName": "BOTany4-Shock&Go",
    "description": """Protocol for E. coli heat-shock transformation""",
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
    parameters.add_csv_file(variable_name="etp_csv",
                       display_name="BOTany4-Shock&Go-Table CSV",
                       description="Import the csv (.xslx) file for this protocol. Make sure to modify the values within first."
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
            {"display_name": "P300", "value": "p300_single_gen2"}
        ],
        default="p300_single_gen2"
    )

#Protocol context - https://docs.opentrons.com/v2/tutorial.html
def run(protocol: protocol_api.ProtocolContext):

    #Parser for the csv runtime parameter. Note that this gets a list where each item is a row in the csv file
    #Each item in the child lists corresponds to a single cell within its row. Data is represented as string.
    csv_data_list = protocol.params.etp_csv.parse_as_csv()

    #Discard the first row of csv, since that's all the titles of the columns.
    csv_trunc_data = csv_data_list[2:]

    #Get the names of the left and right pipettes as strings, ex. p20, p300
    left_pip_name = protocol.params.pipette_left_choice.split("_")[0]
    right_pip_name = protocol.params.pipette_right_choice.split("_")[0]

    tips_300 = protocol.load_labware(load_name="opentrons_96_tiprack_300ul", location=9)
    tips_20 = protocol.load_labware(load_name="opentrons_96_tiprack_20ul", location=1)

    #Load heating/cooling module and aluminum block
    #module_name = OT-2 module names (https://docs.opentrons.com/v2/new_modules.html#), location = slot num
    tc_mod = protocol.load_module(module_name="thermocyclerModuleV2")
    tc_mod.open_lid()
    tc_mod.set_block_temperature(temperature=4)


    #Load the labware with its api name, look it up in labware library - https://labware.opentrons.com/
    #Add labware to dictionary
    labware_dict = dict([
                         ('pcr_strip', tc_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")), 
                         ('media_rack', protocol.load_labware("opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical", 6)), 
                         ('cell_rack', protocol.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", 2)),
                         ('DNA_tube', protocol.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul", 3))
                        ])
    
    #Make a dictionary to store the loaded pipette objects
    pipette_dict = dict()

    #Load each pipette into the dictionary:
    #Left
    if left_pip_name == "p20":
        pipette_dict[left_pip_name] = protocol.load_instrument(instrument_name="p20_single_gen2", mount="left", tip_racks=[tips_20])
    elif left_pip_name == "p300":
        pipette_dict[left_pip_name] = protocol.load_instrument(instrument_name="p300_single_gen2", mount="left", tip_racks=[tips_300])
    #Right
    if right_pip_name == "p20":
        pipette_dict[right_pip_name] = protocol.load_instrument(instrument_name="p20_single_gen2", mount="right", tip_racks=[tips_20])
    elif right_pip_name == "p300":
        pipette_dict[right_pip_name] = protocol.load_instrument(instrument_name="p300_single_gen2", mount="right", tip_racks=[tips_300])

    # ----------------------LIQUID DEFINITIONS------------------------- #

    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[1] != "":

            #Define variables from CSV columns
            labware = csv_row[1]
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

    #Get the starting tips in this format: LetterNumber ex. A1
    left_starting_tip = str(protocol.params.left_starting_tip_let) + str(protocol.params.left_starting_tip_num)
    right_starting_tip = str(protocol.params.right_starting_tip_let) + str(protocol.params.right_starting_tip_num)

    #Set the starting tips for the tip racks:
    if left_pip_name == "p20":
        pipette_dict[str(left_pip_name)].starting_tip = tips_20.well(left_starting_tip)
    elif left_pip_name == "p300":
        pipette_dict[str(left_pip_name)].starting_tip = tips_300.well(left_starting_tip)
    if right_pip_name == "p20":
        pipette_dict[str(right_pip_name)].starting_tip = tips_20.well(right_starting_tip)
    elif right_pip_name == "p300":
        pipette_dict[str(right_pip_name)].starting_tip = tips_300.well(right_starting_tip)

    #Set the first transfer (aka var for checking if this is the first liquid transfer)
    first_transfer_left = True
    first_transfer_right = True
    #Var used to check if the tip has been used


    #Get the loaded pipettes as objects from the pipette dictionary
    left_pip_obj = getLabwareObject(pipette_dict, left_pip_name)
    right_pip_obj = getLabwareObject(pipette_dict, right_pip_name)

    p300 = pipette_dict.get("p300")
    if p300 is None:
        raise RuntimeError("This step requires a P300. Set either left or right pipette to 'p300' in the runtime params.")


    p20 = pipette_dict.get("p20")
    if p20 is None:
        raise RuntimeError("This step requires a P20. Set either left or right pipette to 'p300' in the runtime params.")
    

    # ----------------------TRANSFER COMPETENT CELLS------------------------- #
    # Column indices from your CSV
    SRC_LAB_COL = 8
    SRC_WELL_COL = 9
    DST_LAB_COL = 10
    DST_WELL_COL = 11
    VOLUME_COL = 12   # <-- 'Competent cell transfer volume' for this table

    # Group (src_lab, src_well) -> list of (dest_lab, dest_well) and matching volumes
    groups = defaultdict(lambda: {"dests": [], "vols": []})
    for row in csv_trunc_data:


        # skip rows without a source labware entry
        if not str(row[SRC_LAB_COL]).strip():
            continue

        src_lab  = str(row[SRC_LAB_COL]).strip()
        src_well = str(row[SRC_WELL_COL]).strip()
        dst_lab  = str(row[DST_LAB_COL]).strip()
        dst_well = str(row[DST_WELL_COL]).strip()

        # parse per-row volume (uL)
        vol_cell = row[VOLUME_COL] if len(row) > VOLUME_COL else ""
        try:
            vol = float(str(vol_cell).strip())
        except Exception:
            # skip rows with non-numeric volume
            continue
        if vol <= 0:
            continue

        groups[(src_lab, src_well)]["dests"].append((dst_lab, dst_well))
        groups[(src_lab, src_well)]["vols"].append(vol)


    # 2) (optional) mimic your previous rate=2.0 behavior once, not per row
    orig_asp, orig_disp = p300.flow_rate.aspirate, p300.flow_rate.dispense
    p300.flow_rate.aspirate = orig_asp * 2.0
    p300.flow_rate.dispense = orig_disp * 2.0

    # 3) One tip for the entire distribute step (or move pick/drop inside the loop to use one tip per source)
    # Do one distribute per source with a LIST of volumes
    for (src_lab, src_well), payload in groups.items():
        src_labware = getLabwareObject(labware_dict, src_lab)
        src = src_labware[src_well]

        dest_wells = [getLabwareObject(labware_dict, dl)[dw] for (dl, dw) in payload["dests"]]
        vols = payload["vols"]  # aligns 1:1 with dest_wells

        if not dest_wells:
            continue

        p300.pick_up_tip()
        p300.distribute(
            vols,                 # <-- list of per-destination volumes (uL)
            src,
            dest_wells,
            new_tip='never',
            disposal_volume=5,
            blow_out=True
        )
        p300.drop_tip()

    # 4) restore flow rates
    p300.flow_rate.aspirate = orig_asp
    p300.flow_rate.dispense = orig_disp


        
    # ----------------------TRANSFER DNA------------------------- #
    for csv_row in csv_trunc_data:
        #Check if the current row is empty, if it's empty then skip it
        if csv_row[16] != "":

            #Define variables from CSV columns
            source_labware = csv_row[16]
            source_well = csv_row[17]
            destination_labware = csv_row[18]
            destination_well = csv_row[19]
            transfer_volume = float(csv_row[20])
            pick_up_tip = str(csv_row[21])
            pipette_choice = csv_row[22]

            curr_source_labware = getLabwareObject(labware_dict, source_labware)
            curr_destination_labware = getLabwareObject(labware_dict, destination_labware)

            if pipette_choice == "Left":
                curr_pip = left_pip_obj
            elif pipette_choice == "Right":
                curr_pip = right_pip_obj

            #If we want to switch tips, pick up a new tip
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
                curr_pip.mix(2, 10, curr_destination_labware[destination_well], rate=3)
                curr_pip.blow_out()

            #If we want to keep using the same tip as before
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
                curr_pip.mix(2, 10, curr_destination_labware[destination_well], rate=3)
                curr_pip.blow_out()

            else:

                protocol.comment('Please specify whether to use new or same tip')

    #Discard the previous tip
    curr_pip.drop_tip()

    #Set the first transfer (aka var for checking if this is the first liquid transfer)
    first_transfer_left = True
    first_transfer_right = True

    # ----------------------------HEAT SHOCK -------------------------- #
    protocol.delay(minutes=10)

    tc_mod.set_block_temperature(
        temperature=42,
        hold_time_seconds=40)
    tc_mod.set_block_temperature(temperature=4)

    protocol.delay(minutes=5)
    
# ----------------------TRANSFER OUTGROWTH MEDIUM------------------------- #
    # Column indices from your CSV
    SRC_LAB_COL = 24
    SRC_WELL_COL = 25
    DST_LAB_COL = 26
    DST_WELL_COL = 27
    VOLUME_COL = 28   # <-- 'medium transfer volume' for this table

    # Group (src_lab, src_well) -> list of (dest_lab, dest_well) and matching volumes
    groups = defaultdict(lambda: {"dests": [], "vols": []})
    for row in csv_trunc_data:

        # skip rows without a source labware entry
        if not str(row[SRC_LAB_COL]).strip():
            continue

        src_lab  = str(row[SRC_LAB_COL]).strip()
        src_well = str(row[SRC_WELL_COL]).strip()
        dst_lab  = str(row[DST_LAB_COL]).strip()
        dst_well = str(row[DST_WELL_COL]).strip()

        # parse per-row volume (uL)
        vol_cell = row[VOLUME_COL] if len(row) > VOLUME_COL else ""
        try:
            vol = float(str(vol_cell).strip())
        except Exception:
            # skip rows with non-numeric volume
            continue
        if vol <= 0:
            continue

        groups[(src_lab, src_well)]["dests"].append((dst_lab, dst_well))
        groups[(src_lab, src_well)]["vols"].append(vol)


    # 2) (optional) mimic your previous rate=2.0 behavior once, not per row
    orig_asp, orig_disp = p300.flow_rate.aspirate, p300.flow_rate.dispense
    p300.flow_rate.aspirate = orig_asp * 2.0
    p300.flow_rate.dispense = orig_disp * 2.0

    # 3) One tip for the entire distribute step (or move pick/drop inside the loop to use one tip per source)
    # Do one distribute per source with a LIST of volumes
    for (src_lab, src_well), payload in groups.items():
        src_labware = getLabwareObject(labware_dict, src_lab)
        src = src_labware[src_well]

        dest_wells = [getLabwareObject(labware_dict, dl)[dw].top(z=0) for (dl, dw) in payload["dests"]]
        vols = payload["vols"]  # aligns 1:1 with dest_wells

        if not dest_wells:
            continue

        p300.pick_up_tip()
        p300.distribute(
            vols,                 # <-- list of per-destination volumes (uL)
            src,
            dest_wells,
            new_tip='never',
            disposal_volume=0,
            blow_out=False
        )
        p300.drop_tip()

    # 4) restore flow rates
    p300.flow_rate.aspirate = orig_asp
    p300.flow_rate.dispense = orig_disp


    # --------------CAP THE PCR STRIP TUBE TO PREVENT EVAPORATION------------ #
    protocol.pause("Cap the PCR strip tubes on TC and turn off the HEPA module")

    # -----------------INCUBATION AT 37C------------------- #
    tc_mod.set_block_temperature(
        temperature=37,
        hold_time_minutes=60)

    tc_mod.deactivate_block() 

    # -----------------MANUAL PLATING------------------- #
    protocol.pause("Time to plate the cells on agar plates")

