from datetime import date, timedelta, datetime
import os
import csv
import sqlite3
#from textwrap import TextWrapper
import traceback
from common_funcs import process_lin

current_dir = os.path.dirname(__file__)
outfile = os.path.join("Intermediate", "individual_routes.csv")
all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday","HolsOnly"]

num_entries = 0

ns = {'ns' : 'http://www.transxchange.org.uk/'}

#Import stop points

stop_dict = {}          #takes the StopPointRef and gives CommonName
journey_dict = {}       #takes JourneyId and gives a list of the route including running time
service_dict = {}       #takes ServiceCode and gives a list of LineName, Operator, StartDate, EndDate, Description
pattern_ref_dict = {}   #takes PatternRef and gives the day of travel and departure time
operator_name_dict = {} #operator code to name
operator_mode_dict = {} # Operator name -> Mode
mode_num_dict = {}
operator_num_dict = {}  #operator name to cube number
running_times = {}
flagged_routes = {}
operator_index = 1
mode_index = 1
test_stops = []
test_times = []

class ColumnNotFoundError(Exception):
    def __init__(self, file, column):
        super(ColumnNotFoundError, self).__init__("%s not found in %s" % (column, file))
        self.column = column 
        self.file = file

class NotInNetworkError(Exception):
    def __init__(self):
        super(NotInNetworkError, self).__init__()

class time_entry:
    def __init__(self, pattern):
        self.pattern = pattern
        self.date_dict = {}
    def add_time(self, day, time):
        self.date_dict.setdefault(day, [])
        self.date_dict[day].append(time)


class DateEntry:
    def __init__(self, d=None):
        if d is None:
            # If no date values are passed, assume earliest date allowed
            self.date = date.min
        else:
            self.date = date(year=int(d[2]), month=int(d[1]), day=int(d[0]))

    def within_range(self, start, end):
        if not type(start) == DateEntry and type(end) == DateEntry:
            raise TypeError('start and end variables must be of type DateEntry')
        return start.date < self.date < end.date
        

########## Currently ignores the fact that some services will run into the next day #######################
##### The table of all stops is generated each time that data is read... #####
#####

def write_csv(headers, data, csvfile):

    with open(csvfile, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)

def find_mid(start, running):   #start = [h,m,s], running = s
    interval = [86400, 3600, 60, 1]
    start = [start[x-1] * interval[x] for x in range(1, 4)]
    half = running // 2 + sum(start)
    mid = [0, 0, 0, 0]
    for i in range(0, len(interval)):
        mid[i] = half // interval[i]
        if mid[i] > 0:
            half -= mid[i] * interval[i]
    if mid[0] > 0:
        print("Possible error: Running time goes over 1 day")
    return mid[1:]
    
def make_list(variable):
    if type(variable) == list:
        return variable 
    else:
        return [variable]
        
def date_from_string(date_string, default="1990-01-01"):
    if date_string == None:
        date_string = default
    if date_string == "Not Present":
        return None
    dt = date_string.split('-')
    y = int(dt[0])
    m = int(dt[1])
    d = int(dt[2])
    return date(y, m, d)
    
def days_valid(check_days, valid_days):
    # check_days will sometimes be dummy value if 
    #   the service is only on holidays
    if check_days is None:
        return False
    for day in check_days:
        if day in valid_days:
            return True 
    return False
    
def dates_valid(check_dates, valid_dates):
    c = sorted(check_dates)
    v = sorted(valid_dates)
    if c[0] > v[1] or c[1] < v[0]:
        return False
    return True
    
def timing_to_seconds(timing):
    unit = timing[-1]
    time = int(timing[2:-1])
    in_seconds = time * [1, 60, 3600][["S","M","H"].index(unit)]
    return in_seconds
    
def get_headway_period(test, headways=[7,10,16,19]):
    for i in range(len(headways) - 1):
        if test < headways[i]:
            return None
        elif test < headways[i+1]:
            return i
            
def average_running_time(times, round_places=2):
    if len(times) < 1:
        return 0
    if round_places == 0:
        return int(sum(times)/len(times))
    else:
        return round(sum(times)/len(times), round_places)
    
    
