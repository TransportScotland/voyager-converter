import threading
import os
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from user_func_V2 import SelectBox, TextLog
import TransX_Bus as bi

class BusTab:
    def __init__(self, note_book, general, name="Bus"):
        self.master = ttk.Frame(note_book)
        note_book.add(self.master, text=name)
        self.gen = general
        self.style = ttk.Style()
        self.style.configure('DS.TButton', foreground="green",relief="flat")
        self.header_style = ttk.Style()
        self.header_style.configure("Head.TLabel", font=("Helvetica",10), foreground="blue")

        self.files = {"XML" : tk.StringVar(),
                      "XML_a" : tk.StringVar(),
                      "XML_f" : tk.StringVar(),
                      "sta" : tk.StringVar(),
                      "XML_p" : tk.StringVar(),
                      #"nod" : tk.StringVar(),
                      "lin" : tk.StringVar(),
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
        #self.create_day_widgets(self.day_def_frame)
        #self.create_date_widgets(self.date_def_frame)
        #self.create_headway_widgets(self.headway_frame)
        self.create_operator_widgets(self.operator_frame)
        self.create_filter_widgets(self.filter_frame)
        self.create_print_lin_widgets(self.lin_frame)
        self.progress = ttk.Progressbar(self.progress_frame,orient=tk.HORIZONTAL,length=500,mode="determinate")
        self.progress.grid(row=1,column=1)
        self.log = TextLog(self.log_frame)
        

    def read_file(self, key):
        if key == "XML":
            days_filter = [x.get() for x in self.gen.selected_days]
            date_filters = [[x.get() for x in self.gen.date_from],[x.get() for x in self.gen.date_to]]
            widget_list = (self.log, self.XML_read, self.progress)
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            f_args = (self.to_path("XML"),self.to_path("sta"), self.gen.to_path("b_nod"), self.gen.to_path("ops"), self.to_path("XML_a"),\
                      self.update_input, days_filter, date_filters,\
                      custom_headways, widget_list)
            threading.Thread(target=bi.import_XML_data, args=f_args).start()
        elif key == "ops":
            check_mode = "BUS"
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
            bi.XML_post_filter("bus", self.used_operators.get_contents(), self.to_path("XML_a"), self.to_path("XML_f"),\
                               self.to_path("lin"), self.gen.to_path("ops"), custom_headways, self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("XML_f"))
        elif key == "lin":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            bi.print_lin_file(self.to_path("XML_f"),self.to_path("lin"),self.gen.to_path("ops"),custom_headways, self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("lin"))

    def update_input(self, op_list):
        self.unused_operators.change_contents(op_list)
        self.used_operators.change_contents([])

    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def create_header_widget(self,frame):
        ttk.Label(frame, \
                  text="Use this tab to import bus timetable data from TransXChange XML files\nEnsure the Bus Node Lookup is specified in the 'General Options' tab\nProceed through this tab from top-botton",\
                  style="Head.TLabel").grid(row=0, column=0)

    def create_print_lin_widgets(self,frame):
        ttk.Button(frame, text="Print LIN File",style="DS.TButton", command=lambda : self.read_file("lin")).grid(column=1, row=2,sticky="e")
        ttk.Label(frame, text="Enter desired name to save LIN file to\n(Will be created if it does not exist)").grid(row=1, column=0,sticky="w")
        valid_entry = ttk.Entry(frame, width=50, textvariable=self.files["lin"]).grid(column=0, row=2)

    def create_filter_widgets(self, frame):
        valid_update = ttk.Button(
            frame, text="Filter by Operator", style="DS.TButton",command=lambda : self.read_file("fil")).grid(column=1, row=2,sticky="e")
        ttk.Label(frame, text="Enter desired name to save filtered services to\n(Will be created if it does not exist)").grid(row=1, column=0,sticky="w")
        valid_entry = ttk.Entry(frame, width=50, textvariable=self.files["XML_f"]).grid(column=0, row=2)

    def create_operator_widgets(self, frame):

        ttk.Label(frame, text="-> Read in the operator file then move the desired operators to the 'Keep' pane\nAll 'Remove' operators will be filtered out").grid(
            row=0,column=1,sticky="w",columnspan=3)

        self.op_read = ttk.Button(
            frame, text="Load Bus Operators", style="DS.TButton", command=lambda : self.read_file("ops"))
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
        periods = ttk.Entry(frame, width=40, textvariable=self.gen.head_defs).grid(row=2,column=1)
        lab2 = ttk.Label(frame, text="Names").grid(row=2,column=2)
        names = ttk.Entry(frame, width=40, textvariable=self.gen.head_name).grid(row=2, column=3)

    def create_date_widgets(self, frame):
        d = [str(x).zfill(2) for x in range(1, 32)]
        m = [str(x).zfill(2) for x in range(1, 13)]
        y = [str(x) for x in range(1980, 2040)]
        
        from_day = ttk.Combobox(frame, textvariable=self.gen.date_from[0], values=d, width=3).grid(row=1, column=1, sticky=(tk.E,tk.N))
        from_month = ttk.Combobox(frame, textvariable=self.gen.date_from[1], values=m, width=3).grid(row=1, column=2, sticky=(tk.E,tk.N))
        from_year = ttk.Combobox(frame, textvariable=self.gen.date_from[2], values=y, width=5).grid(row=1, column=3, sticky=(tk.E,tk.N))

        to_day = ttk.Combobox(frame, textvariable=self.gen.date_to[0], values=d, width=3).grid(row=2, column=1, sticky=(tk.E,tk.S))
        to_month = ttk.Combobox(frame, textvariable=self.gen.date_to[1], values=m, width=3).grid(row=2, column=2, sticky=(tk.E,tk.S))
        to_year = ttk.Combobox(frame, textvariable=self.gen.date_to[2], values=y, width=5).grid(row=2, column=3, sticky=(tk.E,tk.S))

        from_label = ttk.Label(frame, text="From").grid(row=1, column=0,sticky=tk.W)
        to_label = ttk.Label(frame, text="To").grid(row=2, column=0,sticky=tk.W)

        buffer = ttk.Label(frame, text="").grid(row=3,column=0)
        line_label = ttk.Label(frame, text="Starting Line Number").grid(row=4, column=0,sticky="es")
        line_entry = ttk.Entry(frame, width=5, textvariable=self.line_start).grid(row=4, column=1,sticky="es")

    def create_day_widgets(self, frame):
        day_boxes = []
        var = self.gen.selected_days
        clm = 1
        rw = 1
        for i in range(0, len(self.days)):
            day_boxes.append(ttk.Checkbutton(frame, text=self.gen.days[i], variable=var[i], onvalue=1, offvalue=0)
                             .grid(row=rw, column=clm, sticky=tk.W))
            rw += 1
            if rw > len(self.gen.days) / 2:
                clm += 1
                rw = 1 
        
    def create_file_widgets(self, frame):
        ttk.Label(frame, text="XML Directory\n(Select the directory conatining the XML files to be processed)").grid(column=0,row=0,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["XML"]).grid(column=0,row=1)
        ttk.Button(frame, text="Browse", command=lambda : self.files["XML"].set(
            os.path.relpath(filedialog.askdirectory(), self.current_dir))).grid(column=1,row=1)

        ttk.Label(frame, text="Full Output\n(Enter the file name to save the processed services to)").grid(column=0,row=4,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["XML_a"]).grid(column=0,row=5)

        ttk.Label(frame, text="NAPTAN-Voyager Node lookup").grid(column=0,row=2,sticky="w")
        ttk.Entry(frame, width=50, textvariable=self.files["sta"]).grid(column=0,row=3)
        ttk.Button(frame, text="Browse", command=lambda : self.files["sta"].set(
            os.path.relpath(filedialog.askdirectory(), self.current_dir))).grid(column=1,row=3)

        #On pressing this, send MSN file to import satation names etc
        self.XML_read = ttk.Button(
            frame, text="Import Data",style="DS.TButton", command=lambda : self.read_file("XML"))
        self.XML_read.grid(
                column=1, row=5)
        

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, columnspan=c_span, sticky=s,padx=3,pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", [1,1],s="w")
        self.file_select_frame = add_frame(self.master, "Select Input and Output files", [2,1], c_span=2,s="w")
        self.operator_frame = add_frame(self.master, "Select Operators", [3,1], c_span=2,s="w")
        self.filter_frame = add_frame(self.master, "Save Valid Schedules to CSV File", [5,1], c_span=2,s="w")
        self.lin_frame = add_frame(self.master, "Print valid schedules to LIN File", [6,1], c_span=2, s="w")
        self.log_frame = add_frame(self.master, "Log", [7,1], c_span=2,s="w")
        self.progress_frame = add_frame(self.master, "Progress", [8,1], c_span=2,s="w")

    def set_defaults(self):
        f = self.files
        f["XML"].set("")
        f["XML_a"].set("calc_head.csv")
        f["XML_f"].set("calc_head_filtered.csv")
        f["XML_p"].set("")
        f["lin"].set("Output Files\\bus_lin.lin")
        f["sta"].set("Node Lookup Files\\ATCO_To_NAPTAN_Codes_V1.0.csv")
        self.files = f
        self.head_defs.set("7, 10, 16, 19")
        self.head_name.set("AM, Mid, PM")
        self.date_from[0].set("01")
        self.date_from[1].set("01")
        self.date_from[2].set("2014")
        self.date_to[0].set("01")
        self.date_to[1].set("01")
        self.date_to[2].set("2022")
        
        
