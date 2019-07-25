# CIF Import Script

import os
import os.path
import csv
import traceback
import sqlite3
from enum import Enum
from datetime import date, timedelta, datetime
#from textwrap import TextWrapper
from common_funcs import left, mid, process_lin

os.chdir(os.path.dirname(__file__))

#################### File Paths ####################

mypath=os.path.dirname(__file__)
input_folder = 'Inputs'
input_path = os.path.join(mypath, input_folder)

################### Assign output files and Databases #######



############### Declare dictionaries and variables #################
Dict_TIPLOC_SNames={}           # TIPLOC -> Station name
operator_index = 1              # Counter for Cube Voyager operator number
mode_index = 1                      # Counter for modes
operator_num_dict = {}          # Operator name -> Cube Voyager operator number
operator_name_dict = {}         #operator code to name
operator_mode_dict = {}         # Maps an operator -> a mode of transport e.g. "RAIL" or "BUS"
mode_num_dict = {}
line_num_dict = {}              # Route -> line number
junction_node = '888888'        # Cube node number assigned to junction stations
out_of_model = '999999'         # Cube node number assigned to stations not included in the Cube model


#################### Import Station Names ####################

# Main function to read MSN files that contains most station information
# Populates the relevant dictionary - Dict_TIPLOC_SNames
#
# args: msn_file     = MSN file location (to read)
#       station_output_path    = Station information file location (to write)
#       log             = Log from the GUI
#
def import_station_names(msn_file, station_output_path, log):

    try:
        with open(station_output_path, 'w') as myfile:
            pass
    except IOError:
        log.add_message("Failed to access Station output file\nCheck that it is not already open\n",color="RED")
        return

    with open(msn_file,'r') as T1_MSN:

        Stations_List = ['SName','TIPLOC','Alpha','Easting',\
                         'Northing','Data_Source']

        if station_output_path == "":
            station_output_path = "Stat_Name_Test_Dummy.csv"

        try:
            with open(station_output_path,'w',newline='') as myfile:

                wr=csv.writer(myfile)
                wr.writerow(Stations_List)
                for line in T1_MSN:
                    if left(line,1)=='A' and mid(line,30,9)!= 'FILE-SPEC':
                        SName=mid(line,5,30).strip()
                        TIPLOC=mid(line,36,7).strip()
                        Alpha=mid(line,49,3).strip()
                        Easting=mid(line,52,5).strip()
                        Northing=mid(line,58,5).strip()
                        Data_Source='MSN'

                        Dict_TIPLOC_SNames[TIPLOC]=SName
                        Stations_List=[SName,TIPLOC,Alpha,Easting,\
                                   Northing,Data_Source]
                        wr.writerow(Stations_List)

        except IOError:
            log.add_message(("Failed to access Station output file\n"
                             "Check that it is not already open\n"),color="RED")
            return

    log.add_message("Read MSN station names\n", color="GREEN")
    
def date_from_string(date_string):
    y, m, d = [int(date_string[i:i+2]) for i in range(0, len(date_string), 2)]
    if y == m == d == 99:
        return date(year=2099, month=1, day=1)
    y += 2000
    return date(year=y, month=m, day=d)

def dates_valid(check_dates, valid_dates):
    c = sorted(check_dates)
    v = sorted(valid_dates)
    if c[0] > v[1] or c[1] < v[0]:
        return False
    return True
    
def days_valid(check_days, valid_days):
    c = [int(x) for x in check_days]
    v = [int(x) for x in valid_days]
    for i in range(len(v)):
        if c[i] == v[i] == 1:
            return True 
    return False
    
def parse_fixed_line(line, key, lengths, use_columns=None, 
                     condition_index=None, condition=None):
    
    if condition_index is not None:
        if line[condition_index:condition_index+len(condition)] != condition:
            return [None for x in use_columns]
    split_line = []
    for col, length in zip(key, lengths):
        if col in use_columns:
            i = key.index(col)
            split_line.append(line[sum(lengths[:i]):sum(lengths[:i+1])])
    return split_line
    
def callback_parse_timetable(mca_path, station_lookup, day_filter, date_filter, 
                             cur, log, progress_bar, 
                             line_start=1, node_lookup=None):
    
    try:
        parse_timetable(mca_path, station_lookup, day_filter, date_filter, 
                        cur, log, progress_bar, line_start=line_start, node_lookup=node_lookup)
    except KeyError as k:
        log.add_message("Exception: %s" % k, color="RED")
        #widgets[1]["state"] = "normal"
        log.add_message("Traceback: %s" % "".join(traceback.format_tb(k.__traceback__)), color="RED")
    except Exception as e:
        log.add_message("Exception: %s" % e, color="RED")
        #widgets[1]["state"] = "normal"
        log.add_message("Traceback: %s" % "".join(traceback.format_tb(e.__traceback__)), color="RED")
    
