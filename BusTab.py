import threading
import os
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import traceback
import data_transx as bi
import data_transx_ncsd as bi_ncsd
import patch_routes as patch
from WidgetTemplates import CreateToolTip, LabelledEntry, TextLog, ThreadWithReturn, SelectBox

class BusTab:
    def __init__(self, note_book, general, name="Bus", default_vars={}):
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
                      "XML_SUMMARY" : tk.StringVar()
                      }
        
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", 
                     "Saturday", "Sunday", "Bank Holiday Running"]
        self.operators = set()
        self.current_dir = os.path.dirname(__file__)
        self.dir_var = tk.StringVar()
        self.dir_var.set(self.current_dir)
        self.input_dir = os.path.join(self.current_dir, "Inputs")
        
        self.head_defs = tk.StringVar()
        self.head_name = tk.StringVar()
        self.selected_days = [tk.IntVar() for x in self.days]
        self.line_start = tk.IntVar()
        self.date_from = [tk.StringVar() for x in range(0,3)]
        self.date_to = [tk.StringVar() for x in range(0,3)]
        self.is_ncsd_data = tk.IntVar()

        self.node_lookup = tk.StringVar()
#        self.node_lookup.set(os.path.join("Node Lookup Files", "bus_nodes_v27.csv"))
        self.link_lookup = tk.StringVar()
