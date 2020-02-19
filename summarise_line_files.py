#
#   The main function of this script summarises PT lines files to get the counts for each line/service
#
#   get_inter_urban_counts() is used to compare the bus counts between areas identified in a node mapping file
#       e.g. a corridor between two major urban areas


import os
import csv
from math import sqrt
from collections import OrderedDict

def file_reader(file):
    while True:
        try:
            line = next(file).strip()
        except StopIteration:
            return
        if line != "":
            if line[0] != ";":
                yield line
                
# Strip the list of nodes from a string
def get_node_list(line, rts=False, previous_rts=[], prev_num_nodes=0):
    data = [x.strip() for x in line.strip(",").split(",")]
    f = [x.split("=")[1] if len(x.split("=")) == 2 and x.split("=")[0] == "N" 
         else x for x in data]
    
    if rts is True:
        new_rts = previous_rts 
        num_new_rts = 0
        last_rt = prev_num_nodes 
        d = line.replace("N=", "")
        for s in d.split(", "):
            if "RT=" in s:
                new_rts.append(
                        [s.replace("RT=", ""), last_rt + [
                                x for x in d.split(", ") if (
                                        len(x.split("=")) == 1 or
                                        x.split("=")[0] == "N" or
                                        x.split("=")[0] == "RT")].index(s) - num_new_rts])
                num_new_rts += 1
        
    return [x for x in f if "=" not in x], previous_rts

def split_data(line, delimiter, get_rts=False, rts_list=[], prev_num_nodes=0):
    try:
        data = [x.strip() for x in line.split(delimiter)]
        data_dict = OrderedDict((name, value) for name, value 
                                in [x.split("=") for x in data if "=" in x] 
                                if name != "N" and name != "RT")
        node_list = [x for x in data if "=" not in x and x != ""]
        node_list, rts_list = get_node_list(line, rts=get_rts, previous_rts=[], 
                                            prev_num_nodes=prev_num_nodes)
    except:
        print(line)
        raise Exception
    return (data_dict, data[-1] == "", node_list, rts_list)
    
def parse_name(name, default_line):
    # In this casae the name is usually made up of "$operator $line $route"
    for i, x in enumerate(name.split(" ")):
        if any(c.isdigit() for c in x):
            return (" ".join(name.split(" ")[:i]), x, " ".join(name.split(" ")[i+1:]))
    # If it does not follow the format 
    return (name, default_line, name)

# For rail the process will be slightly different
# Need to remove the RT=x at various points in the 
def read_lin_file(lin_file):
    with open(lin_file, "r") as file:
        services = []
        current_line = None
        node_list = []
        rt_list = []
        for line in file_reader(file):
            if current_line is None and "LINE NAME" in line:
                current_line, _, _, _ = split_data(line, ",")
                current_line["N"] = []
                current_line["RT"] = []
            elif current_line is not None:
                data, more_data_exists, node_list, rt_list = split_data(line, ",", 
                                    get_rts=True, prev_num_nodes=len(current_line["N"]))
                current_line.update(data)
                try:
                    current_line["N"] += node_list
                    current_line["RT"] += rt_list
                except KeyError:
                    pass
                if more_data_exists is False:
                    services.append(current_line)
                    current_line.move_to_end("N")
                    rt_list = []
                    # print(current_line["N"], current_line["RT"])
                    current_line = None
                    
            else:
                pass
    return services

def add_rts_back_in(services, include_rts=False, added_nodes=[]):
    # Added nodes has form [[num_added, position], [], []]
    for i in range(len(services)):
        if include_rts is True:
            # Cycle through the RTs and add the extra nodes to the position
            for j in range(len(services[i]["RT"])):
                services[i]["RT"][j][1] += sum([x[0] for x in added_nodes if x[1] < services[i]["RT"][j][1]])
            for rt, pos in reversed(services[i]["RT"]):
                services[i]["N"].insert(pos-1, "RT=%s" %rt)
                if pos < len(services[i]["N"]):
                    services[i]["N"][pos+1] = "N=%s" % services[i]["N"][pos+1]
        del services[i]["RT"]
    return services
    
