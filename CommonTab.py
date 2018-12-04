import threading
import os
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from user_func_V2 import SelectBox, TextLog

class CommonTab:
    def __init__(self, note_book, name="COMMON"):
        self.master = ttk.Frame(note_book)
        note_book.add(self.master, text=name)

        self.files = {"ops" : tk.StringVar(),
                      "b_nod" : tk.StringVar(),
                      "r_nod" : tk.StringVar(),
                      }
        
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Bank Holiday Running"]
        self.operators = set()
        self.current_dir = os.path.dirname(__file__)
        self.input_dir = os.path.join(self.current_dir, "Inputs")
        
        self.head_defs = tk.StringVar()
        self.head_name = tk.StringVar()
        self.selected_days = [tk.IntVar() for x in self.days]
        self.date_from = [tk.StringVar() for x in range(0,3)]
        self.date_to = [tk.StringVar() for x in range(0,3)]
        self.auto_open = tk.IntVar()

        self.set_defaults()
        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.file_select_frame)
        self.create_day_widgets(self.day_def_frame)
        self.create_date_widgets(self.date_def_frame)
        self.create_headway_widgets(self.headway_frame)
        self.create_GUI_widgets(self.GUI_frame)

    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def create_header_widget(self,frame):
        ttk.Label(frame, \
                  text="Use this tab to specify the initial parameters\nEnsure all files have been selected/have a name entered\nMost options can be left as the defaults",\
                  style="Head.TLabel").grid(row=0, column=0)

    def create_GUI_widgets(self, frame):
        ttk.Label(frame, text="Automatically open output file after processing?\n(Uncheck if not using Windows)").grid(
            row=0,column=0,sticky="w")
        ttk.Checkbutton(frame, text="Auto-open", variable=self.auto_open, onvalue=1, offvalue=0).grid(
            row=0,column=1,sticky="e")
        
    def create_headway_widgets(self, frame):
        description = ttk.Label(
            frame, text="-> Specify Headway Periods Using a Comma Separated List\n e.g. 7-10, 10-16, 16-19 as AM, Mid, PM").grid(
                row=1, column=0,sticky=tk.W,columnspan=3)
        lab = ttk.Label(frame, text="Periods").grid(row=2,column=0)
        periods = ttk.Entry(frame, width=40, textvariable=self.head_defs).grid(row=2,column=1)
        lab2 = ttk.Label(frame, text="Names").grid(row=3,column=0)
        names = ttk.Entry(frame, width=40, textvariable=self.head_name).grid(row=3, column=1)

    def create_date_widgets(self, frame):
        d = [str(x).zfill(2) for x in range(1, 32)]
        m = [str(x).zfill(2) for x in range(1, 13)]
        y = [str(x) for x in range(1980, 2040)]

        l = ttk.Label(frame, text="-> Select the date range of interest").grid(row=0,column=0,sticky="w")
        
        from_day = ttk.Combobox(frame, textvariable=self.date_from[0], values=d, width=3).grid(row=1, column=1, sticky=(tk.E,tk.N))
        from_month = ttk.Combobox(frame, textvariable=self.date_from[1], values=m, width=3).grid(row=1, column=2, sticky=(tk.E,tk.N))
        from_year = ttk.Combobox(frame, textvariable=self.date_from[2], values=y, width=5).grid(row=1, column=3, sticky=(tk.E,tk.N))

        to_day = ttk.Combobox(frame, textvariable=self.date_to[0], values=d, width=3).grid(row=2, column=1, sticky=(tk.E,tk.S))
        to_month = ttk.Combobox(frame, textvariable=self.date_to[1], values=m, width=3).grid(row=2, column=2, sticky=(tk.E,tk.S))
        to_year = ttk.Combobox(frame, textvariable=self.date_to[2], values=y, width=5).grid(row=2, column=3, sticky=(tk.E,tk.S))

        from_label = ttk.Label(frame, text="From").grid(row=1, column=0,sticky=tk.W)
        to_label = ttk.Label(frame, text="To").grid(row=2, column=0,sticky=tk.W)


    def create_day_widgets(self, frame):
        ttk.Label(frame, text="-> Select the day of interest\n(Selecting Multiple days may cause errors in headway calculations)").grid(
            column=1,row=0,sticky="w", columnspan=2)
        day_boxes = []
        var = self.selected_days
        clm = 1
        rw = 1
        for i in range(0, len(self.days)):
            day_boxes.append(ttk.Checkbutton(frame, text=self.days[i], variable=var[i], onvalue=1, offvalue=0)
                             .grid(row=rw, column=clm, sticky=tk.W))
            rw += 1
            if rw > len(self.days) / 2:
                clm += 1
                rw = 1 
        
    def create_file_widgets(self, frame):

        ttk.Label(frame, text="Operator to Mode Lookup\n(Will be created if it does not exist)").grid(column=0,row=5,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["ops"]).grid(column=0,row=6)
        ttk.Button(frame, text="Browse", command=lambda : self.files["ops"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=6)

        ttk.Label(frame, text="Bus Node Lookup\n(Provide a csv file of ATCO -> Cube Node)").grid(column=0,row=1,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["b_nod"]).grid(column=0,row=2)
        ttk.Button(frame, text="Browse", command=lambda : self.files["b_nod"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=2)

        ttk.Label(frame, text="Rail Node Lookup\n(Provide a csv file of TIPLOC -> Cube Node)").grid(column=0,row=3,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["r_nod"]).grid(column=0,row=4)
        ttk.Button(frame, text="Browse", command=lambda : self.files["r_nod"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=1,row=4)
        

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, columnspan=c_span, sticky=s, padx=3, pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", [0,1],s="w")
        self.day_def_frame = add_frame(self.master, "Day Definitions", [1,1],s="w")
        self.date_def_frame = add_frame(self.master, "Date and Line Definitions", [2,1],s="w")
        self.file_select_frame = add_frame(self.master, "Select Common Files", [3,1],s="w")
        self.headway_frame = add_frame(self.master, "Headway Definition", [4,1],s="w")
        self.GUI_frame = add_frame(self.master, "GUI Options",[5,1],s="w")

    def set_defaults(self):
        f = self.files
        f["ops"].set("Node Lookup Files\\Operator_Codes.csv")
        f["b_nod"].set("Node Lookup Files\\Bus_ATCO_To_Voyager_Node_V1.0.csv")
        f["r_nod"].set("Node Lookup Files\\CSTM_Friendly_Names_V1.3.csv")
        self.files = f
        self.head_defs.set("7, 10, 16, 19")
        self.head_name.set("AM, Mid, PM")
        self.date_from[0].set("01")
        self.date_from[1].set("01")
        self.date_from[2].set("2014")
        self.date_to[0].set("01")
        self.date_to[1].set("01")
        self.date_to[2].set("2022")
        self.auto_open.set(1)
        for i in range(0,len(self.selected_days)-1):
            self.selected_days[i].set(1)
        
        
