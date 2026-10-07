# Golden Gate assembly, transformation, and plating protocol
# Written by Fankang Meng, and Koray Malci Imperial College London

import os
import tkinter
from tkinter import filedialog, messagebox
import csv
import json
import sys

def main():

	# GETTING USER INPUT
	dna_fixed_plate_map_filename = ask_fixed_dna_plate_map_filename()
	dna_customised_plate_map_filename = ask_customised_dna_plate_map_filename()
	combinations_filename = ask_combinations_filename()
	template_folder_path_config = get_template_path_config()
	output_folder_path_config = get_output_folder_path_config()

	# Load in CSV files as a dict containing lists of lists.
	dna_plate_map_dict = generate_plate_maps(dna_fixed_plate_map_filename, dna_customised_plate_map_filename)
	combinations_to_make = generate_combinations(combinations_filename)
	check_number_of_combinations( combinations_to_make)

	# Generate and save output plate maps.
	generate_and_save_output_plate_maps(combinations_to_make, output_folder_path_config)

	# Create a protocol file.
	create_protocol(dna_plate_map_dict, combinations_to_make, template_folder_path_config, output_folder_path_config)


# Functions for getting user input
def get_output_folder_path_config():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose output folder", '''You will now select the folder to save the protocol and the final plate map. ''')
    config = filedialog.askdirectory(title="Choose output folder")
    if not config:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return config

def get_template_path_config():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose workflow file", '''You will now choose "cloning_workflow.py"''')
    config = filedialog.askopenfilename(title="Choose workflow file")
    if not config:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return config

def ask_fixed_dna_plate_map_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Welcome to Slowpoke!", '''
~~~ Welcome to Slowpoke ~~~

This program will guide you through an OT-2 cloning protocol design.
''')
    messagebox.showinfo("Select the fixed toolkit map", '''In the upcoming file browser, open the "Cloning" subfolder of Slowpoke and select "fixed_toolkit_map.csv"''')
    fixed_dna_plate_map_filename = filedialog.askopenfilename(title = "Select fixed toolkit map", filetypes = (("CSV files","*.CSV"),("all files","*.*")))
    if not fixed_dna_plate_map_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return fixed_dna_plate_map_filename

def ask_customised_dna_plate_map_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Choose the custom parts map", '''You will now choose "custom_parts_map.csv"''')
    customised__dna_plate_map_filename = filedialog.askopenfilename(title = "Choose the custom parts map", filetypes = (("CSV files","*.CSV"),("all files","*.*")))
    if not customised__dna_plate_map_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return customised__dna_plate_map_filename

def ask_combinations_filename():
    window = tkinter.Tk()
    window.withdraw()
    messagebox.showinfo("Select file containing combinations to make", '''You will now choose "combination-to-make.csv"''')
    combinations_filename = filedialog.askopenfilename(title = "Select file containing combinations to make.", filetypes = (("CSV files","*.CSV"),("all files","*.*")))
    if not combinations_filename:
        messagebox.showinfo("Cancel", "Operation cancelled. The program will now exit.")
        sys.exit()
    return combinations_filename

def generate_plate_maps(filename1, filename2):
	plate_maps = {}
	plate_map1 = []
	plate_map2 = []
	with open(filename1, "r") as file:
		for row in csv.reader(file, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				plate_map1.append(row)
	plate_name1 = os.path.splitext(os.path.basename(filename1))[0]
	plate_maps[plate_name1] = plate_map1

	with open(filename2, "r") as file:
		for row in csv.reader(file, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				plate_map2.append(row)
	plate_name2 = os.path.splitext(os.path.basename(filename2))[0]
	plate_maps[plate_name2] = plate_map2
	return plate_maps

def generate_combinations(combinations_filename):
	combinations_to_make = []
	with open(combinations_filename, "r") as f:
		for row in csv.reader(f, dialect='excel'):
			if len(row) == 0:
				continue
			if row[0]:
				if '\ufeff' in row[0]:
					row[0] = str(row[0].replace(u'\ufeff',''))
				combinations_to_make.append({
											"name": row[0],
											"parts": [x for x in row[1:] if x]
											})
	return combinations_to_make

def check_number_of_combinations( combinations_to_make): 
	number_of_combinations = len(combinations_to_make)
	if number_of_combinations > 96:
		raise ValueError('Too many combinations ({0}) requested. Max for single combinations is 96.'.format(number_of_combinations))


# Functions for creating output files
def generate_and_save_output_plate_maps(combinations_to_make, output_folder_path):
	# Split combinations_to_make into 8x6 plate maps.
	output_plate_map_flipped = []
	for i, combo in enumerate(combinations_to_make):
		name = combo["name"]
		if i % 2 == 0:
			# new column
			output_plate_map_flipped.append([name])
		else:
			output_plate_map_flipped[-1].append(name)
	print("output_plate_map_flipped", output_plate_map_flipped)

	# Correct row/column flip.
	output_plate_map = []
	for i, row in enumerate(output_plate_map_flipped):
		for j, element in enumerate(row):
			if j >= len(output_plate_map):
				output_plate_map.append([element])
			else:
				output_plate_map[j].append(element)
	print("output_plate_map", output_plate_map)

	output_filename = os.path.join(output_folder_path, "Agar_plate.csv")
	with open(output_filename, 'w+', newline='') as f:
		writer = csv.writer(f)
		for row in output_plate_map:
			writer.writerow(row)

def create_protocol(dna_plate_map_dict, combinations_to_make, protocol_template_path, output_folder_path):

	# Get the contents of colony_pick_template.py, which contains the body of the protocol.
	with open(protocol_template_path) as template_file:
		template_string = template_file.read()
	with open(output_folder_path + '/' + 'protocol_for_cloning.py', "w+") as protocol_file:
		# Paste in plate maps at top of file.
		protocol_file.write('dna_plate_map_dict = ' + json.dumps(dna_plate_map_dict) + '\n\n')
		protocol_file.write('combinations_to_make = ' + json.dumps(combinations_to_make) + '\n\n')
		# Paste the rest of the protocol.
		protocol_file.write(template_string)

# Call main function
if __name__ == '__main__':
	main()
    
# Display success message
messagebox.showinfo("Completed", "The protocol has been successfully generated!")