def single_add_rts_back_in(service, added_nodes):
    # Cycle through the RTs and add the extra nodes to the position
    num_nodes = len(service["N"])
    for j in range(len(service["RT"])):
        service["RT"][j][1] += sum([x[1] for x in added_nodes if x[0]+1 < service["RT"][j][1]])
    for rt, pos in reversed(service["RT"]):
        service["N"].insert(pos, "RT=%s" % rt.strip(","))
        if pos < num_nodes:
            service["N"][pos+1] = "N=%s" % service["N"][pos+1]
    return service
    
def headway_to_count(headway, length):
    try:
        count = length / float(headway)
    except ZeroDivisionError:
        count = 0
    return round(count, 1)

def parse_lin_service(x, convert_headway=True, operator_lookup=None):
    if convert_headway is True:
        head_func = headway_to_count
    else:
        head_func = lambda headway,_ : headway
    if operator_lookup is None:
        parsed_service = [parse_name(x["LONGNAME"], x["LINE NAME"])[2].strip('"'),
                          parse_name(x["LONGNAME"], x["LINE NAME"])[1].strip('"'), 
                     parse_name(x["LONGNAME"], x["LINE NAME"])[0],
                     x["CIRCULAR"], x["MODE"], head_func(x.get("HEADWAY[1]", 0), 180),
                     head_func(x.get("HEADWAY[2]",0), 360),
                      head_func(x.get("HEADWAY[3]",0), 180), "F", ",".join(x["N"])]
    else:
        parsed_service = [parse_name(x["LONGNAME"], x["LINE NAME"])[2].strip('"'),
                          parse_name(x["LONGNAME"], x["LINE NAME"])[1].strip('"'), 
                     operator_lookup.get(x["OPERATOR"]),
                     x["CIRCULAR"], x["MODE"], head_func(x.get("HEADWAY[1]", 0), 180),
                     head_func(x.get("HEADWAY[2]",0), 360),
                      head_func(x.get("HEADWAY[3]",0), 180), "F", ",".join(x["N"])]
    return parsed_service
    

def summarise_lin_file(services, out_file, operator_lookup=None):
    with open(out_file, "w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["name", "line", "operator", "circular", "mode", "AM", 
                    "IP", "PM", "is_total", "nodes"])
        parsed_data = [parse_lin_service(x, operator_lookup=operator_lookup) for x in services]
        unique_services = {(x[1],x[2]):x[:5] + [0,0,0, "Y"] for x in parsed_data}
        for _,line, op, _, _, am, ip, pm, _, _ in parsed_data:
            unique_services[(line,op)][5] += am
            unique_services[(line,op)][6] += ip
            unique_services[(line,op)][7] += pm
        w.writerows(parsed_data + list(unique_services.values()))

