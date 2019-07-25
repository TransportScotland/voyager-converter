import threading
import os
import csv
import tkinter as tk
from tkinter import ttk
import patch_routes as patch
import traceback
import data_cif as ri
from WidgetTemplates import CreateToolTip, LabelledEntry, TextLog, SelectBox, ThreadWithReturn

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
                      "stock" : tk.StringVar(),
                      "t_name" : tk.StringVar()
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

        self.node_lookup = tk.StringVar()
#        self.node_lookup.set(os.path.join("Node Lookup Files", "rail_nodes.csv"))
        self.link_lookup = tk.StringVar()
#        self.link_lookup.set(os.path.join("Node Lookup Files", "rail_links.csv"))
        self.set_defaults()
        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.file_select_frame)
        self.create_patching_widgets(self.patch_frame)
        self.create_operator_widgets(self.operator_frame)
        self.create_print_lin_widgets(self.lin_frame)
        self.progress = ttk.Progressbar(self.progress_frame,orient=tk.HORIZONTAL,length=500,mode="determinate")
        self.progress.grid(row=1,column=1)
        self.log = TextLog(self.log_frame)
        
    '''def create_print_lin_widgets(self,frame):
        ttk.Button(frame, text="4. Print LIN File",style="DS.TButton", command=lambda : self.read_file("lin")).grid(column=0, row=3, padx=5, pady=5, ipady=5, ipadx=5,sticky="we")
        ttk.Label(frame, text="Enter desired name to save LIN file to\n(Will be created if it does not exist)").grid(row=1, column=0,sticky="w")
        valid_entry = ttk.Entry(frame, width=90, textvariable=self.files["lin"])
        valid_entry.grid(column=0, row=2, padx=5, pady=5)'''
        
    def callback_patching_window(self):
        self.create_patching_window()
        
    def create_patching_window(self):
    
        def callback_patch_routes():
            try:
                patch_log.add_message("Patching routes...")
                args = (node_file.get(), link_file.get(), self.to_path("MCA_f"), 
                        self.to_path("MCA_p"), path_out,
                        self.gen.files["user_p"].get(), err_out)
                kwargs = {"progress_inc":progress.step, 
                          "use_distance":use_distance.get()==1,
                          "max_distance":int(max_distance.get()),
                          "type":"rail"}
                t = ThreadWithReturn(target=patch.patch_selected, args=args, kwargs=kwargs)
                t.start()
                num_found, num_errors = t.join()
                patch_log.add_message("Finished Patching:\nFound %d Paths (Saved in %s)" % (num_found, path_out), color="GREEN")
                patch_log.add_message("Encountered %d Bad Paths (Saved in %s)" % (num_errors, err_out), color="RED")
            except Exception as e:
                patch_log.add_message("Exception: %s" % e, color="RED")
                patch_log.add_message("Traceback: %s" % "".join(traceback.format_tb(e.__traceback__)), color="RED")
                
        def callback_view_file(file_num):
            file_path = file_names[file_num]
            try:
                os.startfile(file_path)
            except FileNotFoundError:
                patch_log.add_message("File does not exist: Patch the routes first", color="RED")
            
        patch_window = tk.Toplevel()
        patch_window.title("Patch Rail Routes")
        patch_window.attributes("-topmost", "true")
        patch_window.wm_attributes("-topmost","true")
        
        node_file = tk.StringVar()
        link_file = tk.StringVar()
        node_file.set(self.node_lookup.get())
        link_file.set(self.link_lookup.get())
        path_out = os.path.join(self.current_dir, 
                                os.path.join(self.gen.inter_dir, "rail_linked_paths.csv"))
        err_out = os.path.join(self.current_dir, 
                               os.path.join(self.gen.inter_dir, "rail_unlinked_paths.csv"))
        use_distance = tk.IntVar(value=1)
        max_distance = tk.StringVar(value="500")
        max_distance.set("500")
        file_names = {1:path_out, 2:err_out, 3:self.gen.files["user_p"].get(), 
                      4:self.to_path("MCA_p")}
        unpatched_file_var = tk.StringVar()
        unpatched_file_var.set(self.to_path("MCA_f"))
        
        top_frame = ttk.Frame(patch_window)
        file_frame = ttk.Frame(patch_window)
        button_frame = ttk.Frame(patch_window)
        log_frame = ttk.Frame(patch_window)
        top_frame.pack(side="top")
        file_frame.pack(side="top")
        button_frame.pack(side="top")
        log_frame.pack(side="top")
        
        ttk.Label(top_frame, text=("Usage: Enter paths to network files "
                                   "(Nodes and Links) to fill in gaps "
                                   "between bus stops")).pack(side="top")
        
        node = LabelledEntry(file_frame, "Node File", node_file, w=50, 
                             tool_tip_text=("CSV File that contains all rail nodes "
                                            "in the network\nOne column called "
                                            "'Node' containing node numbers"))
        node.add_browse(self.current_dir)
        link = LabelledEntry(file_frame, "Link File", link_file, w=50, 
                             tool_tip_text=("CSV File that contains all rail links "
                                            "in the network\nTwo columns "
                                            "called 'NodeA' and 'NodeB' "
                                            "containing node numbers"))
        link.add_browse(self.current_dir)
        over = LabelledEntry(file_frame, "Patch Override File", 
                             self.gen.files["user_p"], w=50, 
                             tool_tip_text="User overrides for patching routes")
        over.add_browse(self.current_dir)
        out = LabelledEntry(file_frame, "Output File", 
                            self.files["MCA_p"], w=50, 
                            tool_tip_text=("CSV Output file for the patched "
                                           "services\nSame format as other "
                                           "intermediate files"))
        out.add_browse(self.current_dir, save=True)
        
        options_frame = ttk.Frame(file_frame)
        options_frame.pack()
        l = ttk.Label(options_frame, text="Check Size")
        l.pack(side="left")
        CreateToolTip(l, text=("Number of nodes to check when 'Use Distance' "
                               "is checked. Larger numbers "
                               "will increase patching time"))
        e = ttk.Entry(options_frame, text=max_distance.get(), 
                  textvariable=max_distance)
        e.pack(side="left", padx=5, pady=2)
        distance = ttk.Checkbutton(options_frame, text="Use Distance", variable=use_distance)
        distance.pack(side="left")
        CreateToolTip(distance, text=("If ticked, the distance of the links will"
                                      " be used and the shortest distance will "
                                      "be found. If unticked, the shortest route "
                                      "will be found according to the number "
                                      "of nodes passed"))
        
        patch_button = ttk.Button(button_frame, text="Patch Routes", 
                                  command=callback_patch_routes, style="DS.TButton")
        patch_button.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(patch_button, text="Automated patching of routes")
        view_paths = ttk.Button(button_frame, text="Patches", 
                                command=lambda: callback_view_file(1))
        view_paths.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(view_paths, text="View the patches that the process created")
        view_errs = ttk.Button(button_frame, text="Errors", 
                               command=lambda: callback_view_file(2))
        view_errs.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(view_errs, text="View the routes that could not be patched")
        view_overrides = ttk.Button(button_frame, text="Overrides", 
                                    command=lambda: callback_view_file(3))
        view_overrides.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(view_overrides, text=("Open the user overrides file to "
                                            "manually enter patches"))
        view_patch = ttk.Button(button_frame, text="Output", 
                                command=lambda: callback_view_file(4))
        view_patch.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(view_patch, text="View the file with all patched services")
        
        patch_log = TextLog(log_frame)
        progress = ttk.Progressbar(log_frame,orient=tk.HORIZONTAL,length=200,mode="determinate")
        progress.pack(side="top", padx=5, pady=5)

    def read_file(self, key):
        if key == "read":
            ri.import_station_names(self.to_path("MSN"), self.to_path("stn"), self.log)
            
            days_filter = [x.get() for x in self.gen.selected_days]
            date_filters = [[x.get() for x in self.gen.date_from],[x.get() for x in self.gen.date_to]]
            widget_list = (self.progress, self.import_data, self.log)
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            
            f_args = (self.to_path("MCA"), self.to_path("stn"), 
                      self.gen.to_path("r_nod"), self.gen.to_path("ops"), 
                      self.to_path("MCA_a"), days_filter, date_filters, 
                      self.line_start.get(), custom_headways, widget_list)
            threading.Thread(target=ri.import_cif_callback, args=(f_args)).start()
            
        elif key == "ops":
            check_mode = "RAIL"
            ops = set()
            try:
                with open(self.gen.to_path("ops"), "r") as file:
                    reader = csv.reader(file)
                    _ = next(reader)
                    for line in reader:
                        if line[0].strip(" ") == check_mode:
                            ops.add(line[1])
                if len(ops) == 0:
                    self.log.add_message(("No operators in file\n"
                                          "Try importing some data first"),color="RED")
            except IOError:
                self.log.add_message(("No operator file present\nTry "
                                      "importing some data first"),color="RED")
            self.update_input(ops)
        elif key == "fil":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            ri.CIF_post_filter("rail", self.to_path("MCA_a"), self.to_path("MCA_f"), \
                               self.to_path("lin"), self.used_operators.get_contents(), \
                               self.gen.to_path("ops"), self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("MCA_f"))
                
        elif key == "lin":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            ri.print_lin_file(self.to_path("MCA_p"),self.to_path("lin"),
                              self.gen.to_path("ops"),custom_headways, self.log,
                              rolling_stock_file=self.to_path("stock"),
                              tiploc_lookup_file=self.to_path("t_name"))
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("lin"))

    def update_input(self, op_list):
        self.unused_operators.change_contents(op_list)
        self.used_operators.change_contents([])

    def create_patching_widgets(self, frame):
        patch_but = ttk.Button(frame, text="3. Open Patching Interface", 
                               command=self.callback_patching_window, style="DS.TButton")
        patch_but.pack(side="top", anchor="w", padx=5, pady=5, 
                       ipadx=5, ipady=5, fill="both")
        
    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def create_header_widget(self,frame):
        ttk.Label(frame, text=("Use this tab to import rail timetable data "
                               "from MSN and MCA files\nEnsure the Rail Node "
                               "Lookup is specified in the 'General Options' "
                               "tab\nProceed through this tab from top-botton "
                               "then patch the routes in the next tab"), 
            style="Head.TLabel").grid(row=0, column=0)

    def create_filter_widgets(self, frame):
        valid_update = ttk.Button(
            frame, text="Filter by Operator", style="DS.TButton", 
            command=lambda : self.read_file("fil"))
        valid_update.grid(column=1, row=2,sticky="e")
        l = ttk.Label(frame, text=("Enter desired file to save filtered services "
                               "to\n(Will be created if it does not exist)"
                               )).grid(row=1, column=0,sticky="w")
        l.grid(column=0, row=2)

    def create_operator_widgets(self, frame):

        ttk.Label(frame, text=("-> Read in the operator list then move the "
                               "desired operators to the 'Keep' pane\nAll "
                               "'Remove' operators will be filtered out")).grid(
            row=0,column=1,sticky="w",columnspan=3)

        self.op_read = ttk.Button(
            frame, text="Read Operator File", command=lambda : self.read_file("ops"))
        self.op_read.grid(
                    column=3, row=0, sticky="e")

        ttk.Label(frame, text="Remove").grid(row=1,column=1,sticky="w")
        ttk.Label(frame, text="Keep").grid(row=1,column=3,sticky="w")
                  
        self.unused_operators = SelectBox(frame, 10, 40, 2, 1, self.operators)
        self.used_operators = SelectBox(frame, 10, 40, 2, 3)

        un_op = self.unused_operators
        u_op = self.used_operators

        add_op = ttk.Button(frame, text="Add",
                        command=lambda : un_op.swap_element(u_op))
        add_op.grid(row=2, column=2)
        rem_op = ttk.Button(frame, text="Remove",
                        command=lambda : u_op.swap_element(un_op))
        rem_op.grid(row=3, column=2)
        add_all_op = ttk.Button(frame, text="Add all",
                        command=lambda : un_op.swap_all(u_op))
        add_all_op.grid(row=4, column=2)
        rem_all_op = ttk.Button(frame, text="Remove all",
                        command=lambda : u_op.swap_all(un_op))
        rem_all_op.grid(row=5, column=2)
                        
        valid_update = ttk.Button(
            frame, text="2. Filter Operators", style="DS.TButton",
            command=lambda : self.read_file("fil"))
        valid_update.grid(column=1, row=6,columnspan=3, padx=5, pady=5, 
                          ipadx=5, ipady=5, sticky="we")
        
    def create_headway_widgets(self, frame):
        description = ttk.Label(
            frame, text=("Specify Headway Periods Using a Comma Separated "
                         "List\n e.g. 7-10, 10-16, 16-19 as AM, Mid, PM"))
        description.grid(row=1, column=1,sticky=tk.W,columnspan=3)
        lab = ttk.Label(frame, text="Periods")
        lab.grid(row=2,column=0)
        periods = ttk.Entry(frame, width=40, textvariable=self.head_defs)
        periods.grid(row=2,column=1)
        lab2 = ttk.Label(frame, text="Names")
        lab2.grid(row=2,column=2)
        names = ttk.Entry(frame, width=40, textvariable=self.head_name)
        names.grid(row=2, column=3)

                
    def create_print_lin_widgets(self,frame):
        valid_entry = LabelledEntry(frame, "Line File Save Path", 
                                    self.files["lin"], w=50,
                                    tool_tip_text=("Path where the final "
                                                   "Lin file will be saved"),
                                    px=0,py=0,lx=0,ly=0)
        valid_entry.add_browse(self.current_dir,save=True, 
                               types=(("LIN", "*.lin")), extension=".lin")
        ttk.Button(frame, text="4. Print LIN File",style="DS.TButton", 
                   command=lambda : self.read_file("lin")).pack(side="top", 
                                                  padx=5, pady=5, ipadx=5, 
                                                  ipady=5,expand=True, 
                                                  fill="both")
        
    def create_file_widgets(self, frame):
        a = LabelledEntry(frame, "MSN File", self.files["MSN"], w=50,
                          tool_tip_text="MSN Station Information. CIF format",
                          px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir)
            
        a = LabelledEntry(frame, "MCA File", self.files["MCA"], w=50,
                          tool_tip_text="MCA Timetable Information. CIF format",
                          px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir)
        
        a = LabelledEntry(frame, "Rolling Stock", self.files["stock"], w=50,
                          tool_tip_text=("Rolling Stock CSV lookup file. Origin"
                                         " and destination TIPLOC, AM/IP/PM, maps"
                                         " to a seating capacity and cruh capacity"
                                         ". Optional"),
                          px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir)
        
        a = LabelledEntry(frame, "TIPLOC Lookup", self.files["t_name"], w=50,
                          tool_tip_text=("Station name (NAME) and the related"
                                         " TIPLOC (TIPLOC) for each station."
                                         " Usually required if using rolling "
                                         "stock data"),
                          px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir)

        #On pressing this, send MSN file to import satation names etc
        self.import_data = ttk.Button(
                            frame, text="1. Import Data", style="DS.TButton",
                            command=lambda : self.read_file("read"))
        self.import_data.pack(side="top", padx=5, pady=5, ipadx=5, ipady=5,
                              expand=True, fill="both")
        

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, 
                           columnspan=c_span, sticky=s,padx=3,pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", 
                                      [1,1])
        self.file_select_frame = add_frame(self.master, "Select Input and Output files", 
                                           [2,1], c_span=2,s="we")
        self.operator_frame = add_frame(self.master, "Select Operators", 
                                        [3,1], c_span=2,s="we")
        self.patch_frame = add_frame(self.master, "Patch Routes", 
                                     [5,1], c_span=2,s="we")
        self.log_frame = add_frame(self.master, "Log", 
                                   [7,1], c_span=2)
        self.lin_frame = add_frame(self.master, "Print LIN Files", 
                                   [6,1], c_span=2, s="we")
        self.progress_frame = add_frame(self.master, "Progress", 
                                        [8,1], c_span=2)

    def set_defaults(self):
        f = self.files
        f["MCA"].set("..\Data\Rail\Rail Data\Test1.mca")
        f["MSN"].set("..\Data\Rail\Rail Data\Test1.msn")
        f["MCA_a"].set(os.path.join(self.gen.inter_dir, "mca_out_head.csv"))
        f["MCA_f"].set(os.path.join(self.gen.inter_dir, "mca_out_head.csv"))
        f["MCA_p"].set(os.path.join(self.gen.inter_dir, "mca_out_head_patched.csv"))
        f["stn"].set(os.path.join(self.gen.inter_dir, "stat_name.csv"))
        f["lin"].set("Output Files\\rail_lin.lin")
        f["links"].set("Node Lookup Files\\CSTM_Network_Filler_V1.1.txt")
        f["t_name"].set(os.path.join("Node Lookup Files", 
                                 "rolling_stock_stations.csv"))
        self.files = f
        self.head_defs.set("7, 10, 16, 19")
        self.head_name.set("AM, Mid, PM")
        self.date_from[0].set("01")
        self.date_from[1].set("01")
        self.date_from[2].set("2014")
        self.date_to[0].set("01")
        self.date_to[1].set("01")
        self.date_to[2].set("2022")
        
        
