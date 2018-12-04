import csv
import os
import tkinter as tk
from tkinter import ttk
from user_func_V2 import SelectBox, TextLog

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
        #width = 10
        #info = nu.ljust(width) + c.ljust(width) + na.ljust(width + 20) + ' ' + m
        return info

class OperatorTab:
    def __init__(self, note_book, operator_file="operator_lookup.csv", name=""):
        self.current_dir = os.path.dirname(__file__)
        
        self.frame = ttk.Frame(note_book)
        note_book.add(self.frame, text=name)
        self.file = os.path.join(self.current_dir, operator_file)
        self.operators = []
        self.s_operators = []
        self.header = []
        self.all_nums = set()
        self.all_codes = set()
        self.all_modes = set()
        self.f_all_modes = set(["ALL"])

        ttk.Label(self.frame, \
                  text=\
'''Use this tab to specify the mode of an operator (after importing the timetable data in other tabs)
Press "Load Operators" to populate the list with all operators in the lookup file
Change the mode of an operator by:
- Selecting the new mode in the drop down box
- Selecting the operator in the list
- Pressing "Change Mode"
Press "Save Operators" to overwrite the lookup file

Operator Number - Operator Code - Operator Name - Mode''',\
                  style="Head.TLabel").grid(row=0, column=1,columnspan=3, sticky="w")
            
        self.operator_box = SelectBox(
            self.frame, 20, 60, 1, 1,span=7,select_mode=tk.EXTENDED)
        self.operator_box.list.bind('<<ListboxSelect>>', self.on_select)

        self.number = tk.StringVar()
        self.code = tk.StringVar()
        self.mode = tk.StringVar()
        self.name = tk.StringVar()
        self.n_mode = tk.StringVar()
        self.f_mode = tk.StringVar()

        read_button = ttk.Button(self.frame, text="Load Operators", style="DS.TButton",command=self.load_file).grid(row=1,column=2)
        save_button = ttk.Button(self.frame, text="Save Operators", style="DS.TButton", command=self.save_to_file).grid(row=7,column=2)
        delete_button = ttk.Button(self.frame, text="Delete Selected", command=self.remove_elements).grid(row=6,column=2)
        update_button = ttk.Button(self.frame, text="Change Mode", command=self.update_operators).grid(row=3,column=3,sticky="n")
        filter_button = ttk.Button(self.frame, text="Filter by Mode", command=self.filter_operators).grid(row=5,column=3,sticky="n")

        self.f_mode_option = ttk.Combobox(self.frame, textvariable=self.f_mode, width=10)
        self.f_mode_option.grid(row=5,column=2,sticky="n")
        self.n_mode_option = ttk.Combobox(self.frame, textvariable=self.n_mode, width=10)
        self.n_mode_option.grid(row=3,column=2,sticky="n")

        self.log_frame = ttk.LabelFrame(self.frame, text="Log")
        self.log_frame.grid(row=8,column=1,columnspan=3,sticky="w",padx=3,pady=3)
        self.log = TextLog(self.log_frame)

        f_mode_label = ttk.Label(self.frame, text="Filter Modes").grid(row=4,column=2,sticky="s")
        n_mode_label = ttk.Label(self.frame, text="New Mode").grid(row=2,column=2,sticky="s")


    def on_select(self,evt):
        selected = self.operator_box.get_selected()
        if len(selected) == 1:
            op = self.s_operators[selected[0]]
            self.number.set(op.num)
            self.mode.set(op.mode)
        else:
            self.number.set("<multi>")
            self.mode.set("<multi>")

    def remove_elements(self):
        for index in reversed(self.operator_box.get_selected()):
            if index == None:
                print("No operator selected")
                return
            element = self.s_operators[index]
            del self.operators[self.operators.index(element)]
            del self.s_operators[index]
            self.operator_box.remove(index)
        self.update_box()

    def update_operators(self):
        for index in self.operator_box.list.curselection():
            op = self.s_operators[index]
            a_index = self.operators.index(op)
            self.operators[a_index].mode = self.n_mode.get()
            op.mode = self.n_mode.get()
        self.update_box()

    def filter_operators(self):
        for op in self.operators:
            if self.f_mode.get() == "ALL":
                op.show = True
            elif op.mode == self.f_mode.get():
                op.show = True
            else:
                op.show = False
        self.update_box()

    def set_file(self, operator_file):
        self.file = operator_file

    def load_file(self):
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
                    self.all_modes.add(row[0])
                    self.f_all_modes.add(row[0])
                    self.all_codes.add(row[1])
                    self.all_nums.add(row[2])
                    self.operators.append(OperatorInfo(row[0],row[1],row[2],row[3]))
            self.update_box()
        except IOError:
            self.log.add_message("Error: No operator file found\nTry running the tool and ensure the date/day \nranges are valid",color="RED")

    def save_to_file(self):
        try:
            with open(self.file, "w",newline="") as file:
                writer = csv.writer(file)
                writer.writerow(self.header)
                for op in self.operators:
                    writer.writerow([op.mode,op.code,op.num,op.name])
        except IOError:
            print("Cannot open file")
            return
                
    def update_box(self):
        ops = [x for x in self.operators]
        ops.sort(key=lambda x: x.num)
        self.s_operators = []
        for op in ops:
            if op.show == True:
                self.s_operators.append(op)
        ops = [x.get_string() for x in ops]
        self.operator_box.change_contents(ops, hidden=True)
        self.f_mode_option['values'] = list(self.f_all_modes)
        self.n_mode_option['values'] = list(self.all_modes)