def summarize(excel_output_file):
    
    """
    Creates a summary excel file of the routes extracted from TransXChange data
    """
    
    import pandas as pd
    
    df = pd.read_csv("Intermediate\\individual_routes.csv")
    n = pd.read_csv("Node Lookup Files/tmfs_naptan_to_local_authority.csv")
    n = n.fillna("External")    
    n.columns = ["ATCOCode", "LA"]
    
    df = df.loc[df.Mode.isin(["coach", "bus"])]
    df["Origin"] = df.Route.str.split(",").apply(lambda x:x[0])
    df["Destination"] = df.Route.str.split(",").apply(lambda x:x[-1])
    df = df.merge(n, left_on="Origin", right_on="ATCOCode", how="left").drop("ATCOCode", axis=1)
    df["Origin"] = df.LA.fillna("Unknown")
    df.drop("LA", axis=1, inplace=True)
    df = df.merge(n, left_on="Destination", right_on="ATCOCode", how="left").drop("ATCOCode", axis=1)
    df["Destination"] = df.LA.fillna("Unknown")
    df.drop("LA", axis=1, inplace=True)
    
    g1 = df.groupby(["LongName", "LineName", "Operator", 
                     "Origin", "Destination", "Hour"])["RunningTime"].count()
    
    g2 = df.groupby(["Origin", "Destination", "Operator", "Hour"])["RunningTime"].count()
    
    df = df[["Operator", "LineName", "LongName", "Origin", "Destination", "Hour"]]
    
    with pd.ExcelWriter(excel_output_file) as writer:
        g2.to_excel(writer, sheet_name="LA Counts")
        df.to_excel(writer, sheet_name="Base Data")
        g1.to_excel(writer, sheet_name="Service Counts")
    
# # Provide:
#    filename = Name of XML file 
#    op_list = list of operators (SS)
#    day_filter = list of days of the week to include 
#    date_filter = list of two dates that define the range to look for 
#    cur = sql cursor (SS)
#    sim_node_lookup = dictionary of ATCO to node (simulation network only)
#    node_lookup = dictionary of ATCO to node (entire network)
#    model_timings = set True to use the timings only when the service is within the model area
# # 
    
