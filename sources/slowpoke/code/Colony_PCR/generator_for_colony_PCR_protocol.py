# Colony PCR protocol generator
# Written by Fankang Meng and Koray Malci Imperial College London
#2024

import os
import tkinter
from tkinter import filedialog, messagebox
import csv
import json
import datetime
import time
import sys

def main():

	# GETTING USER INPUT
	pcr_deck_map_filename = ask_pcr_deck_map_filename()
	colony_template_map_filename = ask_colony_template_map_filename()
	pcr_recipe_filename = ask_pcr_recipe_filename()
	template_folder_path_config = get_template_path_config()
	output_folder_path_config = get_output_folder_path_config()

	# Load in CSV files as a dict containing lists of lists.
	pcr_deck_colony_template_maps_dict = pcr_deck_colony_template_maps(pcr_deck_map_filename, colony_template_map_filename)
	pcr_recipe_to_make = generate_pcr_recipe(pcr_recipe_filename)
	check_number_of_combinations(pcr_recipe_to_make)

	# Create a protocol file.
	create_protocol(pcr_deck_colony_template_maps_dict, pcr_recipe_to_make, template_folder_path_config, output_folder_path_config)

    

# Functions for getting user input
def get_output_folder_path_config():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose output folder", "You will now select the folder to save the protocol. ")
    config = filedialog.askdirectory(title="Choose output folder")
    if not config:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit() 
    return config

def get_template_path_config():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose colony PCR workflow", '''You will now choose "colony_PCR_workflow.py" ''')
    config = filedialog.askopenfilename(title="Choose colony PCR workflow file")
    if not config:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit() 
    return config

def ask_pcr_deck_map_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Welcome to Slowpoke!", '''
~~~ Welcome to Slowpoke ~~~

This program will guide you through an OT-2 colony PCR protocol design.
''')
    messagebox.showinfo("Choose the PCR deck map file", '''In the upcoming file browser, open the "Colony_PCR" subfolder of Slowpoke and select "pcr_deck_map.csv"''')
    ask_pcr_deck_map_filename = filedialog.askopenfilename(title="Choose the PCR deck map file", filetypes=(("CSV files", "*.CSV"), ("all files", "*.*")))    
    # Check if the user clicked "Cancel" or closed the dialog
    if not ask_pcr_deck_map_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()    
    return ask_pcr_deck_map_filename

def ask_colony_template_map_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose the colony template map file", '''You will now choose "colony_template_map.csv" ''')
    ask_colony_template_map_filename = filedialog.askopenfilename(title = "Choose the colony template map file", filetypes = (("CSV files","*.CSV"),("all files","*.*")))
    if not ask_colony_template_map_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return ask_colony_template_map_filename

def ask_pcr_recipe_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Select the PCR recipe file", '''You will now choose Select the "pcr_recipe_to_make.csv" ''')
    ask_pcr_recipe_filename = filedialog.askopenfilename(title = "Select the PCR recipe file", filetypes = (("CSV files","*.CSV"),("all files","*.*")))
    if not ask_pcr_recipe_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return ask_pcr_recipe_filename

def pcr_deck_colony_template_maps(filename1, filename2):
	pcr_deck_colony_template_maps = {}
	pcr_deck_map = []
	colony_template_map = []
	with open(filename1, "r") as file:
		for row in csv.reader(file, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				pcr_deck_map.append(row)
	pcr_deck_name = os.path.splitext(os.path.basename(filename1))[0]
	pcr_deck_colony_template_maps[pcr_deck_name] = pcr_deck_map

	with open(filename2, "r") as file:
		for row in csv.reader(file, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				colony_template_map.append(row)
	colony_template_map_name = os.path.splitext(os.path.basename(filename2))[0]
	pcr_deck_colony_template_maps[colony_template_map_name] = colony_template_map
	return pcr_deck_colony_template_maps

def generate_pcr_recipe(combinations_filename):
	pcr_recipe_to_make = []
	with open(combinations_filename, "r") as f:
		for row in csv.reader(f, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				pcr_recipe_to_make.append({
											"name": row[0],
											"parts": [x for x in row[1:] if x]
											})
	return pcr_recipe_to_make

def check_number_of_combinations( combinations_to_make): 
	number_of_combinations = len(combinations_to_make)


def create_protocol(pcr_deck_colony_template_maps_dict, pcr_recipe_to_make, protocol_template_path, output_folder_path):
	# Get the contents of colony_pick_template.py, which contains the body of the protocol.
	with open(protocol_template_path) as template_file:
		template_string = template_file.read()
	folder_time = datetime.datetime.now().strftime("%Y_%m_%d")
	with open(output_folder_path + '/' + 'colony_PCR_protocol_'+ folder_time + '.py', "w+") as protocol_file:
		# Paste in plate maps at top of file.
		protocol_file.write('pcr_deck_colony_template_maps_dict = ' + json.dumps(pcr_deck_colony_template_maps_dict) + '\n\n')
		protocol_file.write('pcr_recipe_to_make = ' + json.dumps(pcr_recipe_to_make) + '\n\n')
		# Paste the rest of the protocol.
		protocol_file.write(template_string)

# Call main function
if __name__ == '__main__':
	main()

# Display success message
messagebox.showinfo("Completed", "The protocol has been successfully generated!")
