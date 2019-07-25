import os
import tkinter as tk
from tkinter import ttk, messagebox
from common_funcs import process_lin
from WidgetTemplates import LabelledEntry, TextLog, CreateToolTip
import summarise_line_files as sl

def kmp_search(s, seq):
    seq_i = 0
    i = 0
    occurences = []
    while i < len(s):
        if s[i] == seq[seq_i]:
            seq_i += 1
            i += 1
            if seq_i == len(seq):
                occurences.append(i - seq_i)
                seq_i = 0
        else:
            seq_i = 0
            i += 1
    return occurences
        
class SummaryTab:
    def __init__(self, note_book, general,name=""):
        self.current_dir = os.path.dirname(__file__)
        
        self.frame = ttk.Frame(note_book)
        note_book.add(self.frame, text=name)
        self.gen = general

        lf = ttk.Labelframe(self.frame, text="Explanation")
        lf.pack(padx=5, pady=5, fill="x")
        ttk.Label(lf,
                text='''Create a summary of a lin file
Converts a lin file into CSV format 
CSV Lookup files of nodes to main Urban Areas are required
Additional lookups to cordons and local autority are required for the extended summary''',
                  style="Head.TLabel").pack(side="top", anchor="w")
            
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(side="top")
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side="top")
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="top")
        
        self.lin_input = tk.StringVar()
        self.summary_file = tk.StringVar()
        self.urban_defs = tk.StringVar()
        self.la_defs = tk.StringVar()
        self.cordon_defs = tk.StringVar()
        self.node_file = tk.StringVar()
        
        # Default values
        '''file_name = "bus_lin.lin"
        self.lin_input.set(("..\\..\\41456 - LATIS Scoping\\TMfS18 PT Modelling"
                            "\\voyager-converter-tmfs\\Output Files"
                            "\\bus_lin_TMfS18.lin"))
        self.summary_file.set(os.path.join("Intermediate", 
                                           "summary_%s.csv" % "".join(file_name.split(".")[:-1])))
        self.urban_defs.set(("..\\..\\41456 - LATIS Scoping"
                             "\\TMfS18 PT Modelling\\voyager-converter-tmfs"
                             "\\Node Lookup Files\\urban_areas_lookup.csv"))
        self.node_file.set(("..\\..\\41456 - LATIS Scoping\\TMfS18 PT Modelling"
                            "\\04 Networks\\Updated Network\\nodes_coords.csv"))
        self.la_defs.set(("..\\..\\41456 - LATIS Scoping\\TMfS18 PT Modelling"
                          "\\04 Networks\\Updated Network\\nodes_la_lookup.csv"))
        self.cordon_defs.set(("..\\..\\41456 - LATIS Scoping"
                              "\\TMfS18 PT Modelling\\voyager-converter-tmfs"
                              "\\Node Lookup Files\\cordon_lookup.csv"))'''

        lin_input = LabelledEntry(input_frame, "LIN File", self.lin_input, w=50,
                                  tool_tip_text=("Path to the Cube LIN file to "
                                                 "be summarised.\nShould be "
                                                 "the standard format and "
                                                 "begin each service/line "
                                                 "with 'LINE='"))
        lin_input.add_browse(self.current_dir)
        urban_defs = LabelledEntry(input_frame, "Urban Areas", self.urban_defs, w=50,
                                   tool_tip_text=("Path to the file containing "
                                                  "Cube nodes ('N') assigned "
                                                  "to urban areas "
                                                  "('urban_area') (integer)."
                                                  " Used to identify if the "
                                                  "service is within an urban "
                                                  "area"))
        urban_defs.add_browse(self.current_dir)
        la_defs = LabelledEntry(input_frame, "Node Local Authority", self.la_defs, w=50,
                                tool_tip_text=("Path to the file containing "
                                               "Cube nodes ('N') assigned to a "
                                               "local authority ('LA'). Used to "
                                               "identify start and end LA"))
        
        la_defs.add_browse(self.current_dir)
        cordon_defs = LabelledEntry(input_frame, "Node Cordons", self.cordon_defs, w=50,
                                tool_tip_text=("Path to the file containing "
                                               "Cube nodes ('N') assigned to "
                                               "a Cordon zone (string). Used to "
                                               "identify type of service (If "
                                               "it passes a Cordon boundary)"))
        
        cordon_defs.add_browse(self.current_dir)
        node_defs = LabelledEntry(input_frame, "Node Coordinates", self.node_file, w=50,
                                  tool_tip_text=("Path to the file containing "
                                                 "Cube nodes ('N') and "
                                                 "their coordinates. Used to calculate"
                                                 "End-to-End distance"))
        node_defs.add_browse(self.current_dir)
        summary_file = LabelledEntry(input_frame, "Output File", self.summary_file, w=50,
                                     tool_tip_text="Path to save the summary to")
        summary_file.add_browse(self.current_dir, save=True, 
                                types=(("CSV", "*.csv")), extension=".csv")
        
        
        # view_button = ttk.Button(button_frame, text="Edit Changes File", command=lambda: self.callback_view_file(self.changes_file.get())).pack(side="left")
        read_button = ttk.Button(
            button_frame, text="Create Summary", style="DS.TButton",
            command=self.callback_summarise_lin)
        read_button.pack(side="left")
        CreateToolTip(read_button, text=("Convert to CSV. Only requires "
                                         "Urban Areas lookup"))
        flag_button = ttk.Button(
            button_frame, text="Extended Summary", style="DS.TButton",
            command=self.callback_flag_lin)
        flag_button.pack(side="left")
        CreateToolTip(flag_button, text="Create a CSV summary, using all lookups")

        self.log_frame = ttk.LabelFrame(self.frame, text="Log")
        self.log_frame.pack(side="top")
        self.log = TextLog(self.log_frame)
        
    def callback_view_file(self, file_path):
        try:
            os.startfile(file_path)
        except FileNotFoundError:
            if not messagebox.askokcancel("Create File", "Create a blank file at %s?" % file_path):
                return 
            else:
                with open(file_path, "w", newline="") as file:
                    s = ("# This file contains the sequences to replace in "
                         "the LIN files\n#\n# Sequences can be changed using "
                         "the notation:\n#\n#       'start_node':'end_node':'"
                         "new_node_1-new_node_2'\n#       1000-1005:1000-1001-"
                         "1002-1003-1004-1005\n#       If the nodes are not "
                         "stopped at, precede them with p \n#       "
                         "e.g. 1000-p1005:1000-p1001-p1002-p1003-p1004-p1005\n"
                         "#\n##################################"
                         "###################################\n\n"
                         "#88377-74908:88377-1232121-74908\n#88377-p74908:"
                         "88377-p1232121-p74908")
                    for x in s.split("\n"):
                        file.write(x)
                        file.write("\r\n")
                self.callback_view_file(file_path)
                
    def callback_summarise_lin(self):
        sl.summarise_main(self.lin_input.get(), self.summary_file.get(),
                          self.urban_defs.get(),
                          operator_lookup_file=self.gen.files["ops"].get())
        self.log.add_message("Finished", color="GREEN")

    def callback_flag_lin(self):
        sl.flag_main(self.lin_input.get(), self.summary_file.get(),
                     self.urban_defs.get(), 
                     operator_lookup_file=self.gen.files["ops"].get(),
                     node_lookup_file=self.node_file.get(), 
                     la_lookup_file=self.la_defs.get(),
                     cordon_lookup_file=self.cordon_defs.get())
        self.log.add_message("Finished", color="GREEN")

    def replace_sequence(self):
        # Read the patching file 
        with open(self.changes_file.get(), "r") as file:
            data = file.readlines()
            seq_dict = {}
            for row in data:
                if  row[0] == "#" or row == "\n":
                    continue
                row = row.strip("\n")
                old, new = row.split(":")
                old = old.split("-")
                new = new.split("-")
                seq_dict[tuple(old)] = new
    
        # Read the lin file into dicts with one string for each line
        with open(self.lin_input.get(), "r") as file:
            line_info_dict = {} # Dict of everything but line nodes
            line_dict = {}  # Dict of line nodes
            data = file.readlines()
            looking_for_service = True
            current_service = None
            for row in data:
                if looking_for_service is True and "LINE NAME=" in row:
                    looking_for_service = False
                    row = [x.strip() for x in row.split(",")]
                    current_service = row[0]
                    line_info = ",".join(row)
                elif row[0] == ";":
                    continue
                elif looking_for_service is False and row == "\n":
                    line_info = line_info.replace("\n", "")
                    line_info = line_info.replace("\t", " ")
                    line_info_dict[current_service] = line_info.split("N=")[0]
                    line_dict[current_service] = line_info.split("N=")[1].split(",")
                    looking_for_service = True
                    current_service = None
                else:
                    row = [x.strip() for x in row.split(",")]
                    line_info += ",".join(row)
                    
        with open(self.lin_output.get(), "w", newline="") as file:
            file.write(";;<<PT>><<LINE>>;;\n")
            num_replacements = 0
            # Replace the node sequences with new ones
            for line, node_seq in line_dict.items():
                new_nodes = node_seq
                # Check if anything needs replacing
                for old_seq, new_seq in seq_dict.items():
                    old_seq = [x.replace("p", "-") for x in old_seq]
                    for index in kmp_search(node_seq, old_seq):
                        num_replacements += 1
                        print("Replaced a sequence in %s, position %d" % (
                                line.replace("LINE NAME=",""), index))
                        del new_nodes[index:index + len(old_seq)]
                        for j, node in enumerate(new_seq):
                            new_nodes.insert(index + j, node.replace("p", "-"))
                print(new_nodes)
                # Write the (new) sequence to file
                line_string = line_info_dict[line] + "N=" + ", ".join(new_nodes)
                result = process_lin(line_string)
                file.write(result)
                file.write('\n\n')
                
        self.log.add_message("Finished", color="GREEN")
        self.log.add_message("Replaced %d occurences" % num_replacements)
                    
                    
                    
                    