# 
def get_inter_urban_counts(summary_file, urban_definitions_file, 
                           urban_summary_file, urban_services_file):
    
    with open(urban_definitions_file, "r") as file:
        r = csv.DictReader(file)
        urban_nums = {str(row["N"]):str(row["urban_area"]) for row 
                      in r if str(row["urban_area"]) != "0"}
    with open(urban_definitions_file, "r") as file:
        r = csv.DictReader(file)
        unique_areas = list(set([row["urban_area"] for row 
                                 in r if row["urban_area"] != "0"]))
    with open(summary_file, "r") as file:
        r = csv.reader(file)
        summary_data = [x for x in r]
        
    unique_areas.sort(key=lambda x:int(x))
    counts = {(str(o), str(d)):[0,0,0] for o in unique_areas for d in unique_areas}
    relevant_services = {(str(o), str(d)):[] for o in unique_areas for d in unique_areas}
    for service in summary_data:
        nodes = service[-1].split(",")
        areas = []
        for node in nodes:
            area = urban_nums.get(node)
            if area is not None:
                areas.append(area)
        # Check if it is inter-urban/ goes from one
        # urban zone to another
        if len(set(areas)) > 1:
            # get o-d
            o = areas[0]
            d = areas[-1]
            am, ip, pm = [float(x) for x in service[5:8]]
            counts[(o, d)][0] += am
            counts[(o, d)][1] += ip
            counts[(o, d)][2] += pm
            relevant_services[(o, d)].append(service)
    with open(urban_summary_file, "w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["origin", "destination", "AM", "IP", "PM"])
        w.writerows([[k[0], k[1]] + v for k, v in counts.items()])
    with open(urban_services_file, "w", newline="") as file:
        w = csv.writer(file)
        w.writerows([[k[0], k[1]] + x for k, v in relevant_services.items() for x in v])

def flag_services(services, urban_definitions_file,
                  out_file, operator_lookup, node_lookup_file,
                  la_lookup_file, cordon_lookup_file):
    with open(urban_definitions_file, "r") as file:
        r = csv.DictReader(file)
        urban_nums = {str(row["N"]):str(row["urban_area"]) for row in r}
    with open(node_lookup_file, "r") as file:
        r = csv.DictReader(file)
        node_coords = {str(row["N"]):(str(row["X"]), str(row["Y"])) for row in r}
    with open(la_lookup_file, "r") as file:
        r = csv.DictReader(file)
        la_nodes = {str(int(float(row["N"]))):str(row["LA"]) for row in r}
    with open(cordon_lookup_file, "r") as file:
        r = csv.DictReader(file)
        cordon_nodes = {str(int(float(row["N"]))):row["CORDON"] for row in r}
    # Add new field 'flag'
    for i in range(len(services)):
        node_list = services[i]["N"]

        #Calculate the distance as the crow flies of the service
        start_coords = [int(float(x)) for x in node_coords[node_list[0].strip("-")]]
        end_coords = [int(float(x)) for x in node_coords[node_list[-1].strip("-")]]
        distance = sqrt((start_coords[0] - end_coords[0])**2 +
                        (start_coords[1] - end_coords[1])**2)
        
        urban_zones = [urban_nums.get(x) for x in node_list]
        urban_zones = [x for x in urban_zones if x is not None] # Remove unmatched values
        la_route = [la_nodes.get(x,None) for x in node_list]
        full_cordon_route = [cordon_nodes.get(x) for x in node_list]
        try:
            #Need to run twice to remove Nones and then duplicates
            la_route = [x for i, x in enumerate(la_route)
                        if x is not None and (i == 0 or x != la_route[i-1])]
            la_route = [x for i, x in enumerate(la_route)
                        if x is not None and (i == 0 or x != la_route[i-1])]
        except:
            print("Error processing route to cordon/urban areas")
            print(node_list)
            return
        cordon_route = [x for i, x in enumerate(full_cordon_route)
                        if x is not None and (i == 0 or x != full_cordon_route[i-1])]
        cordon_route = [x for i, x in enumerate(cordon_route)
                        if x is not None and (i == 0 or x != cordon_route[i-1])]
        
        ### Set Urban Flag intra/inter/between/external
        # If all nodes are urban -> 'intra'
        if urban_zones[0] != "0" and all([x == urban_zones[0] for x in urban_zones]):
            flag = "intra"
            start_zone = end_zone = urban_zones[0]
        # If nodes start and end in urban -> 'between'
        elif len(set(urban_zones)) > 2: # (Visits more than one zone)
            flag = "between"
            start_zone = urban_zones[0]
            end_zone = urban_zones[-1]
        # Otherwise it is either not in an urban area or only in one
        elif len(set(urban_zones)) == 1:
            flag = "external"
            start_zone = urban_zones[0]
            end_zone = urban_zones[-1]
        else:
            flag = "inter"
            start_zone = urban_zones[0]
            end_zone = urban_zones[-1]
            
        ### Set Cordon Flag
        if len(cordon_route) > 1:
            # The route must pass through a cordon
            cordon_flag = "PASS_CORDON"
        else:
            cordon_flag = "NOT_PASS_CORDON"
            
        services[i]["cordon_flag"] = cordon_flag
        services[i]["cordon_route"] = "-".join(cordon_route)

        services[i]["s_urban"] = start_zone
        services[i]["e_urban"] = end_zone
        services[i]["flag"] = flag
        services[i]["distance"] = distance

        # If TMfS14 system use this
        services[i]["unique_links"] = parse_lin_service(
            services[i], convert_headway=False, operator_lookup=operator_lookup)[1]
        # Otherwise use this
        try:
            services[i]["unique_line"] = str(services[i]["LINE NAME"].strip('"').split("-")[0])
        except IndexError:
            services[i]["unique_line"] = "Not Found"
        
        try:
            services[i]["s_la"] = la_route[0]
        except IndexError:
            services[i]["s_la"] = "Not Found"
        try:
            services[i]["e_la"] = la_route[-1]
        except IndexError:
            services[i]["e_la"] = "Not Found"
        services[i]["la_route"] = ", ".join(la_route)
        
    parsed_data = [[x["LINE NAME"]] + parse_lin_service(x, convert_headway=False, operator_lookup=operator_lookup) +
                   [x["s_urban"], x["e_urban"], x["flag"],
                    x["s_la"], x["e_la"], x["la_route"],
                    x["distance"],x["unique_line"],
                    "", "", "", "", x["cordon_flag"], x["cordon_route"]] for x in services]

    with open(out_file, "w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["name", "line", "operator", "circular", "mode",
                    "AM", "IP", "PM", "is_total", "nodes",
                    "start_urban_zone", "end_urban_zone", "flag",
                    "start_local_authority", "end_local_authority",
                    "local_authorty_route",
                    "distance", "line_base", "joined_name",
                    "am_freq", "ip_freq", "pm_freq", "cordon_flag",
                    "cordon_route"])
        w.writerows(parsed_data)
        
