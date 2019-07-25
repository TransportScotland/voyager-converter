import os
import tkinter as tk
from tkinter import ttk, filedialog
from threading import Thread
from TableTemplate import TableWidget

class ThreadWithReturn(Thread):
    def __init__(self, group=None, target=None, name=None,
        args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None 
        
    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)
            
    def join(self):
        Thread.join(self)
        return self._return
        

class TextLog:
    def __init__(self, frame, width=50, height=8):
        self.log_frame = ttk.Frame(frame, borderwidth=2, relief=tk.GROOVE)
        self.log_frame.pack(side="top", padx=5, pady=5, ipadx=5, ipady=5)
        self.text = tk.Text(self.log_frame, width=width, height=height, wrap=tk.WORD)
        self.text.config(state=tk.DISABLED)
        self.scrollbar = tk.Scrollbar(self.log_frame)
        self.text.pack(side="left", fill="both", expand="yes")
        self.scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text.yview)
        self.text.tag_config('RED', foreground='red')
        self.text.tag_config('GREEN', foreground='green')
        self.text.tag_config('BLUE', foreground='blue')
        

        
    def add_message(self, message, color='', clear=False):
        
        self.text.config(state=tk.NORMAL)
        if clear == True:
            self.clear()
        if message.endswith('\n') == False:
            message += '\n'
        if color == '':
            self.text.insert(tk.END, message)
        else:
            self.text.insert(tk.END, message, color)
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)
        
    def clear(self):
        self.add_message("Clearing...")
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)

class CreateToolTip:
    def __init__(self, widget, text="Widget Info"):
        self.wait_time = 500
        self.wrap_length = 180
        self.widget = widget
        self.text = text 
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave) 
        self.wait_id = None
        self.top_window = None 
        
    def enter(self, event=None):
        self.begin_wait()
        
    def leave(self, eveny=None):
        self.stop_wait()
        self.destroy_tooltip()
        
    def begin_wait(self):
        self.stop_wait()
        self.wait_id = self.widget.after(self.wait_time, self.create_tooltip)
        
    def stop_wait(self):
        id = self.wait_id 
        self.id = None 
        if id:
            self.widget.after_cancel(id)
            
    def create_tooltip(self, event=None):
        x = 0
        y = 0
        x, y, w, h = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25 
        y += self.widget.winfo_rooty() + 20 
        
        self.top_window = tk.Toplevel(self.widget)
        self.top_window.attributes("-topmost", "true")
        
        self.top_window.wm_overrideredirect(True)
        self.top_window.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.top_window, text=self.text, justify="left", 
                         background="#ffffff", relief="solid", borderwidth=1,
                         wraplength=self.wrap_length)
        label.pack(ipadx=1)
        
    def destroy_tooltip(self):
        top_window = self.top_window
        self.top_window = None 
        if top_window:
            top_window.destroy()
            
class LabelledEntry:
    def __init__(self, master, text, var, w=5, lw=20,pack_side="top", 
                 tool_tip_text="", anchor="w", char_limit=None, 
                 px=5, py=5, lx=10,ly=8):
        self.px = px
        self.frame = ttk.Frame(master)
        self.frame.pack(side=pack_side,anchor=anchor,pady=py,padx=px)
        self.dir = None
        self.variable = var
        self.limit = char_limit
        
        okay_func = self.frame.register(self.validate)
        label = ttk.Label(self.frame, text=text,width=lw)
        label.pack(side="left",anchor=anchor,padx=lx, pady=ly)
        self.entry = ttk.Entry(self.frame, textvariable=var,width=w,
                               validate="all", validatecommand=(okay_func, "%P"))
        self.entry.pack(side="left",anchor="e")
        if tool_tip_text != "":
            CreateToolTip(label, tool_tip_text)
            
    def validate(self, text):
        if self.limit == None:
            return True
        if len(text) < self.limit:
            return True
        return False
        
    def add_button(self, callback_command, text=""):
        button = ttk.Button(self.frame, text=text, command=callback_command)
        button.pack(side="left", anchor="e", padx=self.px)
            
    def add_directory(self, working_dir, change_callback=None):
        self.dir = working_dir
        self.callback = change_callback
        button = ttk.Button(self.frame, text="Browse", command=self.get_working_dir)
        button.pack(side="left", anchor="e", padx=self.px)
            
    def add_browse(self, working_dir, save=False, 
                   types=(("CSV", "*.csv")), extension=".csv"):
        
        self.dir = tk.StringVar()
        self.dir.set(working_dir)
        if save == False:
            button = ttk.Button(self.frame, text="Browse", 
                                command=self.get_file_name)
        elif save == True:
            self.types = types
            button = ttk.Button(self.frame, text="Browse", 
                                command=lambda : self.get_save_file_name(extension))
        button.pack(side="left", anchor="e", padx=self.px)
        
    def get_working_dir(self):
        try:
            working_dir = filedialog.askdirectory(title=("Working Directory - "
                                                         "Containing: Data, "
                                                         "Input, Output Folders"))
        except ValueError:
            return
        if working_dir == "":
            return
        self.variable.set(working_dir)
        self.dir.set(working_dir)
        self.callback()
        
    def get_save_file_name(self, extension=".xlsx"):
        try:
            full_path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        except ValueError:
            return
        if full_path == "":
            return
        self.variable.set(os.path.relpath(full_path, self.dir.get()))
        
    def get_file_name(self):
        try:
            full_path = filedialog.askopenfilename(parent=self.frame)
        except ValueError:
            return
        if full_path == "":
            return
        self.variable.set(os.path.relpath(full_path, self.dir.get()))
        
# Container for a scrollable listbox that can add/remove items
class SelectBox:
    def __init__(self, frame, h, w, r, c, elements=[],span=4,select_mode=tk.MULTIPLE):
        self.contents=[]
        self.list = tk.Listbox(frame, height=h, width=w, selectmode=select_mode)
        self.list.grid(row=r, column=c, rowspan=span)
        self.scroll = tk.Scrollbar(frame)
        self.scroll.grid(row=r, column=c, sticky=(tk.E, tk.N, tk.S), rowspan=span)
        self.list.config(yscrollcommand=self.scroll.set)
        self.scroll.config(command=self.list.yview)
        self.init_list(elements)

    def init_list(self, elements, hidden=False):
        #elements.sort(key=int)
        if hidden == False:
            elements = sorted(elements)
        if len(self.contents) > 0:
            #Widget contains items, so remove all
            self.list.delete(0, len(self.contents))
            self.contents=[]
        for element in elements:
            if hidden == True:
                if element != "":
                    self.list.insert(tk.END, element)
            else:
                self.list.insert(tk.END, element)
            self.contents.append(element)
    
    def change_contents(self, elements=[], hidden=False):
        self.init_list(elements, hidden)
    def get_contents(self):
        return self.contents
    def get_selected(self):
        return self.list.curselection()

    def add(self, element):
        if element in self.contents:
            return
        else:
            self.contents.append(element)
            #self.contents.sort(key=int)
            self.contents = sorted(self.contents)
            i = self.contents.index(element)
            self.list.insert(i, element)

    def remove(self, element):
        if element in self.contents:
            i = self.contents.index(element)
            del self.contents[i]
            self.list.delete(i)

    def swap_element(self, other_select_box):
        for index in reversed(self.list.curselection()):
            if index == None:
                print("No operator selected")
                return
            element = self.contents[index]
            other_select_box.add(element)
            self.remove(element)

    def swap_all(self, other_select_box):
        for index in reversed(range(0, len(self.contents))):
            element = self.contents[index]
            other_select_box.add(element)
            self.remove(element)

        
        
        
        
        
        