def get_services(filename, day_filter, date_filter, headways, 
                 sim_node_lookup=None, node_lookup=None, model_timings=True,
                 discard_non_headways=True):
    """Get all relevant services within an XML TransXChange file.
    
    Parameters
    ----------
    filename : str
        The XML file.
    day_filter : list
        Days of the week to use.
    date_filter : list
        Start and end dates of the period to look at.
    headways : tuple
        Headway period names and definitions
    sim_node_lookup : dict, optional
        ATCO->Node dictionary (simulation nodes only)
    node_lookup : dict, optional
        ATCO->Node dictionary (all nodes)
    model_timings : bool, optional
        Calculate running times when inside the model area (default True)
    discard_non_headways : bool, optional
        Controls whether the services outside of the headway periods are discarded
        
    Returns
    -------
    dict
        Filtered data dictionary
    """

    global num_entries, operator_index, operator_name_dict, mode_index

    try:
        import xmltodict as x2d
    except ImportError:
        print("Could not import module xmltodict")
        print("This is required for processing TransXChange data")
        return
    
    headway_names, headway_periods = headways
    
    date_from = date(year=int(date_filter[0][2]), month=int(date_filter[0][1]), 
                     day=int(date_filter[0][0]))
    date_to = date(year=int(date_filter[1][2]), month=int(date_filter[1][1]), 
                   day=int(date_filter[1][0]))
    
    with open(filename, "r") as file:
        xml_text = ""
        for line in file:
            xml_text += line 
    xml = x2d.parse(xml_text)["TransXChange"]
    
    # List of stop points, services, journey sections, journeys, operators
    points = make_list(xml["StopPoints"]["AnnotatedStopPointRef"])#List
    services = make_list(xml["Services"]["Service"]) #List
    j_sections = make_list(xml["JourneyPatternSections"]["JourneyPatternSection"]) #List
    journeys = make_list(xml["VehicleJourneys"]["VehicleJourney"]) # List
    operators = make_list(xml["Operators"]["Operator"]) # Dict?
    
    xml = None
    
    # Dictionary of stop point ref to common name
    stop_dict = {list(x.values())[0]:list(x.values())[1] for x in points}
    
    # Check if all stops are outside of the simulation network 
    # Assigns '-1' if the stop is not included in the network
    nodes = [sim_node_lookup.get(stop, "-1") for stop in stop_dict]
    if all(x == "0" or x == "-1" for x in nodes) == True:
        raise NotInNetworkError
        return []
    
    # Dictionary of journey id to route and timings
    j_pattern_dict = {j["@id"]:[
            [x["From"]["StopPointRef"], x["To"]["StopPointRef"], x["RunTime"]] for x 
            in make_list(j["JourneyPatternTimingLink"])] for j in j_sections}
    # Dictionary of operator ids to names
    operator_dict = {o["@id"]:o["OperatorShortName"] for o in operators}
    # Dictionary of service code to Origin and Destination
    od_dict = {s["ServiceCode"]:[
            s["StandardService"]["Origin"], 
            s["StandardService"]["Destination"]
            ] for s in services}
    # Dictionary of service code to journey pattern id to inbound/outbound
    dir_dict = {s["ServiceCode"]:{jp["@id"]:jp["Direction"] for jp 
                in make_list(s["StandardService"]["JourneyPattern"])} for s in services}
    # Dictionary of service id to service details 
    s_dict = {s["ServiceCode"]:[
            s["Lines"]["Line"]["LineName"], 
            operator_dict[s["RegisteredOperatorRef"]],
            date_from_string(s["OperatingPeriod"].get("StartDate"), default="1990-01-01"),
            date_from_string(s["OperatingPeriod"].get("EndDate"), default="2090-01-01"),
            s["Description"],
            s["Mode"]
            ] for s in services if 
                dates_valid([
                        date_from_string(s["OperatingPeriod"].get("StartDate"), default="1990-01-01"),
                        date_from_string(s["OperatingPeriod"].get("EndDate"), default="2090-01-01")
                        ], [date_from, date_to]) == True}
    # Dictionary of journeys codes to service, pattern, operating days, departure time, valid_days(bool)
    j_dict = {j["VehicleJourneyCode"]:[
            j["ServiceRef"], 
            j["JourneyPatternRef"], 
            list(j["OperatingProfile"]["RegularDayType"].get("DaysOfWeek",{None:None}).keys()), 
            j["DepartureTime"]
            ] for j in journeys if 
                days_valid(list(
                        j["OperatingProfile"]["RegularDayType"].get(
                                "DaysOfWeek", {None:None}).keys()), day_filter) == True}
    # Dictionary of journey codes to non-operating days
    noop_dict = {j["VehicleJourneyCode"]:[
            [date_from_string(d.get("StartDate","Not Present")),
             date_from_string(d.get("EndDate","Not Present"))
             ] for d in make_list(j.get(
                    "OperatingProfile",{}).get(
                            "SpecialDaysOperation",{}).get(
                                    "DaysOfNonOperation",{}).get(
                                            "DateRange",{}))] for j in journeys if 
                days_valid(list(j["OperatingProfile"]["RegularDayType"].get(
                        "DaysOfWeek",{None:None}).keys()), day_filter) == True}
    
    points = None 
    services = None 
    journeys = None 
    operators = None
    
    operator_name_dict = dict(list(operator_dict.items()) + list(operator_name_dict.items()))
    
    service_details = []
    
    for k, j in j_dict.items():
        
        # Get all the details for the journey
        s_ref, pat_ref, running_days, dep_time = j[0], j[1], j[2], j[3]
        # service_id, journey_pattern_id, days_of_operation, departure_time
        noop_ranges = noop_dict[k] # Start and end of non-operating period (not always present)
        
            
        route_details = j_pattern_dict[pat_ref]# [[stop1, stop2, time],[stop2, stop3, time], ...]
        try:
            line, operator, desc, mode = s_dict[s_ref][0], s_dict[s_ref][1], s_dict[s_ref][4], s_dict[s_ref][5]
            # line_name, operator, service_description, mode_of_travel
        except KeyError:
            # Key error raised if the service should be skipped the service should be skipped 
            continue
        origin, destination = od_dict[s_ref]# origin_stop, destination_stop
        direction = dir_dict[s_ref][pat_ref]# 'inbound' or 'outbound'
        running_days_string = ','.join(running_days)

        # If not operating, skip this journey
        is_operating = True
        for noop_start, noop_end in noop_ranges:
            if noop_start is not None and noop_end is not None:
                if noop_start <= date_from <= noop_end:
                    is_operating = False
                    print(s_ref, " is caught by non-working range")
                    print(noop_start.strftime("%d/%m/%Y"), 
                          date_from.strftime("%d/%m/%Y"), 
                          noop_end.strftime("%d/%m/%Y"))
        if is_operating is False:
            continue
                
        # Add operator to operator list
        if operator not in operator_num_dict:
            operator_num_dict[operator] = str(operator_index)
            operator_index += 1
        if operator not in operator_mode_dict:
            operator_mode_dict[operator] = mode
        if mode not in mode_num_dict: #Check that the mode is not an unknown
            print("Adding mode to lookup - %s as %s" % (mode, mode_index))
            mode_num_dict[mode] = mode_index 
            mode_index += 1
            
        # Get list of stops and check if circular
        stops_a = [[x[0],x[1]] for x in route_details]
        stops_duplicates = []
        for s in stops_a:
            stops_duplicates.extend(s)
        stops = [x for i, x in enumerate(stops_duplicates) if i == 0 or x != stops_duplicates[i-1]]
        if direction == "inbound": pass
            # stops.reverse()
        elif direction == "outbound": pass
        else:
            print("Direction is not inbound or outbound")
        route_string = ','.join(stops)
        circular = stops[0] == stops[-1]
        
        # Get running time in seconds
        timings = [timing_to_seconds(x[2]) for x in route_details]
        running_time = sum(timings)
        
        # If no lookup provided set nodes to '0'
        if node_lookup == None:
            nodes = ["0" for x in stops]
        # Get the relevant node, flag the stop if no node is available
        # Use the entire network (including buffer)
        else:
            nodes = [node_lookup.get(stop, "-1") for stop in stops]
        if all(x == "-1" for x in nodes) == True:
            continue
        node_string = ','.join(nodes)
        
        time_format = "%H:%M:%S"
        
        # Pad the timings array with a leading 0
        # Get the indices that the service is within the network
        timings = [0] + timings
        for first_node, x in enumerate(nodes):
            if x != "-1":
                break 
        for last_node, x in enumerate(reversed(nodes)):
            if x != "-1":
                break
        last_node = len(nodes) - last_node
        # Get the running times according to the model 
        if last_node == len(nodes):
            model_running_time = sum(timings[first_node:])
        else:
            model_running_time = sum(timings[first_node:last_node])
        model_start_time = datetime.strptime(dep_time, time_format) + timedelta(seconds=sum(timings[:first_node]))
        model_mid_time = model_start_time + timedelta(seconds=model_running_time/2)
        model_running_hour = model_mid_time.hour 
        model_mid_time = model_mid_time.strftime(time_format)
        # # # # # # # #
        
        # Get the midpoint of the service 
        # If using the model timings (from function call), do not calculate again
        if model_timings is True:
            mid_time = model_mid_time 
            running_hour = model_running_hour 
        else:
            mid_time = datetime.strptime(dep_time, time_format) + timedelta(seconds=running_time/2)
            running_hour = mid_time.hour
            mid_time = mid_time.strftime(time_format)
        # Classify the service as AM, IP, PM
        # This assumes that only 3 periods are being used
        # Could be made more general
        
        
        headway_index = get_headway_period(running_hour, headway_periods)
        # Use to filter headways not in the model periods
        if discard_non_headways:
            headway_index = 0
        if headway_index is None:
            continue
        running_times.setdefault(line, {})
        running_times[line].setdefault(operator, {"AM":[], "IP":[], "PM":[]})
        period = ["AM", "IP", "PM"][headway_index]
        running_times[line][operator][period].append(running_time)
        
        # Get running times for am, ip, pm
        running_time_period = [0, 0, 0]
        running_time_period[headway_index] = running_time
        am_time, ip_time, pm_time = running_time_period
        
        # Name the service using origin and destination 
        if direction == "outbound":
            name = "%s - %s" % (origin, destination)
        else:
            name = "%s - %s" % (destination, origin)
        
        line = [s_ref, name, line, circular, direction, operator, mode, running_days_string,
            dep_time, running_time, mid_time, running_hour, pat_ref, route_string, node_string,
            am_time, ip_time, pm_time]
        service_details.append(line)
            
        num_entries += 1
            
    
    return service_details
        

