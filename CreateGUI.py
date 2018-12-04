import tkinter as tk
from tkinter import ttk

import OperatorTab
import RailTab
import BusTab
import PatchTab
import CommonTab

######################################################


#Class that represents the overall gui
class Application():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rail CIF to Cube Voyager Line Converter")
        self.buttons = []

        button_style = ttk.Style()
        button_style.configure('DS.TButton', foreground="green",relief="flat")
        header_style = ttk.Style()
        header_style.configure("Head.TLabel", font=("Helvetica",10,"bold"), foreground="blue")
        self.init_widgets()
        
    #Create the frames needed to group various widgets together
    def init_widgets(self):
        n_book = ttk.Notebook()

        self.general = CommonTab.CommonTab(n_book, name="General Options")
        self.bu_tab = BusTab.BusTab(n_book, self.general,name="Bus Import")
        self.ra_tab = RailTab.RailTab(n_book,self.general,name="Rail Import")
        self.pa_tab = PatchTab.PatchTab(n_book, self.bu_tab, self.ra_tab, self.general, name="Rail Patching")
        self.op_tab = OperatorTab.OperatorTab(n_book, self.general.files["ops"].get(), name="Assign Operators")
        n_book.pack(expand=1, fill="both")

#Initialise the GUI               
app = Application()
app.root.mainloop()
