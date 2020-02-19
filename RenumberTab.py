import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from common_funcs import process_lin, print_rail_lin
from WidgetTemplates import LabelledEntry, TextLog, CreateToolTip
from summarise_line_files import read_lin_file

        
class RenumberTab:
    """
    
    """
    def __init__(self, note_book, general,name="", default_vars=None):
        self.current_dir = os.path.dirname(__file__)
        
        self.frame = ttk.Frame(note_book)
        note_book.add(self.frame, text=name)
        self.gen = general

        lf = ttk.Labelframe(self.frame, text="Explanation")
        lf.pack(padx=5, pady=5, fill="x")
        ttk.Label(lf,
                text='''Renumber the lines in a file according to a base version
                Will also output a lookup of the line names as line_name_lookup.csv. Lines files
                need the naming convention ***AM.LIN/***IP.LIN/***PM.LIN''',
                  style="Head.TLabel").pack(side="top", anchor="w")
            
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(side="top")
        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(side="top")
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side="top")
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="top")
        
        self.lin_input = tk.StringVar()
        self.lin_lookup = tk.StringVar()
        self.other_lookup = tk.StringVar()
        self.lin_output = tk.StringVar()
        

        lin_input = LabelledEntry(input_frame, "Input LIN File", self.lin_input, w=50,
                                  tool_tip_text=("Path to the Cube LIN file to "
                                                 "Renumber. AM version"))
        lin_input.add_browse(self.current_dir)
        lin_lookup = LabelledEntry(input_frame, "Lookup LIN File", self.lin_lookup, w=50,
                                   tool_tip_text=("Path to the file containing "
                                                  "the numbers to line numbers to use"
                                                  ". AM version. Only needs to be "
                                                  "supplied if no 'Alternative Lookup"
                                                  " is available"))
        lin_lookup.add_browse(self.current_dir)
        other_lookup = LabelledEntry(input_frame, "Alternative Lookups", self.other_lookup, w=50,
                                tool_tip_text=("Path to the file containing "
                                               "a previous lookup. If not blank "
                                               "this will be used over the LIN lookup "))
        
        other_lookup.add_browse(self.current_dir)
        lin_output = LabelledEntry(input_frame, "Output LIN File", self.lin_output, w=50,
                                tool_tip_text=("Can be same as the input"))
        
        lin_output.add_browse(self.current_dir, save=True, 
                              types=(("LIN", "*.lin")), extension=".lin")
        
        
        read_button = ttk.Button(
            button_frame, text="Renumber", style="DS.TButton",
            command=self.callback_renumber)
        read_button.pack(side="left")
        CreateToolTip(read_button, text=("Renumber the input LIN file "))

        ######## 
        # Convert line files
        
        self.con_lin_input = tk.StringVar()
        self.con_lin_output = tk.StringVar()
        self.con_csv_input = tk.StringVar()
        self.con_csv_output = tk.StringVar()
        left_frame = ttk.Frame(bottom_frame)
        left_frame.pack(side="top")
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side="top")
        lin_input = LabelledEntry(left_frame, "Input LIN File", self.con_lin_input, w=50,
                                  tool_tip_text=("Path to the Cube LIN file to "
                                                 "Convert"))
        lin_input.add_browse(self.current_dir)
        csv_output = LabelledEntry(left_frame, "Output CSV File", self.con_csv_output, w=50)
        csv_output.add_browse(self.current_dir, save=True, 
                              types=(("CSV", "*.csv")), extension=".csv")
        lin_csv_button = ttk.Button(
            left_frame, text="Convert", style="DS.TButton",
            command=self.callback_lin_csv)
        lin_csv_button.pack(side="top")
            
        csv_input = LabelledEntry(right_frame, "Input CSV File", self.con_csv_input, w=50,
                                  tool_tip_text=("Path to the CSV file to "
                                                 "Convert"))
        csv_input.add_browse(self.current_dir)
        lin_output = LabelledEntry(right_frame, "Output LIN File", self.con_lin_output, w=50,
                                tool_tip_text=("Can be same as the input"))
        lin_output.add_browse(self.current_dir, save=True, 
                              types=(("LIN", "*.lin")), extension=".lin")
        csv_lin_button = ttk.Button(
            right_frame, text="Convert", style="DS.TButton",
            command=self.callback_csv_lin)
        csv_lin_button.pack(side="top")
        

        self.log_frame = ttk.LabelFrame(self.frame, text="Log")
        self.log_frame.pack(side="top")
        self.log = TextLog(self.log_frame)
                
    def callback_renumber(self):
        renumber(self.lin_input.get(), self.lin_lookup.get(),
                          self.other_lookup.get(), self.lin_output.get())
        self.log.add_message("Finished", color="GREEN")
    def callback_csv_lin(self):
        csv_to_lin(self.con_csv_input.get(), self.con_lin_output.get())
    def callback_lin_csv(self):
        lin_to_csv(self.con_lin_input.get(), self.con_csv_output.get())

