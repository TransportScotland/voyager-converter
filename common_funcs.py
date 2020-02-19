from datetime import datetime
from datetime import timedelta
from summarise_line_files import single_add_rts_back_in
#import tkinter as tk
#from tkinter import ttk
import csv
#from tkinter import filedialog

# Clear the back/forth check file
with open("Intermediate\\back_forth_services.txt","w"):
    pass
with open("Intermediate\\testing_lin.csv","w") as file:
    file.write(("Longname,Stops,Line,Mode,Operator,Oneway,Circular,Head[1],"
                "Head[2],Head[3],Seatcap,Crushcap,Loaddist,N\n"))

# Takes a string containing a single line of a service
# Retuns the same string but with line breaks so that 'width'
#   is not exceeded
def process_lin(text, break_char=",", width=80, comment_stops=False,
                node_lookup_file="Node Lookup Files\\tmfs_tiploc_to_node_v3.csv"):
    text_list = text.split(break_char)
    text_list = [x.strip() for x in text_list]

    # Get stop nodes
    try:
        with open(node_lookup_file,"r") as file:
            r = csv.DictReader(file)
            node_lookup = {row["Cube Node"]:row["SName"] for row in r}
    except:
        #print("Couldn't open lookup file")
        node_lookup = {}
    first_node = [i for i,x in enumerate(text_list) if "N=" in x][0]
    all_nodes = [x.strip("N=").strip("-") for x in text_list[first_node:] if "RT=" not in x]
    stop_nodes = [x.strip("N=") for x in text_list[first_node:]
                  if "-" not in x and "RT=" not in x]
    stop_names = [node_lookup.get(x,x) for x in stop_nodes]
    # Check for repeating nodes within x places
    check_length = 5
    no_repeating_nodes = all([all_nodes[i:i+check_length].count(x) == 1 for i,x 
                              in enumerate(all_nodes)])
    if no_repeating_nodes is False:
        repeating_nodes = [x for i,x 
                           in enumerate(all_nodes) if all_nodes[i:i+check_length].count(x) > 1]
        with open("Intermediate\\back_forth_services.txt","a") as file:
            file.write("%s in %s\n" % (",".join(repeating_nodes),",".join(text_list[:first_node])))
#    with open("Intermediate\\testing_lin.csv","a") as file:
#        file.write('%s,"%s",%s,"%s"\n' % (
#            text_list[1].split("=")[1],
#            ",".join(stop_names),
#            ",".join([x.split("=")[1] for i,x 
#                      in enumerate(text_list[:first_node]) if i != 1]),
#            ",".join(text_list[first_node:])))
    
    line_length = 0
    if comment_stops is False:
        parsed_text = ""
    else:
        parsed_text = ";Stops: %s\n" % ",".join(stop_names)
    for i, part in enumerate(text_list):
        if line_length + len(part) + len(", ") > width:
            parsed_text += "\n\t"
            line_length = 0
        parsed_text += part + ", "
        line_length += len(part) + len(", ")

    return parsed_text.strip(", ")

# Returns the left hand side of a string up to the specified index
def left(str,amt):
    return str[:amt]

# Returns the right hand side of a string from the specified index
def right(str, amt):
    return str[-amt:]

# Returns the slice of a string between specified indices
def mid(str,offset,amt):
    return str[offset:offset+amt]


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

# Prints a line file in the standard agreed format with line breaks after certain fields
# File paths contains paths of all AM,IP,PM files in that order
# Period is 0 - 2 and indicates AM, IP, PM
def print_rail_lin(data, file_paths):
    
    breaks = ["MODE=",
              "ONEWAY=",
              "HEADWAY[1]=",
              "HEADWAY[2]=",
              "HEADWAY[3]=",
              "CROWDCURVE[1]=",
              "CROWDCURVE[4]=",
              "SEATCAP="]
    
    in_line_files = file_paths
    
    for i, in_lin_file in enumerate(in_line_files):
        output_lin_file = in_lin_file#.replace(".LIN", "_LINENUMBERS.LIN")
        with open(output_lin_file, "w", newline="") as file:
            file.write(";;<<PT>><<LINE>>;;\n")
            for service in sorted(list(data[i].values()), 
                                  key=lambda k: int("".join(c for c in k["LINE NAME"] if c.isdigit()))):
                # If the service is flagged with None, can be ignored
                if service == None:
                    continue
                new_service = single_add_rts_back_in(service, [])
                line_string = ", ".join([k + "=" + v for k, v in new_service.items() if k != "N" and k != "RT"])
                line_string += ",\n\tN=" + ",\n\t".join([x.replace(",", ",\n\t") for x in new_service["N"]])
                result = line_string
                for break_point in breaks:
                    result = result.replace(break_point, "\n\t%s" % break_point)
                result = result.replace("\n\tRT=", " RT=")
                file.write(result)
                file.write("\n\n")