def parse_timetable(mca_path, station_lookup, day_filter,
                    date_filter, cur, log, progress_bar,
                    line_start=1, node_lookup=None,
                    alternative_headway_rules=True):
    global operator_index, mode_index
    
    line_counter = line_start
    
    class stat(Enum):
        TIPLOC = 0
        ARRIVAL = 1
        DEPARTURE = 2
    
    ## Get the size of the MCA file (in lines) for the GUI ##
    filesize = 0
    with open(mca_path,'r') as T1_MCA:
        filesize = sum(1 for line in T1_MCA)
    #step_interval = filesize / 100
    counter = 0
    
    date_from = date(year=int(date_filter[0][2]), month=int(date_filter[0][1]), day=int(date_filter[0][0]))
    date_to = date(year=int(date_filter[1][2]), month=int(date_filter[1][1]), day=int(date_filter[1][0]))
    
    # Load MCA data 
    # Define the columns and lengths for all required row types -> LO, LI, LT, BS, BX
    bs_key = ["Identity", "Tran_type", "UID", "Date From", "Date To", "Days", 
              "Bank Hol", "Status", "Category", "Identity", "Headcode", 
              "Course", "Service Code", "Portion ID", "Power Type", 
              "Timing Load", "Speed", "Op Chars", "Class", "Sleepers", 
              "Reservations", "Connections", "Catering", "Brand", "Spare", "STP"]
    bs_lengths = [2,1,6,6,6,7,1,1,2,4,4,1,8,1,3,4,3,6,1,1,1,1,4,4,1,1]
    bs_use = ["UID", "Date From", "Date To", "Days", "Bank Hol"]
    
    bx_key = ["Identity", "Class", "UIC", "ATOC", "Timetable Code", "Reserved1", "Reserved2", "Spare"]
    bx_lengths = [2,4,5,2,1,8,1,57]
    bx_use = ["Identity", "ATOC"]
    
    lo_key = ["Identity", "TIPLOC", "Departure", "P Dep Time", "Platform", "Line", "Eng Allowance", "Activity", "Perf Allowance", "Spare"]
    lo_lengths = [2,8,5,4,3,3,2,2,12,2,37]
    lo_use = ["TIPLOC", "Departure"]
    
    li_key = ["Identity", "TIPLOC", "Arrival", "Departure", "Pass", "Platform", "Line", "Path", "Activity", "Eng Allowance", "Path Allowance", "Perf Allowance", "Spare"]
    li_lengths = [2,8,5,5,5,4,4,3,3,3,12,2,2,2,20]
    li_use = ["TIPLOC", "Arrival", "Departure", "Pass"]
    
    lt_key = ["Identity", "TIPLOC", "Arrival", "P Arrival", "Platform", "Path", "Activity", "Spare"]
    lt_lengths = [2,8,5,4,3,3,12,43]
    lt_use = ["TIPLOC", "Arrival"]
    
    # Get TIPLOC info 
    #ti_key = ["Identity", "TIPLOC", "Capitals", "Nalco", "NLC", "Description", "Stanox", "PO", "CRS", "Description2"]
    #ti_lengths = [2,7,2,6,1,26,5,4,3,16]
    #ti_use = ["TIPLOC", "Description", "CRS"]
    
    # Get Schedule data 
    with open(mca_path, "r") as file:
    
        basic_service = {} # UID -> [dates, days]
        service_details = {} # UID -> [[TIPLOC, Arrival, Departure]]
        UID = None
        LO = BX = LI = LT = None
    
        log.add_message("Reading From File")
    
        for line in file:
            
            counter += 1
            
            
            # If not within a service, look for BS lines to indicate start of service 
            if UID is None:
                UID, serv_date_from, serv_date_to, days, bank_hol = parse_fixed_line(
                        line, bs_key, bs_lengths, 
                        use_columns=bs_use, condition="BS", condition_index=0)
                if UID is None:
                    continue
                days = [day for day in days]
                
                # Check service is valid, if not set UID to none to look for the next one
                serv_date_from = date_from_string(serv_date_from)
                serv_date_to = date_from_string(serv_date_to)
                if dates_valid([serv_date_from, serv_date_to], 
                               [date_from, date_to]) == False:
                    UID = None 
                    continue
                if days_valid(days, day_filter) == False:
                    UID = None
                    continue
                
                
            # Look for the BX info 
            elif BX is None:
                BX, operator = parse_fixed_line(line, bx_key, bx_lengths, 
                                                use_columns=bx_use, 
                                                condition="BX", condition_index=0)
                basic_service[UID] = [serv_date_from, serv_date_to, 
                             "".join(days), operator, "rail"]
                # Add operator to operator list
                mode = "rail"
                if operator not in operator_name_dict:
                    operator_name_dict[operator] = operator
                if operator not in operator_num_dict:
                    operator_num_dict[operator] = str(operator_index)
                    operator_index += 1
                if operator not in operator_mode_dict:
                    operator_mode_dict[operator] = mode
                if mode not in mode_num_dict: #Check that the mode is not an unknown
                    print("Adding mode to lookup - %s as %s" % (mode, mode_index))
                    mode_num_dict[mode] = mode_index 
                    mode_index += 1
                 
            # Look for LO lines if not already found
            elif LO is None:
                LO, departure = parse_fixed_line(line, lo_key, lo_lengths, 
                                                 use_columns=lo_use, 
                                                 condition="LO", condition_index=0)
                if LO is None:
                    print("No LO ", line)
                    continue 
                service_details[UID] = [[LO.split()[0].strip(), None, departure[:4]]]
                    
            # Look for LT lines for terminal station 
            elif LT is None:
                LT, arrival = parse_fixed_line(line, lt_key, lt_lengths, 
                                               use_columns=lt_use, 
                                               condition="LT", condition_index=0)
                # End of service, reset the UID to look for new service
                if LT is not None:
                    progress_bar.step(1.0/filesize*100.0)
                    counter = 0
                    service_details[UID].append([LT.split()[0].strip(), arrival[:4], None])
                    UID = None
                    BX = None
                    LO = None
                    LT = None
                   
                # There are LI lines to read
                else:
                    LI, sub_arrival, sub_departure, sub_pass = parse_fixed_line(
                            line, li_key, li_lengths, use_columns=li_use, 
                            condition="LI", condition_index=0)
                    
                    # If the train just passes this is added in during patching
                    if LI is None:
                        # print(line)
                        continue
                    if sub_pass.strip() != "":
                        service_details[UID].append([LI.split()[0].strip(), 
                                       "-%s" % sub_pass.strip()[:4], None]) 
                        #service_details[UID].append([LI.strip(), "9999", "9999"]) 
                    else:
                        service_details[UID].append([LI.split()[0].strip(), 
                                       sub_arrival[:4], sub_departure[:4]])
                
    # All details read in 
    # Get mid times and node routes
    all_service = {}
    log.add_message("Processing required services") 
    
    for ID, service in service_details.items():
    
    
        start_time = service[0][stat.DEPARTURE.value][:2] + ":" +  service[0][stat.DEPARTURE.value][2:]
        end_time = service[-1][stat.ARRIVAL.value][:2] + ":" +  service[-1][stat.ARRIVAL.value][2:]
        diff = datetime.strptime(end_time, "%H:%M") - datetime.strptime(start_time, "%H:%M")
        mid_time = datetime.strptime(start_time, "%H:%M") + timedelta(seconds=diff.seconds/2)
        running_hour = mid_time.time().hour
        mid_time = mid_time.time().strftime("%H:%M")

        if alternative_headway_rules is True:
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
            # Specifically for TMfS, headway definitions are more complicated...
            #
            # - Service is defined as a certain headway, e.g. 7 - 10 am if:
            # - - Starts and ends within time frame
            # - - Starts 0.5 hours before end of time frame
            # - - Starts 0.5 hours before start of time frame and 
            #           mid time in time frame 
            # - - Non-scot start, 'starting' 0.5 hours after start of time frame
            #           and ending within time frame
            #
            # These will need to be determined at this point rather than after 
            #       reading in the data and using SQL
            # Headway definitions are hardcoded. Could be changed later...
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
            
            # Determine headways by moving 'running_hour' to be correct
            time_format = "%H:%M"
            headway_ranges = [
                [datetime.strptime("07:00", time_format) , datetime.strptime("10:00", time_format)],
                [datetime.strptime("10:00", time_format) , datetime.strptime("16:00", time_format)],
                [datetime.strptime("16:00", time_format) , datetime.strptime("19:00", time_format)]
                ]
            
            
            starts_outside_model = service[0][stat.TIPLOC.value] == "999999"
            ends_outside_model = service[-1][stat.TIPLOC.value] == "999999"
            # times_in_model = [start, mid, end]
            times_in_model = [arr.strip("-") if arr is not None 
                              else dep.strip("-") for stat, arr, dep 
                              in service if stat != "999999"]
            times_in_model = [datetime.strptime(times_in_model[0][:2] + ":" + times_in_model[0][2:], 
                                                time_format), 0, 
                            datetime.strptime(times_in_model[-1][:2] + ":" + times_in_model[-1][2:], 
                                              time_format)]
            times_in_model[1] = times_in_model[0] + timedelta(
                    seconds=(times_in_model[0] - times_in_model[2]).seconds/2)
            for h_start, h_end in headway_ranges:
                if (starts_outside_model is False 
                    and all(h_start <= time < h_end for time in times_in_model)):
                    running_hour = h_start.time().hour 
                    break
                elif (starts_outside_model is False 
                      and h_start <= times_in_model[0] < h_end - timedelta(minutes=30)):
                    running_hour = h_start.time().hour 
                    break 
                elif (starts_outside_model is False 
                      and (h_start - timedelta(minutes=30) <= times_in_model[0] < h_start)
                      and (h_start + timedelta(minutes=30) < times_in_model[1])):
                    running_hour = h_start.time().hour 
                    break 
                elif (starts_outside_model is True 
                      and h_start + timedelta(minutes=30) < times_in_model[1] < h_end):
                    running_hour = h_start.time().hour 
                    break
                else:
                    running_hour = 0
            print(times_in_model[0], times_in_model[1], running_hour)
            # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
        
        
        # Check if the service has any station within the network
        tiploc_list = [stop[stat.TIPLOC.value] for stop in service]
        if node_lookup is not None:
            node_list = [node_lookup.get(tiploc,"999999") for tiploc in tiploc_list]
        else:
            node_list = ["0" for tiploc in tiploc_list]
        if all(node == "999999" for node in node_list) is True:
            # Not within the network so can be ignored
            continue 
        # Format -> origin, destination, start date, end date, days, operator,  start time, end time, mid_time, hour, route, nodes
        passing_times = ",".join([str(stop[stat.DEPARTURE.value]) if 
                                  stop[stat.DEPARTURE.value] is not None else 
                                  stop[stat.ARRIVAL.value] for stop in service])
        tiploc_string = ",".join(tiploc_list)
        node_string = ",".join(node_list)
        #Generate the line name from the user starting number
        if line_num_dict.get(tiploc_string) is None:
            line_num_dict[tiploc_string] = line_start + line_counter
            line_counter += 1
        line_name = line_num_dict[tiploc_string]
        origin = station_lookup.get(service[0][stat.TIPLOC.value], 
                                    service[0][stat.TIPLOC.value])
        destination = station_lookup.get(service[-1][stat.TIPLOC.value], 
                                         service[-1][stat.TIPLOC.value])
        long_name = "%s - %s" % (origin, destination)
        all_service[ID] = ([origin, destination, long_name, line_name] + 
                   basic_service[ID] + 
                   [start_time, end_time, mid_time, running_hour, 
                    tiploc_string, node_string, passing_times])
                
    print(len(all_service))
    return all_service
    
