import os
from datetime import date
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from typing import Callable
from WidgetTemplates import CreateToolTip


class CommonTab:
    """Create a tab for general settings

    Parameters
    ----------

    """

    def __init__(self,
                 note_book: ttk.Notebook,
                 load_default_vars: Callable,
                 save_default_vars: Callable,
                 name: str = "COMMON"
                 ):
        self.master = ttk.Frame(note_book)
        note_book.add(self.master, text=name)

        self.files = {"ops": tk.StringVar(),
                      "b_nod": tk.StringVar(),
                      "r_nod": tk.StringVar(),
                      "int": tk.StringVar(),
                      "user_p": tk.StringVar(),
                      "mode": tk.StringVar()
                      }
        self.folders = {"output_folder": "Output Files",
                        "inter_folder": "Intermediate",
                        "lookup_folder": "Node Lookup Files"}

        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        # , "Bank Holiday Running"]
        self.operators = set()
        self.current_dir = os.path.dirname(__file__)
        self.output_folder = "Output Files"
        self.inter_folder = "Intermediate"
        self.lookup_folder = "Node Lookup Files"

        self.folder_keys = {self.output_folder: "{out_folder}",
                            self.inter_folder: "{inter_folder}",
                            self.lookup_folder: "{lookup_folder}"
                            }

        self.output_dir = os.path.join(self.current_dir, self.output_folder)
        self.inter_dir = os.path.join(self.current_dir, self.inter_folder)
        self.lookup_dir = os.path.join(self.current_dir, self.lookup_folder)

        for path in [self.output_dir, self.inter_dir, self.lookup_dir]:
            try:
                os.mkdir(path)
            except FileExistsError:
                pass

        self.head_defs = tk.StringVar()
        self.head_name = tk.StringVar()
        self.selected_day = tk.IntVar()
        self.selected_days = [tk.IntVar() for x in self.days]
        self.bank_hol = tk.IntVar()
        self.date_from = [tk.StringVar() for x in range(0, 3)]
        self.date_to = [tk.StringVar() for x in range(0, 3)]
        self.auto_open = tk.IntVar()

        self.set_defaults()
        self.add_frames()
        self.create_header_widget(self.header_frame)
        self.create_file_widgets(self.file_select_frame)
        self.create_day_widgets(self.day_def_frame)
        self.create_date_widgets(self.date_def_frame)
