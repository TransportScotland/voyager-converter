import threading
import os
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from user_func_V2 import SelectBox, TextLog
import CIF_Import_V6 as ri

class RailTab:
    def __init__(self, note_book, general, name="Rail"):
        self.master = ttk.Frame(note_book)
        note_book.add(self.master, text=name)
        self.gen = general
        self.style = ttk.Style()
        self.style.configure("DS.TButton", forefround="green",relief="flat")

        self.files = {"MCA" : tk.StringVar(),
                      "MSN" : tk.StringVar(),
                      "MCA_a" : tk.StringVar(),
                      "stn" : tk.StringVar(),
                      "MCA_f" : tk.StringVar(),
                      "MCA_p" : tk.StringVar(),
                      "lin" : tk.StringVar(),
                      "links" : tk.StringVar(),
                      }
        
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Bank Holiday Running"]
        self.operators = set()
        self.current_dir = os.path.dirname(__file__)
        self.input_dir = os.path.join(self.current_dir, "Inputs")
        
        self.head_defs = tk.StringVar()
        self.head_name = tk.StringVar()
        self.selected_days = [tk.IntVar() for x in self.days]
        self.line_start = tk.IntVar()
        self.date_from = [tk.StringVar() for x in range(0,3)]
        self.date_to = [tk.StringVar() for x in range(0,3)]

        self.set_defaults()
        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.file_select_frame)
        self.create_operator_widgets(self.operator_frame)
        self.create_filter_widgets(self.filter_frame)
        self.progress = ttk.Progressbar(self.progress_frame,orient=tk.HORIZONTAL,length=500,mode="determinate")
        self.progress.grid(row=1,column=1)
        self.log = TextLog(self.log_frame)
        

    def read_file(self, key):
        if key == "read":
            ri.import_station_names(self.to_path("MSN"), self.to_path("stn"), self.log)
            
            days_filter = [x.get() for x in self.gen.selected_days]
            date_filters = [[x.get() for x in self.gen.date_from],[x.get() for x in self.gen.date_to]]
            widget_list = (self.progress, self.import_data, self.log)
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            f_args = (self.to_path("MCA"), self.to_path("stn"), self.to_path("MCA_a"), self.gen.to_path("r_nod"),\
                      self.gen.to_path("ops"), self.update_input, days_filter, date_filters, self.line_start.get(), \
                      custom_headways, widget_list)
            threading.Thread(target=ri.import_timetable_info, args=(f_args)).start()
        elif key == "ops":
            check_mode = "RAIL"
            ops = set()
            try:
                with open(self.gen.to_path("ops"), "r") as file:
                    reader = csv.reader(file)
                    headers = next(reader)
                    for line in reader:
                        if line[0].strip(" ") == check_mode:
                            ops.add(line[1])
                if len(ops) == 0:
                    self.log.add_message("No operators in file\nTry importing some data first",color="RED")
            except IOError:
                self.log.add_message("No operator file present\nTry importing some data first",color="RED")
            self.update_input(ops)
        elif key == "fil":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            ri.CIF_post_filter("rail", self.to_path("MCA_a"), self.to_path("MCA_f"), \
                               self.to_path("lin"), self.used_operators.get_contents(), \
                               self.gen.to_path("ops"), self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("MCA_f"))

    def update_input(self, op_list):
        self.unused_operators.change_contents(op_list)
        self.used_operators.change_contents([])

    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def create_header_widget(self,frame):
        ttk.Label(frame, \
                  text="Use this tab to import rail timetable data from MSN and MCA files\nEnsure the Rail Node Lookup is specified in the 'General Options' tab\nProceed through this tab from top-botton then patch the routes in the next tab",\
                  style="Head.TLabel").grid(row=0, column=0)

    def create_filter_widgets(self, frame):
        valid_update = ttk.Button(
            frame, text="Filter by Operator", style="DS.TButton", command=lambda : self.read_file("fil")).grid(column=1, row=2,sticky="e")
        ttk.Label(frame, text="Enter desired file to save filtered services to\n(Will be created if it does not exist)").grid(row=1, column=0,sticky="w")
        valid_entry = ttk.Entry(frame, width=50, textvariable=self.files["MCA_f"]).grid(column=0, row=2)

    def create_operator_widgets(self, frame):

        ttk.Label(frame, text="-> Read in the operator list then move the desired operators to the 'Keep' pane\nAll 'Remove' operators will be filtered out").grid(
            row=0,column=1,sticky="w",columnspan=3)

        self.op_read = ttk.Button(
            frame, text="Load Rail Operators", style="DS.TButton", command=lambda : self.read_file("ops"))
        self.op_read.grid(
                    column=3, row=0, sticky="e")

        ttk.Label(frame, text="Remove").grid(row=1,column=1,sticky="w")
        ttk.Label(frame, text="Keep").grid(row=1,column=3,sticky="w")
                  
        self.unused_operators = SelectBox(frame, 10, 40, 2, 1, self.operators)
        self.used_operators = SelectBox(frame, 10, 40, 2, 3)

        un_op = self.unused_operators
        u_op = self.used_operators

        add_op = ttk.Button(frame, text="Add",
                        command=lambda : un_op.swap_element(u_op)).grid(row=2, column=2)
        rem_op = ttk.Button(frame, text="Remove",
                        command=lambda : u_op.swap_element(un_op)).grid(row=3, column=2)
        add_all_op = ttk.Button(frame, text="Add all",
                        command=lambda : un_op.swap_all(u_op)).grid(row=4, column=2)
        rem_all_op = ttk.Button(frame, text="Remove all",
                        command=lambda : u_op.swap_all(un_op)).grid(row=5, column=2)
        
    def create_headway_widgets(self, frame):
        description = ttk.Label(
            frame, text="Specify Headway Periods Using a Comma Separated List\n e.g. 7-10, 10-16, 16-19 as AM, Mid, PM").grid(
                row=1, column=1,sticky=tk.W,columnspan=3)
        lab = ttk.Label(frame, text="Periods").grid(row=2,column=0)
        periods = ttk.Entry(frame, width=40, textvariable=self.head_defs).grid(row=2,column=1)
        lab2 = ttk.Label(frame, text="Names").grid(row=2,column=2)
        names = ttk.Entry(frame, width=40, textvariable=self.head_name).grid(row=2, column=3)

    def create_date_widgets(self, frame):
        d = [str(x).zfill(2) for x in range(1, 32)]
        m = [str(x).zfill(2) for x in range(1, 13)]
        y = [str(x) for x in range(1980, 2040)]
        
        from_day = ttk.Combobox(frame, textvariable=self.date_from[0], values=d, width=3).grid(row=1, column=1, sticky=(tk.E,tk.N))
        from_month = ttk.Combobox(frame, textvariable=self.date_from[1], values=m, width=3).grid(row=1, column=2, sticky=(tk.E,tk.N))
        from_year = ttk.Combobox(frame, textvariable=self.date_from[2], values=y, width=5).grid(row=1, column=3, sticky=(tk.E,tk.N))

        to_day = ttk.Combobox(frame, textvariable=self.date_to[0], values=d, width=3).grid(row=2, column=1, sticky=(tk.E,tk.S))
        to_month = ttk.Combobox(frame, textvariable=self.date_to[1], values=m, width=3).grid(row=2, column=2, sticky=(tk.E,tk.S))
        to_year = ttk.Combobox(frame, textvariable=self.date_to[2], values=y, width=5).grid(row=2, column=3, sticky=(tk.E,tk.S))

        from_label = ttk.Label(frame, text="From").grid(row=1, column=0,sticky=tk.W)
        to_label = ttk.Label(frame, text="To").grid(row=2, column=0,sticky=tk.W)

        buffer = ttk.Label(frame, text="").grid(row=3,column=0)
        line_label = ttk.Label(frame, text="Starting Line Number").grid(row=4, column=0,sticky="es")
        line_entry = ttk.Entry(frame, width=5, textvariable=self.line_start).grid(row=4, column=1,sticky="es")

    def create_day_widgets(self, frame):
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
        ttk.Label(frame, text="MSN File").grid(column=0,row=0)
        ttk.Entry(frame, width=50, textvariable=self.files["MSN"]).grid(column=1,row=0)
        ttk.Button(frame, text="Browse", command=lambda : self.files["MSN"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=2,row=0)

        ttk.Label(frame, text="MCA File").grid(column=0,row=1)
        ttk.Entry(frame, width=50, textvariable=self.files["MCA"]).grid(column=1,row=1)
        ttk.Button(frame, text="Browse", command=lambda : self.files["MCA"].set(
            os.path.relpath(filedialog.askopenfilename(), self.current_dir))).grid(column=2,row=1)

        ttk.Label(frame, text="All Services").grid(column=0,row=2)
        ttk.Entry(frame, width=50, textvariable=self.files["MCA_a"]).grid(column=1,row=2)

        #On pressing this, send MSN file to import satation names etc
        self.import_data = ttk.Button(
            frame, text="Import Data", style="DS.TButton",command=lambda : self.read_file("read"))
        self.import_data.grid(
                column=2, row=2)
        

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, columnspan=c_span, sticky=s,padx=3,pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", [1,1],s="w")
        self.file_select_frame = add_frame(self.master, "Select Input and Output files", [2,1], c_span=2,s="w")
        self.operator_frame = add_frame(self.master, "Select Operators", [3,1], c_span=2,s="w")
        self.filter_frame = add_frame(self.master, "Save Valid Schedules to CSV File", [5,1], c_span=2,s="w")
        self.log_frame = add_frame(self.master, "Log", [6,1], c_span=2,s="w")
        self.progress_frame = add_frame(self.master, "Progress", [7,1], c_span=2,s="w")

    def set_defaults(self):
        f = self.files
        f["MCA"].set("Test1.mca")
        f["MSN"].set("Test1.msn")
        f["MCA_a"].set("mca_out_head.csv")
        f["MCA_f"].set("mca_out_head.csv")
        f["MCA_p"].set("mca_out_head_patched.csv")
        f["stn"].set("stat_name.csv")
        f["lin"].set("Output Files\\rail_lin.lin")
        f["links"].set("Node Lookup Files\\CSTM_Network_Filler_V1.1.txt")
        self.files = f
        self.head_defs.set("7, 10, 16, 19")
        self.head_name.set("AM, Mid, PM")
        self.date_from[0].set("01")
        self.date_from[1].set("01")
        self.date_from[2].set("2014")
        self.date_to[0].set("01")
        self.date_to[1].set("01")
        self.date_to[2].set("2022")
        
        