def import_cif_callback(mca_path, station_path, node_lookup, operator_file, 
                        save_timetables_path, day_filter, date_filter, 
                        line_start, headway_defs, widgets):
    try:
        log = widgets[2]
        button = widgets[1]
        import_cif_data(mca_path, station_path, node_lookup, operator_file, 
                        save_timetables_path, day_filter, date_filter, 
                        line_start, headway_defs, widgets)
        button["state"] = "normal"
    except Exception as e:
        log.add_message("Exception: %s" % e, color="RED")
        button["state"] = "normal"
    
def import_cif_data(mca_path, station_path, node_lookup, operator_file, 
                    save_timetables_path, day_filter, date_filter, 
                    line_start, headway_defs, widgets):
    
    global operator_index, mode_index
    
    progress = widgets[0]
    button = widgets[1]
    progress_frame = progress.winfo_parent()
    progress_frame = progress._nametowidget(progress_frame)
    log = widgets[2]
    button['state'] = 'disabled'
    
    log.add_message("Importing CIF Data")

    headway_def = headway_defs[0].split(',')
    headway_names = headway_defs[1].split(',')
    headway_def = [int(x.strip(' ')) for x in headway_def]

    if len(headway_def) != len(headway_names)+1:
        log.add_message(("Headway period and name mismatch\nMust have 1 less "
                         "headway name than period"), color="RED")
        return
    for i in range(1,len(headway_def)):
        if headway_def[i] <= headway_def[i-1]:
            log.add_message("Headways given are invalid\n", color="RED")
            return
    
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(("CREATE TABLE IF NOT EXISTS services ("
                 "uniqueID, origin, destination, long_name, line, start_date, "
                 "end_date, days, operator, mode, departure_time, running_time, "
                 "mid_time, hour, route, nodes, pass_times)"))
    
    # Load node lookup into a dictionary
    with open(node_lookup, "r") as file:
        node_dict = {}
        reader = csv.DictReader(file)
        for row in reader:
            node_dict[row["TIPLOC"]] = row["Cube Node"]
            
    # Load station lookup into dictionary 
    with open(station_path, "r") as file:
        reader = csv.DictReader(file)
        station_dict = {row["TIPLOC"]: row["SName"] for row in reader}
            
    # Read mode lookup table 
    try:
        with open("mode_lookup.csv", "r") as lookup:
            reader = csv.reader(lookup)
            columns = next(reader)
            for row in reader:
                try:
                    mode_name, mode_num = row[0], row[1]
                except IndexError:
                    continue
                mode_num_dict[mode_name] = mode_num
            mode_index = max([int(x) for x in mode_num_dict.values()]) + 1
    except FileNotFoundError:
        with open("mode_lookup.csv", "w") as lookup:
            writer = csv.writer(lookup)
            writer.writerow(["Mode", "Num"])
            
    
    
    # Get the data from the CIF data
    data = parse_timetable(mca_path, station_dict, day_filter, date_filter, 
                           cur, log, progress, line_start=line_start, 
                           node_lookup=node_dict)
    num_entries = len(data)
    print(num_entries)
    try:
        print(list(data.items())[0])
    except IndexError:
        log.add_message("No services found in the simulation area for this date/day", color="RED")
        log.add_message("Check that the provided data contains relevant information", color="RED")
        button["state"] = "normal"
        return
    
    with open("Intermediate\\mca_out.csv", "w", newline="") as file:
        w = csv.writer(file)
        w.writerows([[k] + v for k, v in data.items()])
    
    cur.executemany(("INSERT INTO services (uniqueID, origin, destination, "
                     "long_name, line, start_date, end_date, days, operator, "
                     "mode, departure_time, running_time, mid_time, hour, "
                     "route, nodes, pass_times) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"), 
        [[k] + v for k, v in data.items()])
    
    #Write the operator dictionary to file, if it doesn't exist
    # Format
    # Mode(e.g. RAIL),Operator_Name,Operator_Number,operator long name
    print(operator_num_dict, operator_mode_dict, operator_name_dict)
    with open(operator_file, "a+",newline="") as file:
        file.seek(1)
        columns = "Mode,Code,Number,Name\n"
        if not file.read(1):
            file.write(columns)
            file.seek(0)
        reader = csv.reader(file)
        columns = next(reader)
        lines = []
        for row in reader:
            lines.append(row)
        operators_in_lookup = set()
        operator_nums_in_lookup = set()
        op_i = 1
        operators_to_append = []
        for line in lines:
            operators_in_lookup.add(line[1])
            operator_nums_in_lookup.add(line[2])
                
        for key in operator_name_dict:
            if key is None: continue
            if key not in operators_in_lookup:
                name = operator_name_dict.get(key)
                mode = operator_mode_dict.get(name)
                print(name, mode)
                if mode == None:
                    mode = "None"
                if operator_num_dict.get(key) == None:
                    operator_num_dict[key] = "1"
                while str(op_i) in operator_nums_in_lookup:
                    op_i += 1
                if operator_num_dict.get(key) not in operator_nums_in_lookup:
                    operators_to_append.append((mode.upper() + "," + key + 
                                                "," + operator_num_dict.get(key) + 
                                                "," + name))
                    operator_nums_in_lookup.add(operator_num_dict[key])
                else:
                    operators_to_append.append((mode.upper() + "," + key + 
                                                "," + str(op_i) + "," + name))
                    operator_nums_in_lookup.add(str(op_i))
                    op_i += 1
        for line in operators_to_append:
                file.write(line + '\n')

    # # Write mode lookup table ##
    with open("mode_lookup.csv", "w", newline="") as lookup:
        writer = csv.writer(lookup)
        writer.writerow(["Mode", "Num"])
        for key in mode_num_dict:
            writer.writerow([key, mode_num_dict[key]])
    
    # # Execute a SQL query to calculate headways and compress stops ##
    # # Includes: uniqueID, serv_code, TOC, TIPLOC, Times,
    # #       Headways, running_times, stat_seq, stat_seq_nodes

    print(headway_def, headway_names)

    h_periods = headway_def
    h_lengths = [int(h_periods[i]-h_periods[i-1])*60 for i in range(1, len(h_periods))]
    h_names = headway_names
    h_insert = "WHEN t.range='{0}' THEN CAST(ROUND(CAST({1} AS DOUBLE)) AS INT) "
    h_insert_2 = "WHEN hour BETWEEN {0} AND {1} THEN '{2}' "
    h_all_insert = ""
    h_all_insert_2 = ""
    for i in range(0,len(h_lengths)):
        h_all_insert += h_insert.format(h_names[i], h_lengths[i])
        h_all_insert_2 += h_insert_2.format(int(h_periods[i]), int(h_periods[i+1])-1, h_names[i])

    headway_query = '''CREATE TABLE all_serv AS
SELECT uniqueID, operator, long_name, line, GROUP_CONCAT(range) AS Times,
    GROUP_CONCAT(Headway) as Headways, pass_times, route, nodes
FROM (
    SELECT t.uniqueID, t.operator, t.origin, t.pass_times, t.range, COUNT(*) AS NumberOfServices,
            CASE ''' + h_all_insert + '''END/COUNT(*) AS Headway, t.route, t.nodes, t.long_name, t.line
    FROM (
            SELECT uniqueID, operator, origin, pass_times, CASE ''' + h_all_insert_2 + '''END AS range,
                    route, nodes, long_name, line
            FROM services) t
    GROUP BY t.route, t.range) AS Headways
WHERE (((Headways.[Headway]) Is Not Null))
GROUP BY route'''

    cur.execute(headway_query)

    ## Save to file so that post-processing functions can use it quickly ##
    columns = ['uniqueID', 'line', 'long_name','operator','Times','Headways','pass_times','route','nodes']
    columns = ["uniqueID", "operator", "long_name", "line", "times", "headways", "pass_times", "route", "nodes"]
    select_query = "SELECT * FROM all_serv"
    data=[x for x in cur.execute(select_query)]
    print(len(data))
    with open(save_timetables_path,'w',newline='') as file:
        writer=csv.writer(file)
        writer.writerow(columns)
        writer.writerows(data)
        
    log.add_message("Finished", color="GREEN")
    log.add_message("Found %d Entries" % num_entries)
    button['state'] = 'normal'
    