#        self.create_headway_widgets(self.headway_frame)
        self.create_GUI_widgets(
            self.GUI_frame, load_default_vars, save_default_vars)

    def to_path(self, key):
        f = self.files[key].get()
        return os.path.join(self.current_dir, f)

    def update_day_list(self):
        for i in range(0, len(self.selected_days)):
            if i == self.selected_day.get():
                self.selected_days[i].set(1)
            else:
                self.selected_days[i].set(0)

    def create_header_widget(self, frame):
        ttk.Label(frame,
                  text=("Specify the model parameters\n"
                        "Ensure all files have been selected/have a name "
                        "entered\nMost options can be left as the defaults"),
                  style="Head.TLabel").grid(row=0, column=0)

    def create_GUI_widgets(self, frame, load_func, save_func):
        ttk.Label(frame, text=("Automatically open output file after "
                               "processing?\n(Uncheck if not using Windows)"
                               )).grid(
            row=0, column=0, sticky="w")
        ttk.Checkbutton(frame, text="Auto-open", variable=self.auto_open,
                        onvalue=1, offvalue=0).grid(
            row=0, column=1, sticky="e")
        load = ttk.Button(frame, text="Load Default Variables",
                          command=lambda: load_func())
        load.grid(row=1, column=1)
        save = ttk.Button(frame, text="Save Default Variables",
                          command=lambda: save_func())
        save.grid(row=1, column=2)

    def create_date_widgets(self, frame):
        d = [str(x).zfill(2) for x in range(1, 32)]
        m = [str(x).zfill(2) for x in range(1, 13)]
        y = [str(x) for x in range(1980, 2040)]

        label = ttk.Label(frame, text="-> Select the date range of interest")
        label.grid(row=0, column=0, sticky="w")
        CreateToolTip(label,
                      text=("This is a single date to avoid clashes in "
                            "Transxchange data\nFor TransXchange the date "
                            "should generally be later and CIF, earlier"))

        from_day = ttk.Combobox(frame, textvariable=self.date_from[0],
                                values=d, width=3)
        from_day.grid(row=1, column=1, sticky=(tk.E, tk.N))
        from_month = ttk.Combobox(frame, textvariable=self.date_from[1],
                                  values=m, width=3)
        from_month.grid(row=1, column=2, sticky=(tk.E, tk.N))
        from_year = ttk.Combobox(frame, textvariable=self.date_from[2],
                                 values=y, width=5)
        from_year.grid(row=1, column=3, sticky=(tk.E, tk.N))

        to_day = ttk.Combobox(frame, textvariable=self.date_to[0], values=d,
                              width=3, state="disabled")
        to_day.grid(row=2, column=1, sticky=(tk.E, tk.S))
        to_month = ttk.Combobox(frame, textvariable=self.date_to[1], values=m,
                                width=3, state="disabled")
        to_month.grid(row=2, column=2, sticky=(tk.E, tk.S))
        to_year = ttk.Combobox(frame, textvariable=self.date_to[2], values=y,
                               width=5, state="disabled")
        to_year.grid(row=2, column=3, sticky=(tk.E, tk.S))

        from_label = ttk.Label(frame, text="From")
        from_label.grid(row=1, column=0, sticky=tk.W)
        to_label = ttk.Label(frame, text="To")
        to_label.grid(row=2, column=0, sticky=tk.W)

    def create_day_widgets(self, frame):
        ttk.Label(frame, text=("-> Select the day of interest\n(Selecting "
                               "Multiple days may cause errors in headway "
                               "calculations)")).grid(
            column=1, row=0, sticky="w", columnspan=2)
        day_boxes = []
        clm = 1
        rw = 1
        for i in range(0, len(self.days)):
            day_boxes.append(
                ttk.Radiobutton(frame, text=self.days[i],
                                variable=self.selected_day,
                                value=i, command=self.update_day_list).grid(
                                    row=rw, column=clm, sticky=tk.W
                )
            )
            rw += 1
            if rw > len(self.days) / 2:
                clm += 1
                rw = 1

    def create_file_widgets(self, frame):

        def set_file_path(variable):
            path = filedialog.askopenfilename()
            if path is not None:
                try:
                    self.files[variable].set(
                        os.path.relpath(path, self.current_dir))
                except ValueError:
                    return

        a = ttk.Label(frame, text="Operator Lookup")
        a.grid(column=0, row=5, sticky="w")
        CreateToolTip(a, text=("Contains information on which mode of "
                               "transport a service operator operates. This "
                               "will be created if one does not exist"))
        ttk.Entry(frame, width=50, textvariable=self.files["ops"]).grid(
            column=0, row=6)
        ttk.Button(frame, text="Browse",
                   command=lambda: set_file_path("ops")).grid(column=1, row=6)

        a = ttk.Label(frame, text="Mode Lookup")
        a.grid(column=0, row=7, sticky="w")
        CreateToolTip(a, text=("Defines the numbers assigned to each mode"))
        ttk.Entry(frame, width=50, textvariable=self.files["mode"]).grid(
            column=0, row=8)
        ttk.Button(frame, text="Browse",
                   command=lambda: set_file_path("mode")).grid(column=1, row=8)

        a = ttk.Label(frame, text="Bus Node Lookup")
        a.grid(column=0, row=1, sticky="w")
        CreateToolTip(
            a, text="Contains a one to one mapping of 'ATCOCode' to 'Node'")
        ttk.Entry(frame, width=50, textvariable=self.files["b_nod"]).grid(
            column=0, row=2)
        ttk.Button(
            frame,
            text="Browse",
            command=lambda: set_file_path("b_nod")
        ).grid(column=1, row=2)

        a = ttk.Label(frame, text="Rail Node Lookup")
        a.grid(column=0, row=3, sticky="w")
        CreateToolTip(a, text=("Contains a one to one mapping of 'TIPLOC' to "
                               "'Cube Node' and 'NAME'"))
        ttk.Entry(frame, width=50, textvariable=self.files["r_nod"]).grid(
            column=0, row=4)
        ttk.Button(
            frame,
            text="Browse",
            command=lambda: set_file_path("r_nod")
        ).grid(column=1, row=4)

        a = ttk.Label(frame, text="Patching Overrides File")
        a.grid(column=0, row=9, sticky="w")
        CreateToolTip(
            a, text=("File containing the user overrides to be used "
                     "in the patching process")
        )
        ttk.Entry(frame, width=50, textvariable=self.files["user_p"]).grid(
            column=0, row=10)
        ttk.Button(
            frame,
            text="Browse",
            command=lambda: set_file_path("user_p")
        ).grid(column=1, row=10)

    def add_frames(self):
        def add_frame(master, name, pos=[], c_span=1, r_span=1, s=()):
            new_frame = ttk.LabelFrame(master, text=name)
            new_frame.grid(row=pos[0], column=pos[1], rowspan=r_span,
                           columnspan=c_span, sticky=s, padx=3, pady=3)
            return new_frame
        self.header_frame = add_frame(
            self.master, "Explanation", [0, 1], s="w")
        self.day_def_frame = add_frame(
            self.master, "Day Definitions", [1, 1], s="w")
        self.date_def_frame = add_frame(
            self.master, "Date and Line Definitions", [2, 1], s="w")
        self.file_select_frame = add_frame(
            self.master, "Select Common Files", [3, 1], s="w")
        self.headway_frame = add_frame(
            self.master, "Headway Definition", [4, 1], s="w")
        self.GUI_frame = add_frame(self.master, "GUI Options", [5, 1], s="w")

    def update_date(self, index, value, op):
        new_date = [x.get() for x in self.date_from]
        prev_date = [x.get() for x in self.date_to]
        try:
            date(day=int(new_date[0]), month=int(
                new_date[1]), year=int(new_date[2]))
            for i in range(0, len(new_date)):
                self.date_to[i].set(new_date[i])
        except Exception as e:
            # self.log.add_message("Invalid Date", color="RED")
            print(e)
            for i in range(0, len(new_date)):
                self.date_from[i].set(prev_date[i])

    def set_defaults(self):

        f = self.files
        f["ops"].set(os.path.join(self.lookup_folder, "Operator_Codes.csv"))
        f["b_nod"].set(os.path.join(self.lookup_folder,
                                    "naptan_to_node_lookup_V27.1.csv"))
        f["r_nod"].set(os.path.join(self.lookup_folder,
                                    "tiploc_to_node_lookup_V1.csv"))
        f["user_p"].set(os.path.join(
            self.lookup_folder, "patching_overrides.txt"))
        try:
            os.makedirs(self.inter_dir)
        except FileExistsError:
            pass
        f["int"].set(self.inter_dir)
        self.files = f
        self.head_defs.set("7, 10, 16, 19")
        self.head_name.set("1, 2, 3")
        self.bank_hol.set(0)
        self.date_from[0].set("01")
        self.date_from[1].set("06")
        self.date_from[2].set("2015")

        for i in range(len(self.date_from)):
            self.date_from[i].trace("w", self.update_date)

        self.date_to[0].set("01")
        self.date_to[1].set("01")
        self.date_to[2].set("2020")
        self.auto_open.set(1)
        for i in range(0, len(self.selected_days)-1):
            self.selected_days[i].set(0)
        self.selected_days[2].set(1)
        self.selected_day.set(2)