#        self.link_lookup.set(os.path.join("Node Lookup Files", "bus_links_v27.csv"))
        self.set_defaults()
        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.file_select_frame)
        self.create_patching_widgets(self.patch_frame)
        self.create_operator_widgets(self.operator_frame)
        self.create_print_lin_widgets(self.lin_frame)
        self.progress = ttk.Progressbar(self.progress_frame,orient=tk.HORIZONTAL,
                                        length=500,mode="determinate")
        self.progress.grid(row=1,column=1)
        self.log = TextLog(self.log_frame)
        self.load_defaults(default_vars)
        
    def load_defaults(self, default_vars={}):
        for k, default in default_vars.items():
            self.files[k] = default
        
    def read_xml_files(self, summary=False):
        days_filter = [x.get() for x in self.gen.selected_days]
        date_filters = [[x.get() for x in self.gen.date_from],
                         [x.get() for x in self.gen.date_to]]
        widget_list = (self.log, self.XML_read, self.progress)
        custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
        summary_save_path = self.files["XML_SUMMARY"].get() if summary else ""
        f_args = (self.to_path("XML"),self.to_path("sta"), 
                  self.gen.to_path("b_nod"), self.gen.to_path("ops"), 
                  self.to_path("XML_a"),self.update_input, days_filter, 
                  date_filters,custom_headways, widget_list, self.read_file,
                  summary_save_path)
        if self.is_ncsd_data.get() == 1:
            threading.Thread(target=bi_ncsd.import_XML_data_callback, args=f_args).start()
        else:
            threading.Thread(target=bi.import_XML_data_callback, args=f_args).start()
        
    def callback_patching_window(self):
        self.create_patching_window()
        
    def create_patching_window(self):
    
        def callback_patch_routes():
            try:
                patch_log.add_message("Patching routes...")
                args = (self.node_lookup.get(), self.link_lookup.get(), 
                        unpatched_file_var.get(),self.to_path("XML_p"), 
                        path_out, self.gen.files["user_p"].get(), err_out)
                kwargs = {"progress_inc":progress.step, 
                          "use_distance":use_distance.get()==1,
                          "max_distance":int(max_distance.get())}
                t = ThreadWithReturn(target=patch.patch_selected, args=args, kwargs=kwargs)
                t.start()
                num_found, num_errors = t.join()
                patch_log.add_message(
                        "Finished Patching:\nFound %d Paths (Saved in %s)" % (
                                num_found, path_out), color="GREEN")
                patch_log.add_message(
                        "Encountered %d Bad Paths (Saved in %s)" % (
                                num_errors, err_out), color="RED")
            except Exception as e:
                patch_log.add_message("Exception: %s" % e, color="RED")
                patch_log.add_message("Traceback: %s" % "".join(
                        traceback.format_tb(e.__traceback__)), color="RED")
                
        def callback_make_overrides():
            patch.create_override_file(path_out, self.gen.files["user_p"].get())
                
        def callback_view_file(file_num):
            file_path = file_names[file_num]
            try:
                os.startfile(file_path)
            except FileNotFoundError:
                patch_log.add_message("File does not exist: Patch the routes first", color="RED")
    
        patch_window = tk.Toplevel()
        patch_window.title("Patch Bus Routes")
        patch_window.attributes("-topmost", "true")
        patch_window.wm_attributes("-topmost","true")
        
        path_out = os.path.join(self.current_dir, 
                                os.path.join(self.gen.inter_dir, "bus_linked_paths.csv"))
        err_out = os.path.join(self.current_dir, 
                               os.path.join(self.gen.inter_dir, "bus_unlinked_paths.csv"))
        use_distance = tk.IntVar(value=1)
        max_distance = tk.StringVar(value="500")
        max_distance.set("500")
        file_names = {1:path_out, 2:err_out, 3:self.gen.files["user_p"].get(), 
                      4:self.to_path("XML_p")}
        unpatched_file_var = tk.StringVar()
        unpatched_file_var.set(self.to_path("XML_f"))
        
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

        unpatched_file = LabelledEntry(file_frame, "Unpatched File",
                                       unpatched_file_var, w=50,
                                       tool_tip_text="The Unpatched intermediate file")
        unpatched_file.add_browse(self.current_dir)
        node = LabelledEntry(file_frame, "Node File", self.node_lookup, w=50, 
                             tool_tip_text=("CSV File that contains all bus nodes "
                                            "in the network\nOne column called "
                                            "'Node' containing node numbers"))
        node.add_browse(self.current_dir)
        link = LabelledEntry(file_frame, "Link File", self.link_lookup, w=50, 
                             tool_tip_text=("CSV File that contains all bus links "
                                            "in the network\nTwo columns called "
                                            "'NodeA' and 'NodeB' containing "
                                            "node numbers"))
        link.add_browse(self.current_dir)
        over = LabelledEntry(file_frame, "Patch Override File", 
                             self.gen.files["user_p"], w=50, 
                             tool_tip_text="User overrides for patching routes")
        over.add_browse(self.current_dir)
        out = LabelledEntry(file_frame, "Output File", self.files["XML_p"], w=50, 
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
                                  command=lambda:threading.Thread(
                                          target=callback_patch_routes).start(), 
                                  style="DS.TButton")
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
        CreateToolTip(view_overrides, text="Open the user overrides file to manually enter patches")
        view_patch = ttk.Button(button_frame, text="Output", 
                                command=lambda: callback_view_file(4))
        view_patch.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(view_patch, text="View the file with all patched services")
        patch_button = ttk.Button(button_frame, text="Make Overrides", 
                                  command=callback_make_overrides, style="DS.TButton")
        patch_button.pack(side="left", expand=True, fill=tk.X, ipady=5, ipadx=5)
        CreateToolTip(patch_button, text=("Override the selected Patch Override "
                                          "file with the sequences created in "
                                          "the 'Patches' file. This removes the "
                                          "need to calculate the sequences next "
                                          "time and speeds up the patching process"))
        
        patch_log = TextLog(log_frame)
        progress = ttk.Progressbar(log_frame,orient=tk.HORIZONTAL,length=200,
                                   mode="determinate")
        progress.pack(side="top", padx=5, pady=5)
        

    def read_file(self, key):
        if key == "XML":
            self.read_xml_files()
        elif key == "XML_SUMMARY":
            self.read_xml_files(summary=True)
        elif key == "ops":
            check_modes = ["BUS", "COACH"]
            ops = set()
            try:
                with open(self.gen.to_path("ops"), "r") as file:
                    reader = csv.reader(file)
                    _ = next(reader)
                    for line in reader:
                        if line[0].strip(" ") in check_modes:
                            ops.add(line[1])
                if len(ops) == 0:
                    self.log.add_message("No operators in file\nTry importing some data first",color="RED")
            except IOError:
                self.log.add_message("No operator file present\nTry importing some data first",color="RED")
            self.update_input(ops)
        elif key == "fil":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            if len(self.used_operators.get_contents()) < 1:
                self.log.add_message(("No operators selected. Move desired "
                                      "operators to the 'Keep' window"), 
                                color="RED")
                return
            bi.XML_post_filter("bus", self.used_operators.get_contents(), 
                               self.to_path("XML_a"), self.to_path("XML_f"),
                               self.to_path("lin"), self.gen.to_path("ops"), 
                               custom_headways, self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("XML_f"))
        elif key == "lin":
            custom_headways = (self.gen.head_defs.get(), self.gen.head_name.get())
            bi.print_lin_file(self.to_path("XML_p"),self.to_path("lin"),
                              self.gen.to_path("ops"),custom_headways, self.log)
            if self.gen.auto_open.get() == 1:
                os.startfile(self.to_path("lin"))

    def update_input(self, op_list):
        self.unused_operators.change_contents(op_list)
        self.used_operators.change_contents([])

    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def create_header_widget(self,frame):
        label = ttk.Label(frame, text=("Import bus timetable data from "
                               "TransXChange XML files\nEnsure the Bus Node "
                               "Lookup is specified in the 'General Options' "
                               "tab\nProceed through this tab from top-botton"), 
                style="Head.TLabel")
        label.grid(row=0, column=0)

    def create_print_lin_widgets(self,frame):
        valid_entry = LabelledEntry(frame, "Line File Save Path", 
                                    self.files["lin"], w=50,
                                    tool_tip_text=("Path where the final Lin "
                                                   "file will be saved"),
                                                   px=0,py=0,lx=0,ly=0)
        valid_entry.add_browse(self.current_dir,save=True, 
                               types=(("LIN", "*.lin")), extension=".lin")
        print_button = ttk.Button(frame, text="4. Print LIN File",style="DS.TButton", 
                   command=lambda : self.read_file("lin"))
        print_button.pack(side="top", padx=5, pady=5, ipadx=5, ipady=5,
                          expand=True, fill="both")

    def create_filter_widgets(self, frame):
        valid_update = ttk.Button(
            frame, text="Filter by Operator", style="DS.TButton",
            command=lambda : self.read_file("fil"))
        valid_update.grid(column=1, row=2,sticky=tk.E + tk.W,columnspan=3)
        valid_label = ttk.Label(frame, text=("Enter desired name to save "
                                             "filtered services to\n(Will be "
                                             "created if it does not exist)"))
        valid_label.grid(row=1, column=0,sticky="w")
        valid_entry = ttk.Entry(frame, width=50, textvariable=self.files["XML_f"])
        valid_entry.grid(column=0, row=2)
        
    def create_patching_widgets(self, frame):
        patch_but = ttk.Button(frame, text="3. Open Patching Interface", 
                               command=self.callback_patching_window, 
                               style="DS.TButton")
        patch_but.pack(side="top", anchor="w", padx=5, pady=5, ipadx=5, 
                       ipady=5, fill="both")

    def create_operator_widgets(self, frame):

        op_label = ttk.Label(frame, text=("-> Read in the operator file then "
                                          "move the desired operators to the "
                                          "'Keep' pane\nAll 'Remove' operators "
                                          "will not be used"))
        op_label.grid(row=0,column=1,sticky="w",columnspan=3)

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
        description = ttk.Label(frame, text=("Specify Headway Periods Using a "
                                             "Comma Separated List\n e.g. "
                                             "7-10, 10-16, 16-19 as AM, Mid, PM"))
        description.grid(row=1, column=1,sticky=tk.W,columnspan=3)
        lab = ttk.Label(frame, text="Periods")
        lab.grid(row=2,column=0)
        periods = ttk.Entry(frame, width=40, textvariable=self.gen.head_defs)
        periods.grid(row=2,column=1)
        lab2 = ttk.Label(frame, text="Names")
        lab2.grid(row=2,column=2)
        names = ttk.Entry(frame, width=40, textvariable=self.gen.head_name)
        names.grid(row=2, column=3)

        
    def create_file_widgets(self, frame):
        a = LabelledEntry(frame, "XML Directory", self.files["XML"], 
                          w=50,tool_tip_text=("Directory containing the "
                                              "Transxchange XML files. Ideally "
                                              "should not contain anything else"),
                                              px=0,py=0,lx=0,ly=0)
        a.add_directory(self.dir_var)

        a = LabelledEntry(frame, "Intermediate Path", self.files["XML_a"], 
                          w=50,tool_tip_text=("The intermediate file will be "
                                              "saved to this path. For "
                                              "verification purposes"),
                                              px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir, save=True, types=(("CSV", "*.csv")), 
                     extension=".csv")

        #On pressing this, send MSN file to import satation names etc
        butt_frame = ttk.Frame(frame)
        butt_frame.pack()
        ncsd_check = ttk.Checkbutton(butt_frame, text="Is NCSD", variable=self.is_ncsd_data)
        ncsd_check.pack(side="top", padx=5, pady=5, ipadx=5, ipady=5)
        CreateToolTip(ncsd_check, text=("Tick if the data being imported is NCSD\n"
                                        "This data has a different format so "
                                        "must be read in separately (Experimental)"))
        a = LabelledEntry(butt_frame, "Summary Output Path", self.files["XML_SUMMARY"], 
                          w=50,tool_tip_text=("Save path for summary file."),
                                              px=0,py=0,lx=0,ly=0)
        a.add_browse(self.current_dir, save=True, types=(("XLSX", "*.xlsx")), 
                     extension=".xlsx")
        self.XML_read = ttk.Button(
            butt_frame, text="Optional. Summarize Data",style="DS.TButton", 
            command=lambda : self.read_file("XML_SUMMARY"))
        self.XML_read.pack(side="left", padx=5, pady=5, ipadx=5, ipady=5,expand=True, fill="both")
        self.XML_read = ttk.Button(
            frame, text="1. Import Data",style="DS.TButton", command=lambda : self.read_file("XML"))
        self.XML_read.pack(side="left", padx=5, pady=5, ipadx=5, ipady=5,expand=True, fill="both")
        
    def set_dir_callback(self):
        path = filedialog.askdirectory()
        if path is not None and path != "":
            self.files["XML"].set(os.path.relpath(path, self.current_dir))

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span, columnspan=c_span, sticky=s,padx=3,pady=3)
            return new_frame
        self.header_frame = add_frame(self.master, "Explanation", [1,1])
        self.file_select_frame = add_frame(self.master, "Select Input and Output files", [2,1], c_span=2,s="we")
        self.operator_frame = add_frame(self.master, "Filter Operators", [3,1], c_span=2,s="we")
        self.patch_frame = add_frame(self.master, "Patch Routes", [5,1], c_span=2,s="we")
        self.lin_frame = add_frame(self.master, "Print LIN Files", [6,1], c_span=2, s="we")
        self.log_frame = add_frame(self.master, "Log", [7,1], c_span=2)
        self.progress_frame = add_frame(self.master, "Progress", [8,1], c_span=2)

    def set_defaults(self):
        f = self.files
        f["XML"].set("..\\Data\\Bus\\Bus Data Test")
        f["XML_a"].set(os.path.relpath(os.path.join(self.gen.inter_dir, "headways.csv"), self.current_dir))
        f["XML_f"].set(os.path.relpath(os.path.join(self.gen.inter_dir, "headways_filtered_operators.csv"), self.current_dir))
        f["XML_p"].set(os.path.relpath(os.path.join(self.gen.inter_dir, "headways_patched.csv"), self.current_dir))
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
        
        