# Function that prints the Cube Voyager Line file
# args: infile          = File that contains the information to be written
#                               (output from import_timetable_info)
#       outlin          = Line file to write to
#       operator_lookup = Lookup file of operators to Cube operator numbers
#       log             = Log for the GUI
#
##################################################################################
def print_lin_file(infile, outlin, operator_lookup, headway_defs, log, 
                   rolling_stock_file=None, tiploc_lookup_file=None,
                   include_crowding=False, include_crush=False):

    log.add_message("Printing LIN File")

    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    num_dict = {}
    mode_dict = {} # Operator code to mode
    mode_num_dict = {} # Mode to mode number
    op_name_dict = {} # Operator Full name to code

    headway_names = [x.lstrip(' ') for x in headway_defs[1].split(',')]
    headway_periods = [int(x.lstrip(' ')) for x in headway_defs[0].split(',')]
    headway_lengths = [int(headway_periods[i]-headway_periods[i-1])*60 for i in range(1, len(headway_periods))]
    print(headway_lengths)

    with open(infile, "r") as db:
        reader = csv.reader(db)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        cur.execute(create_query)
        for data in reader:
            cur.execute(query, data)
    with open(operator_lookup, "r") as file:
        reader = csv.reader(file)
        _ = next(reader)
        lines = []
        for row in reader:
            lines.append(row)
        for line in lines:
            op_name_dict[line[3]] = line[1]
            num_dict[line[1]] = line[2]
            mode_dict[line[1]] = line[0]
                
    with open("mode_lookup.csv", "r") as file:
        reader = csv.reader(file)
        _ = next(reader)
        lines = []
        for row in reader:
            lines.append(row)
        for line in lines:
            mode_num_dict[line[0]] = line[1]
            
    try:
        with open(rolling_stock_file, "r") as lookup:
            r = csv.reader(lookup)
            stock_data = {(row[0].upper(), row[1].upper()):{} for row in r}
            for k in ["AM","IP","PM"]:
                for route in stock_data:
                    stock_data[route].setdefault(k,["999","999"])
            lookup.seek(0)
            for row in r:
                stock_data[(row[0].upper(), row[1].upper())][row[2]] = [row[3],row[4]]
            include_crowding, include_crush = True, True
    except:
        log.add_message("Could not find rolling stock data. Using default values")
        stock_data = {}
        include_crowding, include_crush = False, False
        
    try:
        with open(tiploc_lookup_file, "r") as lookup:
            r = csv.DictReader(lookup)
            tiploc_lookup = {row["NAME"].upper():row["TIPLOC"].upper() for row
                             in r}
        print(tiploc_lookup)
    except FileNotFoundError:
        log.add_message("Could not find tiploc lookup file %s" % tiploc_lookup_file)
        stock_data = {}
        include_crowding, include_crush = False, False
            
    # Print Cube PTS file 
    with open("Output Files\\rail_op_mode_definitions.PTS", "w") as file:
        file.write(";;<<PT>><<SYSTEM>>;;\n")
        file.write(";Mode List\n")
        file.write(";Operator List\n")
        # Wait curve/Crowd model curve/Vehicle Types
        
        for name, num in mode_num_dict.items():
            print(name, num)
            file.write("""MODE NUMBER=%s LONGNAME="%s" NAME="%s"\n""" % (num, name.capitalize(), name[:3].upper()))
            
        for name, code in op_name_dict.items():
            num = num_dict[code]
            file.write("""OPERATOR NUMBER=%s LONGNAME="%s" NAME="%s"\n""" % (num, name, code))
            
        file.write("""WAITCRVDEF NUMBER=1 LONGNAME="Wait Curve 1 - Non-London Inter Urban" NAME="WC1" ,
           CURVE=5-5,10-10,15-14,20-18,
           30-23,40-26,60-31,90-39,
           120-47,180-63
           """)
        if include_crowding is True:
            file.write("""CROWDCRVDEF NUMBER=1 NAME="Crowd Curve " ,
            CURVE=0-1,20-1.09,40-1.18,60-1.26,
            80-1.35,100-1.44""")

    with open(outlin, "w", newline='') as file:
        log.add_message("Writing line file\n")

        file.write(";;<<PT>><<LINE>>;;\n")
        
        # Separate files if including rolling stock/crush
        for k in ["AM", "IP", "PM"]:
            with open(outlin.upper().replace(".LIN", "_%s.LIN" % k), "w") as p_file:
                p_file.write(";;<<PT>><<LINE>>;;\n")
                
        # Keep track of any missing data for the rolling stock
        missing_rolling_stock = {"AM":0, "IP":0, "PM":0}
        
        # Combine similar routes
        # new headways split by headway - 1, 2, 3 = 60, 60, 60
        # combine by [60, 60, 60] + [180, 180, 180] => 180/60 + 180/180 = 4 => 180 / 4 = 45
        
        cur.execute("SELECT line, long_name, operator, Times, Headways, pass_times, route, nodes FROM all_serv")
        service_dict = {}
        for row in cur.fetchall():
            key = row[1] + " - " + row[7]
            service_dict.setdefault(key, [])
            service_dict[key].append(row)
        
        condensed_services = []
        for k, v in service_dict.items():
            if len(v) > 1:
                headways = {}
                for service in v:
                    for time, headway in zip(service[3].split(","), service[4].split(",")):
                        time = time.strip()
                        headway = headway.strip()
                        headways.setdefault(time, [])
                        headways[time].append(int(headway))
                for time, headway_list in headways.items():
                    headway_length = headway_lengths[int(time) - 1]
                    headways[time] = round(headway_length / (sum([headway_length / x for x in headway_list])))
                    
                new_service = list(v[0])
                new_service[3] = ",".join(str(x) for x in headways.keys())
                new_service[4] = ",".join(str(x) for x in headways.values())
            else:
                new_service = v[0]
            condensed_services.append(new_service)
        
        cur.execute("CREATE TABLE IF NOT EXISTS all_serv_condensed (line, long_name, operator, Times, Headways, pass_times, route, nodes) ")
        cur.executemany("INSERT INTO all_serv_condensed (line, long_name, operator, Times, Headways, pass_times, route, nodes) VALUES (?,?,?,?,?,?,?,?)", condensed_services)
        
        cur.execute("SELECT line, long_name, operator, Times, Headways, pass_times, route, nodes FROM all_serv_condensed")
        #wrapper = TextWrapper(70)
        rows = cur.fetchall()
        # Generate new line names for each service
        current_line = 1
        for row in sorted(rows,key=lambda x:x[1]):
            circ = "F"
            mode_num = mode_num_dict["rail"]
            if row[4] == True:
                circ = "T"
            result = 'LINE NAME="r' + str(current_line) + '", ' + '\nLONGNAME="' + row[1] + '", ' + 'MODE=' + mode_num + \
                     ', OPERATOR=' + num_dict[row[2]] + ', '
            current_line += 1
            result += 'ONEWAY=T, CIRCULAR=F, '
            times = [x.strip(' ') for x in row[3].split(',')]
            headways = [x.strip(' ') for x in row[4].split(',')]
            format_head = [str(0) for x in range(0,len(headway_names))]
            h_query = ""
            #r_labels = ["AM","Mid","PM"]
            if include_crush is True:
                # Fill in blank headways
                for h in times:
                    index = headway_names.index(h)
                    format_head[index] = str(headways[times.index(h)])
                    
                period_head = {"AM":None,"IP":None,"PM":None}
                period_head["AM"], period_head["IP"], period_head["PM"] = [
                        int(head) for head in format_head]
                period_result = {"AM":None,"IP":None,"PM":None}
                period_result["AM"], period_result["IP"], period_result["PM"] = [
                        "HEADWAY[%s]=%s, " % (i+1, head) for i, head 
                              in enumerate(format_head)]
                
                origin, destination = [x.strip() for x in row[1].split("-")[:2]]
