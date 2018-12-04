import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from user_func_V2 import SelectBox, TextLog
from Patch_Links import get_unique_links
from CIF_Import_V6 import print_rail_lin

class PatchTab:
    def __init__(self, note_book, bus_tab, rail_tab, general, name="Patch and Print"):
        self.current_dir = os.path.dirname(__file__)
        
        self.master = ttk.Frame(note_book)
        note_book.add(self.master, text=name)
        self.style = ttk.Style()
        self.style.configure("DS.TButton", foreground="green")

        self.bus = bus_tab
        self.rail = rail_tab
        self.gen = general

        self.output = tk.StringVar()
        self.lin = tk.StringVar()
        self.modes = tk.StringVar()

        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.rail_frame, self.print_frame)
        self.log = TextLog(self.log_frame)

    def create_header_widget(self,frame):
        ttk.Label(frame, \
              text="Use this tab to patch the intermediate Voyager Nodes into the service routes\nEnsure that a valid 'Link Lookup' is provided (see README file for format info)\nFirst 'Patch' the file then 'Print LIN'",\
              style="Head.TLabel").grid(row=0, column=0)


    def create_file_widgets(self,frame, frame2):
        ttk.Label(frame, text="Filtered Services\n(Output from the 'Import Rail' tab)").grid(column=0,row=0,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.rail.files["MCA_f"]).grid(column=0,row=1)
        ttk.Button(frame, text="Browse", command=lambda : self.rail.files["MCA_f"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=1)

        '''ttk.Label(frame, text="Patched Services file name\n(Will be created if it does not exist)").grid(column=0,row=2,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.rail.files["MCA_p"]).grid(column=0,row=3)
        ttk.Button(frame, text="Browse", command=lambda : self.rail.files["MCA_p"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=3)'''

        ttk.Label(frame, text="Intermediate Link Lookup\n(Provide a file containing intermediate Voyager links in the network)").grid(column=0,row=4,columnspan=2,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.rail.files["links"]).grid(column=0,row=5)
        ttk.Button(frame, text="Browse", command=lambda : self.rail.files["links"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=5)

        self.rail_patch = ttk.Button(
            frame, text="Patch", style="DS.TButton", command=self.start_patching)
        self.rail_patch.grid(column=3, row=5)

        ttk.Label(frame2, text="Select LIN Output File Name\n(Will be created if it does not exist)").grid(column=0,row=0,sticky="w")
        ttk.Entry(frame2, width=50, textvariable=self.rail.files["lin"]).grid(column=0,row=1)
        self.rail_print = ttk.Button(
            frame2, text="Print LIN", style="DS.TButton", command=self.print_lin)
        self.rail_print.grid(column=1, row=1)

    def start_patching(self):
        get_unique_links(self.rail.files["MCA_f"].get(), self.rail.files["links"].get(), self.rail.files["MCA_p"].get(), self.log)

    def print_lin(self):
        custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
        print_rail_lin(self.rail.files["MCA_p"].get(), self.rail.files["lin"].get(), self.gen.files["ops"].get(), custom_headways, self.log)
        if self.gen.auto_open.get() == 1:
            os.startfile(self.rail.files["lin"].get())


    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, columnspan=c_span, sticky=s,padx=3,pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", [0,1],s="w")
        self.rail_frame = add_frame(self.master, "Rail Patching", [1,1],s="w")
        self.print_frame = add_frame(self.master, "Printing LIN Files", [2,1],s="w")
        self.log_frame = add_frame(self.master, "Log", [3,1],s="w")
        
