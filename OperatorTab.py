import csv
import os
import tkinter as tk
from tkinter import ttk
from WidgetTemplates import TextLog, TableWidget

class OperatorInfo:
    def __init__(self, mode, code, num, name):
        self.mode = mode
        self.code = code
        self.num = int(num)
        self.name = name
        self.show = True
    def get_string(self):
        if self.show == False:
            return ""
        m = self.mode[:5] if len(self.mode) > 5 else self.mode
        c = self.code[:5] if len(self.code) > 5 else self.code
        nu = self.num[:5] if len(str(self.num)) > 5 else str(self.num)
        na = self.name[:30] if len(self.name) > 30 else self.name + ' '*(30-len(self.name))
        info = '{:<10}'.format(nu) + ' {:<10}'.format(c)+ ' {:<3}'.format(m) + ' {:<50}'.format(na) 
        return info

class OperatorTab:
    def __init__(self, note_book, general, operator_file="operator_lookup.csv", name=""):
        self.current_dir = os.path.dirname(__file__)
        
        self.frame = ttk.Frame(note_book)
        note_book.add(self.frame, text=name)
        self.gen = general
        #self.file = os.path.join(self.current_dir, operator_file)
        self.file = self.gen.to_path("ops")
        self.operators = []
        self.s_operators = []
        self.header = []
        self.all_nums = set()
        self.all_codes = set()
        self.all_modes = set()
        self.f_all_modes = set(["ALL"])

        lf = ttk.Labelframe(self.frame, text="Explanation")
        lf.pack(padx=5, pady=5)
        ttk.Label(lf,
                text='''Change the classification of an operator in the operator file
Press "Load Operators" to populate the list with all operators in the operator file
Any changes can be made by clicking on the cell and pressing 'enter' after the change has been made
Press Save Operators to save changes to the file (Cannot be undone)''',
                  style="Head.TLabel").pack(side="top")
        
        self.main_frame = ttk.Frame(self.frame)
        self.main_frame.pack(side="top")
        self.table_frame = ttk.Frame(self.main_frame)
        self.input_frame = ttk.Frame(self.main_frame)
        self.table_frame.pack(side="left",anchor="w")
        self.input_frame.pack(side="left", anchor="e")
        
        self.operator_box = TableWidget(self.table_frame,
                                        ["No.","Code","Operator Name","Mode"],
                                        stripped_rows=("white","#f2f2f2"),
                                        select_mode="none",
                                        editable=True,
                                        non_edit=[],
                                        hscrollbar=False)
        self.operator_box.grid(row=1,column=1,rowspan=2)

        self.number = tk.StringVar()
        self.code = tk.StringVar()
        self.mode = tk.StringVar()
        self.name = tk.StringVar()
        self.n_mode = tk.StringVar()
        self.f_mode = tk.StringVar()

        read_button = ttk.Button(self.input_frame, text="Load Operators",
                                 style="DS.TButton",command=self.load_file)
        read_button.pack(side="top")
        save_button = ttk.Button(self.input_frame, text="Save Operators",
                                 style="DS.TButton", command=self.save_to_file)
        save_button.pack(side="top")
        delete_button = ttk.Button(self.input_frame, text="Delete Selected",
                                   command=self.remove_elements)
        delete_button.pack(side="top")
        
        self.log_frame = ttk.LabelFrame(self.frame, text="Log")
        self.log_frame.pack(side="top")
        self.log = TextLog(self.log_frame)

    def remove_elements(self):
        to_delete = self.operator_box.indices_of_selected_rows
        to_delete.sort(key=lambda x: int(x),reverse=True)
        for i in to_delete:
            self.operator_box.delete_row(i)

    def update_operators(self):
        for index in self.operator_box.list.curselection():
            op = self.s_operators[index]
            a_index = self.operators.index(op)
            self.operators[a_index].mode = self.n_mode.get()
            op.mode = self.n_mode.get()
        self.update_box()

    def load_file(self):
        self.file = self.gen.to_path("ops")
        try:
            with open(self.file, "r") as file:
                if not file.read(1):
                    return
                self.operators = []
                file.seek(0)
                reader = csv.reader(file)
                self.header = next(reader)
                for row in reader:
                    if len(row) != 4:
                        continue
                    self.operators.append([row[2],row[1],row[3],row[0]])
            self.update_box()
        except IOError:
            self.log.add_message(("Error: No operator file found\n"
                                  "Try running the tool and ensure the "
                                  "date/day \nranges are valid"),color="RED")

    def save_to_file(self):
        self.file = self.gen.to_path("ops")
        try:
            with open(self.file, "w",newline="") as file:
                writer = csv.writer(file)
                writer.writerow(self.header)
                self.operators = self.operator_box.table_data
                for row in self.operators:
                    writer.writerow([row[3],row[1],row[0],row[2]])
            self.log.add_message("Saved %d operators to file" % len(self.operators))
        except IOError:
            print("Permission Denied: Cannot open file")
            return
                
    def update_box(self):
        ops = [x for x in self.operators]
        ops.sort(key=lambda x: int(x[0]))
        self.operator_box.table_data = ops
