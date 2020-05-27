import tkinter as tk
from tkinter import ttk
import traceback


# Create Common directories
from pathlib import Path
Path("Intermediate").mkdir(parents=True, exist_ok=True)

import OperatorTab
import RailTab
import BusTab
import CommonTab
import SequenceReplaceTab
import SummaryTab
import RenumberTab

######################################################



#Class that represents the overall gui
class Application():
    """Initialise the Voyager Converter application
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cube PT Line Coder")
        self.buttons = []
        self.default_file = "default_variables.txt"

        button_style = ttk.Style()
        button_style.configure('DS.TButton', foreground="green",relief="flat")
        header_style = ttk.Style()
        header_style.configure("Head.TLabel", font=("Helvetica",10,"bold"))
        self.init_widgets()
        
    #Create the frames needed to group various widgets together
    def init_widgets(self):
        n_book = ttk.Notebook()

        self.general = CommonTab.CommonTab(n_book, self.load_defaults, 
                                           self.save_defaults, 
                                           name="General Options")
        self.bu_tab = BusTab.BusTab(n_book, self.general,name="Bus Import")
        self.ra_tab = RailTab.RailTab(n_book,self.general,name="Rail Import")
        self.op_tab = OperatorTab.OperatorTab(n_book, self.general,
                                              self.general.files["ops"].get(), 
                                              name="Assign Operators")
        self.seq_tab = SequenceReplaceTab.SequenceReplaceTab(n_book, self.general, 
                                              name="Sequence Replace")
        self.sum_tab = SummaryTab.SummaryTab(n_book, self.general, name="LIN Summary")
        n_book.pack(expand=1, fill="both")
        self.renum_tab = RenumberTab.RenumberTab(n_book, self.general, name="LINE Renumber")
        n_book.pack(expand=1, fill="both")
        
        self.load_defaults()
        
    def load_defaults(self):
        try:
            with open(self.default_file, "r") as file:
                data = [x.strip() for x in file.readlines()]
                try:
                    self.defaults = {x.split("=")[0]:x.split("=")[1].strip('"') for x in data}
                except Exception:
                    print(data)
                self.keys = {k:self.defaults.get(k, "") for k in self.defaults if
                             k in ["{lookup_folder}",
                                  "{inter_folder}",
                                  "{output_folder}"]}
                
                for cat in self.defaults:
                    for key in self.keys:
                        self.defaults[cat] = self.defaults[cat].replace(key, self.keys[key])
                
                self.general.files["ops"].set(self.defaults["operator_file"])
                self.general.files["b_nod"].set(self.defaults["bus_node_lookup"] )
                self.general.files["r_nod"].set(self.defaults["rail_node_lookup"] )
                self.general.files["mode"].set(self.defaults["mode_lookup"])
                self.general.files["user_p"].set(self.defaults["patching_overrides"])
                self.ra_tab.files["MCA"].set(self.defaults["mca_data"])
                self.ra_tab.files["MSN"].set(self.defaults["msn_data"] )
                self.bu_tab.files["XML"].set(self.defaults["xml_directory"])
                self.general.inter_folder = self.defaults["intermediate_directory_name"]
                self.general.head_name.set(self.defaults["headway_names"])
                self.general.head_defs.set(self.defaults["headway_definitions"])
                for i in range(len(self.general.date_from)):
                    self.general.date_from[i].set(self.defaults["date"].split("/")[i])
                for i in range(len(self.defaults["selected_day"])):
                    self.general.selected_days[i].set(int(self.defaults["selected_day"][i]))
                self.ra_tab.node_file = self.defaults["rail_node"]
                self.ra_tab.link_file = self.defaults["rail_link"] 
                self.bu_tab.node_file = self.defaults["bus_node"] 
                self.bu_tab.link_file = self.defaults["bus_link"]
                
                self.ra_tab.log.add_message("Loaded Default Variables", color="GREEN")
                self.bu_tab.log.add_message("Loaded Default Variables", color="GREEN")
        except Exception as e:
            print("Error Loading Defaults", e)
            print("Traceback: %s" % "".join(traceback.format_tb(e.__traceback__)))
            self.defaults = {}
            
        
    def save_defaults(self):
        try:
            self.defaults["operator_file"] = self.general.files["ops"].get()
            self.defaults["bus_node_lookup"] = self.general.files["b_nod"].get()
            self.defaults["rail_node_lookup"] = self.general.files["r_nod"].get()
            self.defaults["mode_lookup"] = self.general.files["mode"].get()
            self.defaults["patching_overrides"] = self.general.files["user_p"].get()
            self.defaults["mca_data"] = self.ra_tab.files["MCA"].get()
            self.defaults["msn_data"] = self.ra_tab.files["MSN"].get()
            self.defaults["xml_directory"] = self.bu_tab.files["XML"].get()
            self.defaults["intermediate_directory_name"] = self.general.inter_folder
            self.defaults["headway_names"] = self.general.head_name.get()
            self.defaults["headway_definitions"] = self.general.head_defs.get()
            self.defaults["date"] = "/".join([x.get() for x in self.general.date_from])
            self.defaults["selected_day"] = "".join([str(x.get()) for x in self.general.selected_days])
            self.defaults["rail_node"] = self.ra_tab.node_lookup.get()
            self.defaults["rail_link"] = self.ra_tab.link_lookup.get()
            self.defaults["bus_node"] = self.bu_tab.node_lookup.get()
            self.defaults["bus_link"] = self.bu_tab.link_lookup.get()

            for cat in self.defaults:
                reverse_keys = {v:k for k, v in self.keys.items()}
                if cat not in self.keys:
                    for key in reverse_keys:
                        self.defaults[cat] = self.defaults[cat].replace(key, reverse_keys[key])
            
            with open(self.default_file, "w", newline="") as file:
                for k, v in self.defaults.items():
                    file.write('%s="%s"\r\n' % (k, v))
                    
            self.ra_tab.log.add_message("Saved Default Variables", color="GREEN")
            self.bu_tab.log.add_message("Saved Default Variables", color="GREEN")
            
        except Exception as e:
            print("Error Saving Defaults", e)
            print("Traceback: %s" % "".join(traceback.format_tb(e.__traceback__)))
            self.defaults = {}
            
