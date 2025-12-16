import re
import os

def split_lin_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    sections = []
    current_section = []

    for line in lines:
        if line.startswith("LINE"):
            if current_section:
                sections.append(''.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    # Add the last section if it exists
    if current_section:
        sections.append(''.join(current_section))

    # Add the first line as its own section
    if sections:
        first_line = sections.pop(0)
        sections.insert(0, first_line.split('\n')[0] + '\n')

    return sections

def process_lin_sections(sections):
    for n, sec in enumerate(sections):
        if n == 0:
            continue
        else:
            sec = sec.split('"')
            sec[3] = sec[3].replace('\n\t','')
            sec = '"'.join(sec)
            if '\n\tLONGNAME' not in sec:
                sec = sec.replace('LONGNAME', '\n\tLONGNAME')
            if '\n\tALLSTOPS' not in sec:
                sec = sec.replace('ALLSTOPS', '\n\tALLSTOPS')
            if '\n\tMODE' in sec:
                sec = sec.replace('\n\tMODE', 'MODE')
            sec = sec.replace('\t','     ')
        sections[n] = sec

    return sections

# Example usage
data_location = os.path.join(os.getcwd(),'Files')
output_folder = os.path.join(os.getcwd(),'Outputs')

# Create output folder where script is located.
if not os.path.exists(output_folder):
    os.makedirs(output_folder, exist_ok=True)

for file in os.listdir(data_location):
    if '.LIN' in file or '.lin' in file:
        filepath = os.path.join(data_location, file)
        sections = split_lin_file(filepath)
        lines = process_lin_sections(sections)
        with open(os.path.join(output_folder, file), 'w') as output_file:
            output_file.writelines(lines)