def load_operator_lookup(file):
    with open(file, "r") as f:
        r = csv.DictReader(f)
        lookup = {row["Number"]:row["Name"] for row in r}
    return lookup

def summarise_main(lin_file, summary_file, urban_areas, operator_lookup_file=None):
    file_name = lin_file
    name = os.path.split(file_name)[-1].split(".")[0]
    urban_summary_file = os.path.join("Intermediate", "urban_summary_%s.csv" % name)
    urban_services_file = os.path.join("Intermediate", "urban_services_%s.csv" % name)
    s = read_lin_file(file_name)
    
    add_rts_back_in(s, include_rts=False)
    
    if operator_lookup_file is not None:
        operator_lookup = load_operator_lookup(operator_lookup_file)
    summarise_lin_file(s, summary_file, operator_lookup=operator_lookup)
    get_inter_urban_counts(summary_file, urban_areas,
                           urban_summary_file, urban_services_file)

def flag_main(lin_file, summary_file, urban_areas, operator_lookup_file=None,
              node_lookup_file=None, la_lookup_file=None, cordon_lookup_file=None):
    file_name = lin_file
    name = os.path.split(file_name)[-1].split(".")[0]
    s = read_lin_file(file_name)
    if operator_lookup_file is not None:
        operator_lookup = load_operator_lookup(operator_lookup_file)
    flag_services(s, urban_areas, summary_file,
                  operator_lookup, node_lookup_file, la_lookup_file,
                  cordon_lookup_file)
                    
def main():
    file_name = "Inter_Urban_Bus_BHAA18.lin"
    summary_file = os.path.join("Intermediate", "summary_%s.csv" % "".join(file_name.split(".")[:-1]))
    urban_summary_file = os.path.join("Intermediate", "urban_%s.csv" % "".join(file_name.split(".")[:-1]))
    urban_services_file = os.path.join("Intermediate", "urban_services_%s.csv" % "".join(file_name.split(".")[:-1]))
    s = read_lin_file(os.path.join("Output Files",file_name))
    summarise_lin_file(s, summary_file)
    get_inter_urban_counts(summary_file,
                           os.path.join("Node Lookup Files", "tmfs_urban_areas.csv"),
                           urban_summary_file,
                           urban_services_file)
                    
if __name__ == "__main__":
    main()