#                origin = tiploc_lookup.get(origin.strip())
#                destination = tiploc_lookup.get(destination.strip())
                for k in period_result:
                    period_result[k] += ("CROWDCURVE[1]=1, CROWDCURVE[2]=1, "
                                       "CROWDCURVE[3]=1, CROWDCURVE[4]=1, "
                                       "CROWDCURVE[5]=1, ")
                    # If there is no data use default of 999
                    seat_cap, crush_cap = stock_data.get(
                            (origin, destination),{}).get(k, ["999","999"])
                    # Try the other time periods
                    if seat_cap == "999" and crush_cap == "999":
                        trial_k = ["PM","AM","AM"][["AM","IP","PM"].index(k)]
                        seat_cap, crush_cap = stock_data.get(
                            (origin, destination),{}).get(trial_k, ["999","999"])
                    if seat_cap == "999" and crush_cap == "999":
                        trial_k = ["IP","PM","IP"][["AM","IP","PM"].index(k)]
                        seat_cap, crush_cap = stock_data.get(
                            (origin, destination),{}).get(trial_k, ["999","999"])
                        
                    period_result[k] += "SEATCAP=%s, CRUSHCAP=%s, " % (
                            seat_cap, crush_cap)
                    if seat_cap == "999" and period_head[k] != 0:
                        missing_rolling_stock[k] += 1
                
                    period_result[k] += "LOADDISTFAC=100, "
                    period_result[k] += 'CROWDCURVE[1]=1, '
            for h in times:
                index = headway_names.index(h)
                format_head[index] = str(headways[times.index(h)])
            for i in range(0,len(format_head)):
                h_query += "HEADWAY[{0}]={1}, ".format(headway_names[i], format_head[i])
            all_result = h_query
            if include_crowding is True:
                all_result += 'CROWDCURVE[1]=1, CROWDCURVE[2]=1, CROWDCURVE[3]=1, CROWDCURVE[4]=1, CROWDCURVE[5]=1, '
            all_result += 'SEATCAP=999, CRUSHCAP=999, LOADDISTFAC=100, '
            if include_crowding is True:
                all_result += 'CROWDCURVE[1]=1, '

            def last_valid_time(times, index):
                for value in reversed(times[:index]):
                    if value[0] != "-":
                        return value[:2] + ":" + value[2:]
                # If no valid get the first time and remove the "-"
                return value[1:3] + ":" + value[3:]
            
            pass_list = row[5].split(",")
            pass_times = [x[:2] + ":" + x[2:] if x[0] != "-" else last_valid_time(pass_list, i) for i, x in enumerate(pass_list)]
            pass_times = [datetime.strptime(x, "%H:%M") for x in pass_times]
            
            running_times = [(x - pass_times[0]).seconds / 60 if i > 0 else 0 for i, x in enumerate(pass_times)]
            route = [x for x in row[6].split(',')]
            nodes = [x for x in row[7].split(',')]
            # If the service only has fewer than n nodes, ignore it 
            min_nodes = 2
            if len(nodes) < min_nodes:
                continue
            # # # # # # # 
            
            line_n_rt = []
            after_stop = True
            
            for i, node in enumerate(nodes):
                if after_stop is True:
                    line_n_rt.append("N=" + node)
                    after_stop = False
                else:
                    line_n_rt.append(node)
                if node[0] != "-" and i > 0:
                    line_n_rt.append("RT=" + str(int(running_times[i])))
                    after_stop = True
            
            # for node in n:
                # if after_stop:
                    # line_n_rt.append("N=" + node)
                    # after_stop = False
                # else:
                    # line_n_rt.append(node)
                # if node in n_rt and n.index(node) > 0:
                    # line_n_rt.append("RT=" + rt[n_rt.index(node)])
                    # after_stop = True
            line_n_rt = ", ".join(line_n_rt)

            if include_crush is True:
                for k, headways in period_result.items():
                    
                    # Skip if no service in the period
                    if period_head[k] == 0:
                        continue
                    
                    period_res = result + headways + line_n_rt
                    period_res = process_lin(period_res, width=70)
                    with open(outlin.upper().replace(".LIN", "_%s.LIN" % k.upper()), 
                              "a", newline="") as ind_file:
                        #ind_file.write(";;<<PT>><<LINE>>;;\n")
                        ind_file.write(period_res)
                        ind_file.write("\n\n")
                     
            result += all_result
            result += line_n_rt
            result = process_lin(result, width=70)
            file.write(result)
            file.write('\n\n')
    log.add_message("Finished Printing LIN File", color="GREEN")
    log.add_message("%d services used" % len(condensed_services), color="GREEN")
    log.add_message("Missing rolling stock: AM = %d, IP = %d, PM = %d" % (
            missing_rolling_stock["AM"], missing_rolling_stock["IP"], missing_rolling_stock["PM"]))
    conn.close()