def renumber(input_lin, lookup_lin, other_lookup, output_lin):
    # Input Line File path - line numbers to use
    if other_lookup == "":
        other_lookup = "line_name_lookup.csv"
        am_line = lookup_lin
        ip_line = am_line.replace("AM.LIN", "IP.LIN")
        pm_line = am_line.replace("AM.LIN", "PM.LIN")
        in_line_files = [am_line, ip_line, pm_line]
        data = []
        for linefilepath in in_line_files:
            data.append({x["LINE NAME"]:x for x in read_lin_file(linefilepath)})
        line_lookup = {(v["LONGNAME"], v["OPERATOR"], ",".join(v["N"])):k 
                       for d in data for k, v in d.items()}
    else:
        with open(other_lookup, "r") as file:
            r = csv.reader(file)
            line_lookup = {(x[0], x[1], x[2]):x[3] for x in r}
            
    # Load the new lines file - line numbers to change
    am_line = input_lin
    ip_line = am_line.replace("AM.LIN", "IP.LIN")
    pm_line = am_line.replace("AM.LIN", "PM.LIN")
    in_line_files = [am_line, ip_line, pm_line]
    data = []
    for linefilepath in in_line_files:
        data.append({x["LINE NAME"]:x for x in read_lin_file(linefilepath)})
        
    # Change the line numbers
    current_line_number = max([int(x.strip("\"").replace("r", "")) for x in line_lookup.values()]) + 1
    for i in range(len(data)):
        used_lines = {k:0 for k in line_lookup.values()}
        for j in data[i]:
            old_line, stopping_pattern = data[i][j]["LINE NAME"], ",".join(data[i][j]["N"])
            operator, route_name = data[i][j]["OPERATOR"], data[i][j]["LONGNAME"]
            key = (route_name, operator, stopping_pattern)
            new_line = line_lookup.get(key, None)
            if new_line is None:
                new_line = "\"r%s\"" % current_line_number
                line_lookup[key] = new_line
                used_lines[new_line] = 1
                current_line_number += 1
            else:
                used_lines[new_line] += 1
            if new_line != old_line:
                print(old_line, new_line)
            if used_lines[new_line] > 1:
                # add a letter to differentiate
                new_line = new_line[:-1] + chr(used_lines[new_line] + 64) + "\""
            data[i][j]["LINE NAME"] = new_line
    print("Length of lookup ", len(line_lookup))
    
    # Output the line name lookup
    with open(other_lookup, "w", newline="") as file:
        w = csv.writer(file)
        w.writerows([list(k) + [v] for k, v in line_lookup.items()])
        
    # Print the new lines files
    am_line = output_lin
    ip_line = am_line.replace("AM.LIN", "IP.LIN")
    pm_line = am_line.replace("AM.LIN", "PM.LIN")
    out_line_files = [am_line, ip_line, pm_line]
    print_rail_lin(data, out_line_files)
    
def lin_to_csv(input_lin, output_csv):
    datar = [x for x in read_lin_file(input_lin)]
    for i in range(len(datar)):
        datar[i]["N"] = ",".join(datar[i]["N"])
        datar[i]["RT"] = ";".join([":".join([str(y) for y in x]) for x in datar[i]["RT"]])
    with open(output_csv, "w", newline="") as file:
        w = csv.DictWriter(file, [x for x in datar[0]])
        w.writeheader()
        w.writerows(datar)

def csv_to_lin(input_csv, output_lin):
    with open(input_csv) as file:
        r = csv.DictReader(file)
        datar = [x for x in r]
    for i in range(len(datar)):
        datar[i]["N"] = datar[i]["N"].split(",")
        datar[i]["RT"] = [[x.split(":")[0],int(x.split(":")[1])]  for x in datar[i]["RT"].split(";")]
    print_rail_lin([{x["LINE NAME"]:x for x in datar}], [output_lin])
        
    
    
    
