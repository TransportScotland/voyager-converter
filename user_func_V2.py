from datetime import datetime
from datetime import timedelta
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

# Container for the log widgets
class TextLog:
    def __init__(self, frame):
        self.text = tk.Text(frame, height=8, width=50)
        self.scrollbar = tk.Scrollbar(frame)
        self.text.grid(row=1,column=1)
        self.scrollbar.grid(row=1,column=1,sticky=(tk.N,tk.S,tk.E), rowspan=10)
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.text.yview)
        self.text.tag_config('RED', foreground='red')
        self.text.tag_config('GREEN', foreground='green')

    def add_message(self, message, color=''):
        if message.endswith('\n') == False:
            message += '\n'
        if color == '':
            self.text.insert(tk.END, message)
        else:
            self.text.insert(tk.END, message, color)
        self.text.see(tk.END)

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

# Returns the left hand side of a string up to the specified index
def left(str,amt):
    return str[:amt]

# Returns the right hand side of a string from the specified index
def right(str, amt):
    return str[-amt:]

# Returns the slice of a string between specified indices
def mid(str,offset,amt):
    return str[offset:offset+amt]

# Container for date objects 
class date_entry:
    def __init__(self, date=[0,0,0]):
        date = [int(x) for x in date]
        self.day = date[0]
        self.month = date[1]
        if date[2] < 100:
            self.year = 2000 + date[2]
        else:
            self.year = date[2]

    # Returns true if the date is later than or equal to the argument given
    def is_later_than(self, other):
        if self.year > other.year:return True
        elif self.year == other.year:
            if self.month > other.month: return True
            elif self.month == other.month:
                    if self.day >= other.day: return True
        else:
            return False

    # Returns true if the date is between 'start' and 'end ' 
    def within_range(self, start, end):
        if self.is_later_than(start) and end.is_later_than(self):
            return True
        else:
            return False

    # Returns true if a range of dates self-other and start-end has any overlap at all
    def has_overlap(self,other,start,end):
        if self.within_range(start,end) or other.within_range(start,end)\
           or start.within_range(self,other) or end.within_range(self,other):
            return True
        else:
            return False

# Returns the mid point of two times
# Times given in the form of a string with the format "HHMM" (e.g 09:56 as "0956")
def find_mid(start, end):   #"HHMM"
    s = datetime.strptime(str(start[:-2]) + ":" + str(start[-2:]), "%H:%M")
    e = datetime.strptime(str(end[:-2]) + ":" + str(end[-2:]), "%H:%M")

    if s <= e:
        diff = e - s
    else:
        e += timedelta(days=1)
        diff = e - s
    return (s + diff // 2).strftime("%H:%M")

# Returns the difference between two times
# Times given in the form of a string with the format "HHMM" (e.g 09:56 as "0956")
def time_diff(start, end):  
    try:
        s = datetime.strptime(str(start[:-2]) + ":" + str(start[-2:]), "%H:%M")
        e = datetime.strptime(str(end[:-2]) + ":" + str(end[-2:]), "%H:%M")
    except ValueError:
        print(start, end)

    if s <= e:
        diff = e - s
    else:
        e += timedelta(days=1)
        diff = e - s
    return str(int(diff.total_seconds() / 60))

# Returns a boolean to represent if the schedule is valid
# Schedule given by CIF_line. Checks if service is on a valid day and date
def check_valid_schedule(CIF_line,day_filter, timetable_days, running_dates, date_filter):
    if mid(CIF_line,79,1)=='C':
        return False
    valid_schedule=False
    day_valid=False
    date_valid=True
    BH_valid=True
    bankhols = timetable_days[-1]
    for x in range(len(timetable_days)-1):
            if day_filter[x] == '1' and timetable_days[x] == '1':
                    day_valid=True
    if day_filter[7]==1 and (bankhols=='X' or bankhols=='G'):
            BH_valid=False
    #Check date is valid
    date_range = [date_entry(date_filter[0]), date_entry(date_filter[1])]
    date_valid = date_range[0].has_overlap(date_range[1], running_dates[0], running_dates[1])

    valid_schedule = date_valid and day_valid and BH_valid
    return valid_schedule

def valid_TOC_time(CIF_Line):
    TOC_valid=False
    tvalid1=False
    tvalid2=False
    if len(T1_TOC2)==0:
        TOC_valid=False
    else:
        for m1 in range(0,len(T1_TOC2 - 1)):
            listitem=T1_TOC2[m1]
            if CIF_Line==listitem:
                TOC_valid=True
                break
    #Check times
    
            
# Calculate journey time 
def calc_jt(begintime,finishtime):
    begin_hour=int(left(begintime,2))
    begin_min=int(right(begintime,2))
    finish_hour=int(left(finishtime,2))
    finish_min=int(right(finishtime,2))
    if begin_hour>finish_hour:
        dur_hour=23-begin_hour+finish_hour
        min1=60-begin_min
        min2=finish_min
        total_dur=(dur_hour*60)+min1+min2
        return total_dur
    else:
        dur_hour=finish_hour-begin_hour
        if begin_min>finish_min:
            dur_hour-=1
            min1=60-begin_min
            min2=finish_min
            total_dur=(dur_hour*60)+min1+min2
            return total_dur
        else:
            min3=finish_min-begin_min
            total_dur=(dur_hour*60)+min3
            return total_dur

# Clear all the variables
# (Not sure if this is needed or works - lots of local variables)
def clear_serv_var():
    transtype = None
    Route = None
    uniqueID = None
    firstdate = None
    lastdate = None
    mon = None
    tue = None
    wed = None
    thu = None
    fri = None
    sat = None
    sun = None
    bankhols = None
    status = None
    catgry = None
    t_identity = None
    headcode = None
    serv_code = None
    power = None
    timing = None
    tclass = None
    sleepers = None
    reservs = None
    sbrand = None
    TOC = None
    begintime = None
    finishtime = None
    numstations = 0
    #TIPLOCvalue.Clear()
    #arrivevalue.Clear()
    #departvalue.Clear()
    #passvalue.Clear()
    #statnamevalue.Clear()
    o_stat = None
    t_stat = None
    fromto = None

    return transtype
    return Route
    return uniqueID
    return firstdate
    return lastdate
    return mon
    return tue
    return wed
    return thu
    return fri
    return sat
    return sun
    return bankhols
    return status
    return catgry
    return t_identity
    return headcode
    return serv_code
    return power
    return timing
    return tclass
    return sleepers
    return reservs
    return sbrand
    return TOC
    return begintime
    return finishtime
    return numstations
    #return TIPLOCvalue.Clear()
    #return arrivevalue.Clear()
    #return departvalue.Clear()
    #return passvalue.Clear()
    #return statnamevalue.Clear()
    return o_stat
    return t_stat
    return fromto