# Filter out any services by operator or operating period
#Produces file of all unique links in the services
def CIF_post_filter(period, infile, outfile, outlinfile, op_list, operator_lookup, log):

    log.add_message("Filtering operators and operating period\n")

    op_nums = [x for x in op_list]

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    with open(infile, "r") as db:
        reader = csv.reader(db)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        c.execute(create_query)
        for data in reader:
            c.execute(query, data)
        query = "SELECT * FROM all_serv WHERE operator IN (" + ','.join('?' * len(op_nums)) + ")"
        filtered_data = c.execute(query, op_nums)

        try:
            with open(outfile, "w", newline="") as out:
                rows = filtered_data.fetchall()
                writer = csv.writer(out)
                writer.writerow(columns)
                writer.writerows(rows)
        except IOError:
            log.add_message("Failed to access Station output file\nCheck that it is not already open\n", color="RED")
            return

    conn.close()

    log.add_message("Finished Filtering", color="GREEN")


# Create a file containing all unique 2 node sequences for patching later
def CIF_get_links(infile, outfile, log):

    log.add_message("Generating all node links\n")

    #Nodes are the final column stored in the file
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    with open(infile, "r") as db:
        reader = csv.reader(db)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        c.execute(create_query)
        for data in reader:
            c.execute(query, data)
        query = "SELECT stat_seq_nodes FROM all_serv"
        c.execute(query)
        nodes = c.fetchall()
        links = set()

        for sequence in nodes:
            sequence = sequence[0].split(', ')
            for i in range(0, len(sequence)-1):
                links.add((sequence[i].lstrip(), sequence[i+1].lstrip()))

        try:
            with open(outfile, "w", newline="") as out:
                writer = csv.writer(out)
                writer.writerows(links)
        except IOError:
            log.add_message("Failed to access Station output file\nCheck that it is not already open\n")
            return
    conn.close()

    log.add_message("Finished Generating Links\n", color="GREEN")
