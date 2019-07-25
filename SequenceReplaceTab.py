import os
import tkinter as tk
from tkinter import ttk, messagebox
from common_funcs import process_lin
from WidgetTemplates import LabelledEntry, TextLog
from summarise_line_files import read_lin_file, single_add_rts_back_in

def all_bin(seq):
    tot = 2**len(seq)
    tot_len = len(bin(tot).split("b")[1])
    variations = [(bin(i).split("b")[1].zfill(tot_len-1)) for i in range(tot)]
    variations = [[int(y) for y in x] for x in variations]
    return variations

def all_node_variations(seq):
    bin_seqs = all_bin(seq)
    all_seqs = []
    for bin_seq in bin_seqs:
        all_seqs.append([x if stop == 1 else "p%s" % x
                        for x, stop in zip(seq, bin_seq)])
    return all_seqs

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
        
class SequenceReplaceTab:
    def __init__(self, note_book, general,name=""):
        self.current_dir = os.path.dirname(__file__)
        
        self.frame = ttk.Frame(note_book)
        note_book.add(self.frame, text=name)
        self.gen = general

        lf = ttk.Labelframe(self.frame, text="Explanation")
        lf.pack(padx=5, pady=5, fill="x")
        ttk.Label(lf,
                text=("Replace node sequences within a Cube LIN file with new "
                      "sequences.\nSee the header of the Changes File for format "
                      "specifications.\nOutput is a new LIN file with sequences "
                      "replaced"),
                  style="Head.TLabel").pack(side="top", anchor="w")
            
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(side="top")
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side="top")
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="top")
        
        self.lin_input = tk.StringVar()
        self.lin_output = tk.StringVar()
        self.changes_file = tk.StringVar()
        #self.lin_input.set(os.path.join("Output Files", "rail_lin.lin"))
        #self.lin_output.set(os.path.join("Output Files", "rail_lin_2.lin"))
        self.changes_file.set(os.path.join("Node Lookup Files", "sequence_patch.txt"))

        lin_input = LabelledEntry(input_frame, "Initial LIN", self.lin_input, 
                                  w=50, tool_tip_text=("Path to the Cube LIN "
                                                       "file that needs to be "
                                                       "patched.\nShould be the "
                                                       "standard format and "
                                                       "begin each service/line "
                                                       "with 'LINE='"))
        lin_input.add_browse(self.current_dir)
        changes_file = LabelledEntry(input_frame, "Changes File", 
                                     self.changes_file, w=50, 
                                     tool_tip_text=("Path to the file containing "
                                                    "sequence changes e.g. to "
                                                    "add nodes 101 and 102 "
                                                    "between 100 and 103 the "
                                                    "format is 100-103:100-101-102-103 "
                                                    "(Must include start and "
                                                    "end nodes)"))
        changes_file.add_browse(self.current_dir)
        lin_output = LabelledEntry(input_frame, "Output File", self.lin_output, 
                                   w=50, tool_tip_text="Path to save the new LIN file to")
        lin_output.add_browse(self.current_dir, save=True, types=(("LIN", "*.lin")), extension=".lin")
        
        view_button = ttk.Button(button_frame, text="Edit Changes File", 
                                 command=lambda: self.callback_view_file(self.changes_file.get())).pack(side="left")
        read_button = ttk.Button(button_frame, text="Patch Sequences", style="DS.TButton",
                                 command=self.replace_sequence).pack(side="left")

        self.log_frame = ttk.LabelFrame(self.frame, text="Log")
        self.log_frame.pack(side="top")
        self.log = TextLog(self.log_frame)
        
    def callback_view_file(self, file_path):
        try:
            os.startfile(file_path)
        except FileNotFoundError as e:
            if not messagebox.askokcancel("Create File", "Create a blank file at %s?" % e):
                return 
            else:
                with open(file_path, "w", newline="") as file:
                    s = ("# This file contains the sequences to replace in the "
                         "LIN files\n#\n# Sequences can be changed using the "
                         "notation:\n#\n#       'old_node1,old_node2,old_noden':'"
                         "new_node_1,new_node_2,new_noden'\n#       1000,1005:1000,"
                         "1001,1002,1003,1004,1005\n#       If the nodes are "
                         "not stopped at, precede them with - \n#       "
                         "e.g. 1000,-1005:1000,-1001,-1002,-1003,-1004,-1005\n"
                         "# If a line is started with a #, it will be ignored\n"
                         "#\n"
                         "# Start a sequence with 'A' to include all stop/pass variations\n"
                         "# e.g. A1000,1001,1000:1000 will replace all the following"
                         " variations: 1000,1001,1000  1000,-1001,1000  1000,-1001,-1000 "
                         " -1000,1001,1000  1000,1001,-1000  etc. with just 1000"
                         "\n# This is used to remove dead ends"
                         "\n###############################################"
                         "######################\n\n#88377,74908:88377,"
                         "1232121,74908\n#88377,-74908:88377,-1232121,-74908")
                    for x in s.split("\n"):
                        file.write(x)
                        file.write("\r\n")
                self.callback_view_file(file_path)
                

    def replace_sequence(self):
        # Read the patching file 
        with open(self.changes_file.get(), "r") as file:
            data = file.readlines()
            seq_dict = {}
            for row in data:
                if  row[0] == "#" or row == "\n":
                    continue
                row = row.strip("\n").strip()
                if row[0] == "A":
                    row = row[1:]
                    old, new = row.split(":")
                    old = old.split(",")
                    new = new.split(",")
                    old_seqs = all_node_variations(old)
                    for seq in old_seqs:
                        seq_dict[tuple(seq)] = new
                else:
                    old, new = row.split(":")
                    old = old.split(",")
                    new = new.split(",")
                    seq_dict[tuple(old)] = new
        
        lines = read_lin_file(self.lin_input.get())
        
        
        with open(self.lin_output.get(), "w", newline="") as file:
            file.write(";;<<PT>><<LINE>>;;\n")
            num_replacements = 0
            
            for service in lines:
                replacement_info = []
                # Check if anything needs replacing
                line_string = ""
                node_seq = service["N"]
                new_nodes = node_seq
                for old_seq, new_seq in seq_dict.items():
                    old_seq = [x for x in old_seq]
                    for index in reversed(kmp_search(node_seq, old_seq)):
                        num_replacements += 1
                        replacement_info.append([index, len(new_seq)-len(old_seq)])
                        self.log.add_message("Replaced a sequence in %s, position %d" % (service["LINE NAME"], index))
                        print(("Replaced a sequence in %s, position %d" % (service["LINE NAME"], index)))
                        del new_nodes[index:index + len(old_seq)]
                        for j, node in enumerate(new_seq):
                            new_nodes.insert(index + j, node)
                service = single_add_rts_back_in(service, replacement_info)
                line_string += ", ".join([k + "=" + v for k, v in service.items() if k != "N" and k != "RT"])
                line_string += ", N=" + ", ".join(new_nodes)
                result = process_lin(line_string)
                file.write(result)
                file.write('\n\n')
                    
                
        self.log.add_message("Finished", color="GREEN")
        self.log.add_message("Replaced %d occurences" % num_replacements)
                    
                    
                    
                    