def print_lin_file(infile, outlin, operator_lookup, headway_defs, log):
    """Print a formatted Cube Voyager Bus line file
    
    Parameters
    ----------
    infile : str
        CSV file containing the line data
    outlin : str
        Line file save path
    operator_lookup : str
        Path to operator lookup CSV
    headway_defs : tuple
        Headway period names and definitions
    log : tkinter widget
        Widget with a add_message method
    """

    log.add_message("Printing LIN File")

    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    num_dict = {} # Operator code to number
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
            
    # Print Cube PTS file 
    with open("Output Files\\bus_op_mode_definitions.PTS", "w") as file:
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
            
    # Combine similar routes
        # new headways split by headway - 1, 2, 3 = 60, 60, 60
        # combine by [60, 60, 60] + [180, 180, 180] => 180/60 + 180/180 = 4 => 180 / 4 = 45
        
        cur.execute(("SELECT Line_Name, Long_Name, Mode, Operator, Circular, "
                     "Times, Headways, Nodes, am_rt, ip_rt, pm_rt FROM all_serv"))
        service_dict = {}
        for row in cur.fetchall():
            key = row[1][:-1] + " - " + row[7]
            service_dict.setdefault(key, [])
            service_dict[key].append(row)
        
        condensed_services = []
        for k, v in service_dict.items():
            if len(v) > 1:
                am_count = ip_count = pm_count = 0
                am_tot = ip_tot = pm_tot = 0.0
                print(k, len(v))
                headways = {}
                for service in v:
                    for time, headway in zip(service[5].split(","), service[6].split(",")):
                        time = time.strip()
                        headway = headway.strip()
                        headways.setdefault(time, [])
                        headways[time].append(int(headway))
                        
                    if service[8] != "":
                        am_tot += int(float(service[8]))
                        am_count += 1
                    if service[9] != "":
                        ip_tot += int(float(service[9]))
                        ip_count += 1
                    if service[10] != "":
                        pm_tot += int(float(service[10]))
                        pm_count += 1
                        
                for time, headway_list in headways.items():
                    headway_length = headway_lengths[int(time) - 1]
                    headways[time] = round(headway_length / (sum([headway_length / x for x in headway_list])))
                    
                new_service = list(v[0])
                new_service[5] = ",".join(str(x) for x in headways.keys())
                new_service[6] = ",".join(str(x) for x in headways.values())
                try:
                    new_service[8] = am_tot / am_count
                except:
                    new_service[8] = 0.0
                try:
                    new_service[9] = ip_tot / ip_count
                except:
                    new_service[9] = 0.0
                try:
                    new_service[10] = pm_tot / pm_count
                except:
                    new_service[10] = 0.0
            else:
                new_service = v[0]
            condensed_services.append(new_service)
        
        cur.execute(("CREATE TABLE IF NOT EXISTS all_serv_condensed "
                     "(Line_Name, Long_Name, Mode, Operator, Circular, "
                     "Times, Headways, Nodes, am_rt, ip_rt, pm_rt) "))
        cur.executemany(("INSERT INTO all_serv_condensed "
                         "(Line_Name, Long_Name, Mode, Operator, Circular, "
                         "Times, Headways, Nodes, am_rt, ip_rt, pm_rt) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?)"), condensed_services)
        
    with open("headways_running_times.csv", "w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["Operator", "Line", "AM(m)", "IP(m)", "PM(m)"])
        cur.execute("SELECT Operator, Line_Name, am_rt, ip_rt, pm_rt FROM all_serv_condensed")
        data = cur.fetchall()
        w.writerows(data)
    
    with open(outlin, "w", newline='') as file:
        log.add_message("Writing line file\n")
        file.write(";;<<PT>><<LINE>>;;\n")
        cur.execute(("SELECT Line_Name, Long_Name, Mode, Operator, "
                     "Circular, Times, Headways, Nodes FROM all_serv_condensed"))
        rows = cur.fetchall()
        for row in sorted(rows, key=lambda x:x[0]):
            circ = "F"
            if str(row[4]) == "1":
                circ = "T"
            op_code = op_name_dict[row[3]] # Get op code
            op_num = num_dict.get(op_code) # get op num
            mode_name = mode_dict.get(op_code).lower() # get mode name
            mode = mode_num_dict.get(mode_name) # get mode num
            result = ('LINE NAME="' + row[0] + '", ' + 'LONGNAME="' + 
                      row[1] + '", ' + 'ALLSTOPS=F, MODE=' + mode + 
                      ', OPERATOR=' + op_num + ', ')
            # result += 'ONEWAY=T, CIRCULAR=' + circ + ', '
            result += 'ONEWAY=T, CIRCULAR=F, '
            times = [x.strip(' ') for x in row[5].split(',')]
            headways = [x.strip(' ') for x in row[6].split(',')]
            format_head = [str(0) for x in range(0,len(headway_names))]
            h_query = ""
            for h in times:
                index = headway_names.index(h)
                format_head[index] = str(headways[times.index(h)])
            for i in range(0,len(format_head)):
                h_query += "HEADWAY[{0}]={1}, ".format(headway_names[i], format_head[i])
            result += h_query
            nodes = [x.strip() for x in row[7].split(",")]
            # If the service only has fewer than n nodes, ignore it 
            min_nodes = 2
            if len(nodes) < min_nodes:
                continue
            # # # # # # # 
            result += 'N=' + ", ".join(nodes)

            #result = wrapper.wrap(result)
            result = process_lin(result, width=70)
            file.write(result)
            #file.write('\n\t'.join(result))
            file.write('\n\n')
    log.add_message("Finished Printing LIN File", color="GREEN")
    log.add_message("%d services used" % len(condensed_services), color="GREEN")
    conn.close()

def XML_post_filter(period, op_list, infile, outfile, outlinfile, 
                    operator_file, headway_defs, log):
    """Filters out specific operators
    """

    log.add_message("Filtering in post\n")

    operator_code_dict = {}

    with open(operator_file, "r") as file:
        reader = csv.reader(file)
        columns = next(reader)
        for row in reader:
            operator_code_dict[row[1]] = row[3]

    operators = op_list
    
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    print(infile)
    with open(infile, "r") as db:
        reader = csv.reader(db)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        cur.execute(create_query)
        for data in reader:
            cur.execute(query, data)
    query = "SELECT * FROM all_serv WHERE Operator IN (" + ','.join('?' * len(operators)) + ")"
    filtered_data = cur.execute(query, [operator_code_dict[x] for x in operators])

    with open(outfile, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        rows = filtered_data.fetchall()
        log.add_message("Found %d rows" % len(rows))
        writer.writerows(rows)
        
    conn.close()

    log.add_message("Done\n", color="GREEN")
            

def import_XML_data_callback(xml_dir, station_lookup, node_lookup, 
                             operator_file, out_headways_file, op_fun, 
                             selected_days, date_filter, headway_defs, 
                             widgets, update_ops, summary_output):
    """Function called from GUI
    """
    
    try:
        import_XML_data(xml_dir, node_lookup, 
                        operator_file, out_headways_file, op_fun, 
                        selected_days, date_filter, headway_defs, widgets,
                        summary_output)
        widgets[1]["state"] = "normal"
    except KeyboardInterrupt:
        widgets[0].add_message("Keyboard Interrupt detected, stopping...", color="RED")
        widgets[1]["state"] = "normal"
        return
    except PermissionError as f:
        widgets[0].add_message("Could not open file: %s" % f, color="RED")
        widgets[1]["state"] = "normal"
        return
    except ColumnNotFoundError as e:
        widgets[0].add_message("Could not find %s column in %s" % (e.column, e.file))
        widgets[1]["state"] = "normal"
    except Exception as e:
        widgets[0].add_message("Exception: %s" % e, color="RED")
        widgets[1]["state"] = "normal"
        widgets[0].add_message("Traceback: %s" % "".join(traceback.format_tb(e.__traceback__)), color="RED")
        return
    if update_ops is not None:
        update_ops("ops")
            
def import_XML_data(xml_dir, node_lookup, operator_file, 
                    out_headways_file, op_fun, selected_days, date_filter, 
                    headway_defs, widgets, summary_output):
    """Processes a directory of TransXChange XML files
    
    Parameters
    ----------
    xml_dir : str
        Path to directory of XML files
    node_lookup : str
        Path to CSV file of ATCO to Cube node mapping
    operator_lookup : str
        Path to operator lookup file 
    out_headways_file : str
        Save path for intermediate processed data
    selected_days : list
        Days of the week to use.
    date_filter : list
        Start and end dates of the period to look at.
    headway_defs : tuple
        Headway period names and definitions
    widgets : tuple
        Must contain (log widget, button widget, progress bar widget)
    """

    log = widgets[0]
    button = widgets[1]
    progress = widgets[2]
    button['state'] = 'disabled'

    headway_def = headway_defs[0].split(',')
    headway_names = headway_defs[1].split(',')
    headway_def = [int(x.strip(' ')) for x in headway_def]
    headway_names = [x.strip(' ') for x in headway_names]

    flagged_file = "flagged_bus_routes.csv"

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS stops (ATCO, Comm_Name)')
    c.execute(("CREATE TABLE IF NOT EXISTS naptan "
               "(ATCOCode, NaptanCode, Easting, Northing, Longitude, Latitude)"))
    c.execute(("CREATE TABLE IF NOT EXISTS services "
              "(Service_Name, Long_Name, Line_Name, Circular, Direction, "
              "Operator, Mode, Day, Departure_time, Running_Time, Mid_Time, "
              "Hour, Route_ID, Route, Nodes, am_rt, ip_rt, pm_rt)"))
    
    global num_entries

    op_list = set()

    day_filter = [all_days[i] if selected_days[i] == 1 else '' 
                  for i in range(0, len(selected_days))]

    #### Load node lookup into a dictionary
    with open(node_lookup, "r") as file:
        sim_node_dict = {}
        node_dict = {}
        reader = csv.DictReader(file)
        possible_node_columns = ["Node", "node", "N", "join_N"]
        node_column = ""
        for row in reader:
            # Get the node column name 
            if node_column == "":
                for name in possible_node_columns:
                    if name in row.keys():
                        node_column = name 
                        break 
                if node_column == "":
                    raise ColumnNotFoundError(node_lookup, "Node")
            
            try:
                _ = row["SimulationNode"]
            except KeyError:
                
                try:
                    _ = row["j_type"]
                    if row["j_type"] == "m":
                        row["SimulationNode"] = "N"
                    else:
                        row["SimulationNode"] = "Y"
                except KeyError:
                    # Node lookup does not contain SimulationNode flag 
                    #   or junction_type flag. Assume all nodes are simulation 
                    row["SimulationNode"] = "Y"
                    
            # Make a dict of just simulation nodes
            if row["SimulationNode"] == "Y":
                sim_node_dict[row["ATCOCode"]] = row[node_column]
            node_dict[row["ATCOCode"]] = row[node_column]

    print("Number of nodes: %d" % len(node_dict))
    print("Number of Simulation nodes %d" % len(sim_node_dict))
        
            
    ##########################################
    
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
    except FileNotFoundError:
        with open("mode_lookup.csv", "w") as lookup:
            writer = csv.writer(lookup)
            writer.writerow(["Mode", "Num"])
    
    
    ##############################

    with open(outfile,"w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Service", "LongName", "LineName", "Circular", 
                         "Direction", "Operator", "Mode", "Day", 
                         "DepartureTime", "RunningTime", "MidTime", "Hour", 
                         "Route_id", "Route", "Nodes", "RT_AM", "RT_IP", "RT_PM"])
        log.add_message("Cleared file: " + outfile + "\n")
    
    num_entries = 0
    log.add_message("Reading XML data\n")
    dir_len = len(os.listdir(xml_dir))

    files_exist = False
    for file in os.listdir(xml_dir):
        if ".xml" in file:
            files_exist = True
    if not files_exist:
        log.add_message("No files found in directory", color="RED")
        button['state'] = 'normal'
        return
        
    data = []
    headway_info = [headway_names, headway_def]
    unused_xml_files = []
    for xml_file in os.listdir(xml_dir):
        prev_data_len = len(data)
        try:
            data += get_services(os.path.join(xml_dir, xml_file),
                                 day_filter, date_filter,
                                 headway_info, sim_node_lookup=sim_node_dict,
                                 node_lookup=node_dict, model_timings=False)
            log.add_message("- Finished reading: %s found %d services" % (xml_file.strip(".xml"), len(data) - prev_data_len))
        except NotInNetworkError:
            unused_xml_files.append(xml_file)
            log.add_message("- Finished reading: %s not in network" % xml_file.strip(".xml"))
        progress.step(1.0/dir_len*99.9)
    log.add_message(str(num_entries) + " entries found\n")
    if num_entries < 1:
        log.add_message("No services found in the simulation area for this date/day", color="RED")
        log.add_message("Check that the provided data contains relevant information", color="RED")
        return
    c.executemany("INSERT INTO services VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", data)
    
    
    write_csv(["Operator", "Line", "AM (m)", "IP (m)", "PM (m)"], 
               [[op, line] + [str(average_running_time(t, round_places=0)/60) for h, t in v.items()]
                                                       for line, sub_v in running_times.items()
                                                       for op, v in sub_v.items()], os.path.join("Output Files", "running_times.csv"))

    with open(outfile, "a", newline='') as csvfile:
        writer = csv.writer(csvfile)
        c.execute("SELECT * FROM services")
        rows = c.fetchall()
        writer.writerows(rows)
    if summary_output != "":
        summarize(summary_output)
        log.add_message("Saved Summary")
        return

    with open("Output Files\\unused_xml_files.txt", "w") as file:
        for xml_file in unused_xml_files:
            file.write("%s\n" % xml_file)
    log.add_message("Unused files have been noted in 'unused_xml_files.txt'")

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
            if key not in operators_in_lookup:
                name = operator_name_dict.get(key)
                mode = operator_mode_dict.get(name)
                if mode == None:
                    mode = "None"
                if operator_num_dict.get(key) == None:
                    operator_num_dict[key] = "1"
                while str(op_i) in operator_nums_in_lookup:
                    op_i += 1
                if operator_num_dict.get(key) not in operator_nums_in_lookup:
                    operators_to_append.append(mode.upper() + "," + key + "," + operator_num_dict.get(key) + "," + name)
                    operator_nums_in_lookup.add(operator_num_dict[key])
                else:
                    operators_to_append.append(mode.upper() + "," + key + "," + str(op_i) + "," + name)
                    operator_nums_in_lookup.add(str(op_i))
                    op_i += 1
        for line in operators_to_append:
                file.write(line + '\n')

    op_fun(op_list)

    ## Execute a SQL query to calculate headways and compress stops ##
    ## Includes: uniqueID, serv_code, TOC, TIPLOC, Times,
    ##       Headways, running_times, stat_seq, stat_seq_nodes

        
    h_periods = headway_def
    h_lengths = [int(h_periods[i]-h_periods[i-1])*60 for i in range(1, len(h_periods))]
    h_names = headway_names
    h_insert = "WHEN t.range='{0}' THEN CAST(ROUND(CAST({1} AS DOUBLE)) AS INT) "
    h_insert_2 = "WHEN Hour BETWEEN {0} AND {1} THEN '{2}' "
    h_all_insert = ""
    h_all_insert_2 = ""
    for i in range(0,len(h_lengths)):
        h_all_insert += h_insert.format(h_names[i], h_lengths[i])
        h_all_insert_2 += h_insert_2.format(int(h_periods[i]), int(h_periods[i+1])-1, h_names[i])

    headway_query = '''CREATE TABLE all_serv AS
SELECT Service_Name, Long_Name, Line_Name, Operator, Circular, Direction,
    Mode, Route_ID, GROUP_CONCAT(range) AS Times, GROUP_CONCAT(Headway) as Headways, Route, Nodes,
    AVG(CASE WHEN am_rt <> 0 THEN am_rt ELSE NULL END)/60.0 as am_rt,
    AVG(CASE WHEN ip_rt <> 0 THEN ip_rt ELSE NULL END)/60.0 as ip_rt,
    AVG(CASE WHEN pm_rt <> 0 THEN pm_rt ELSE NULL END)/60.0 as pm_rt
FROM (
        SELECT t.Service_Name, t.Long_Name, t.Line_Name, t.Operator, t.Circular, t.Direction,
                t.Mode, t.Route_ID, t.range, COUNT(*) AS NumberOfServices,
                CASE ''' + h_all_insert + '''END/COUNT(*) AS Headway,
                t.Route, t.Nodes, 
                AVG(CASE WHEN t.am_rt <> 0 THEN t.am_rt ELSE NULL END) as am_rt,
                AVG(CASE WHEN t.ip_rt <> 0 THEN t.ip_rt ELSE NULL END) as ip_rt,
                AVG(CASE WHEN t.pm_rt <> 0 THEN t.pm_rt ELSE NULL END) as pm_rt
        FROM (
                SELECT Service_Name, Long_Name, Line_Name, Operator, Circular, Mode, Route_ID, Direction,
                        CASE ''' + h_all_insert_2 + '''END AS range,
                        Route, Nodes, am_rt, ip_rt, pm_rt
                FROM services) t
        GROUP BY t.Service_Name, t.Nodes, t.range) AS Headways
WHERE (((Headways.[Headway]) Is Not Null))
GROUP BY Nodes'''

    c.execute(headway_query)

    with open(out_headways_file, "w", newline='') as csvfile:
        c.execute("SELECT * FROM all_serv")
        rows = c.fetchall()
        writer = csv.writer(csvfile)
        writer.writerow( ["Service_Name", "Long_Name", "Line_Name", "Operator", "Circular", "Direction", "Mode", "Route_ID", "Times", "Headways", "Route_ATCO", "Nodes", "am_rt", "ip_rt", "pm_rt"])
        
        # Handle duplicate line names 
        unique_rows = []
        all_line_names = [x[2] for x in rows]
        tot_service_count = {x:all_line_names.count(x) for x in set(all_line_names)}
        cur_service_count = {x:0 for x in tot_service_count}
        service_loop = {x:1 for x in tot_service_count}
        for row in rows:
            new_row = list(row)
            name = new_row[1]
            line = new_row[2]
            if tot_service_count[line] > 1:
                if cur_service_count[line] > 25:
                    cur_service_count[line] = 0
                    service_loop[line] += 1
                new_row[1] = name + " - " + (chr(cur_service_count[line] + 97) * service_loop[line])
                new_row[2] = line + "-" + (chr(cur_service_count[line] + 97) * service_loop[line])
                cur_service_count[line] += 1
            unique_rows.append(new_row)
            
        writer.writerows(unique_rows)
        
    # Summary by Line and operator
    summary_lines = {}
    for row in unique_rows:
        line_name = row[2].split("-")[0]
        operator = row[3]
        line_key = "%s %s" % (operator,  line_name)
        headways = [[name.strip(), val.strip()] for name, val in zip(row[8].split(","), row[9].split(","))]
        counts = {x:0 for x in set([y[0] for y in headways])}
        for key, headway in headways:
            time = [180,360,180][["1","2","3"].index(key)]
            count = time / int(headway)
            counts[key] += count
        _ = summary_lines.setdefault(line_key, [])
        summary_lines[line_key].append([row[1], line_name, row[3], row[4], row[6], 
                                       counts.get("1", 0), counts.get("2", 0), 
                                       counts.get("3", 0)])
    for line, info in summary_lines.items():
        headway_counts = [0, 0, 0]
        for sub in info:
            for i in range(len(headway_counts)):
                headway_counts[i] += int(sub[i + 5])
        summary_lines[line] = info[0][:5] + headway_counts 
    with open(os.path.join("Intermediate", "headways_summary.csv"), "w", newline="") as file:
        w = csv.writer(file)
        w.writerow(["name", "line", "operator", "circular", "mode", "AM", "IP", "PM"])
        w.writerows([v for v in summary_lines.values()])
                
    
    ###### Print out all the flagged routes #######
    with open(flagged_file, "w") as flags:
        writer = csv.writer(flags)
        writer.writerow(["Route", "Nodes"])
        for route in flagged_routes:
            writer.writerow([route, flagged_routes[route]])

    ###### 

    # # Write mode lookup table ##
    with open("mode_lookup.csv", "w", newline="") as lookup:
        writer = csv.writer(lookup)
        writer.writerow(["Mode", "Num"])
        for key in mode_num_dict:
            writer.writerow([key, mode_num_dict[key]])

    log.add_message("Saved intermediate file to: %s" % out_headways_file)
    log.add_message("Done\n", color="GREEN")
    ######################################################################

    conn.commit()
    c.close()
    conn.close()

    button['state'] = 'normal'

