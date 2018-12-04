import os
import csv
import sqlite3
import xml.etree.ElementTree as ET
from itertools import groupby
from textwrap import TextWrapper

current_dir = os.path.dirname(__file__)
outfile = "journeys.csv"
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
mode_num_dict = {"urban bus" : "1", "bus" : "2", "rail" : "3", "underground" : "4", "ferry" : "5", "tram" : "6"}      #Dictionary for line numbers
operator_num_dict = {}  #operator name to cube number
flagged_routes = {}
operator_index = 1
test_stops = []
test_times = []


class time_entry:
    def __init__(self, pattern):
        self.pattern = pattern
        self.date_dict = {}
    def add_time(self, day, time):
        self.date_dict.setdefault(day, [])
        self.date_dict[day].append(time)

class date_entry:
    def __init__(self, date=[0,0,0]):
        date = [int(x) for x in date]
        self.day = date[0]
        self.month = date[1]
        self.year = date[2]
    def is_later_than(self, other): #Returns true if the date is later than or equal to the argument given
        if self.year > other.year:return True
        elif self.year == other.year:
            if self.month > other.month: return True
            elif self.month == other.month:
                    if self.day >= other.day: return True
        else:
            return False 
    def within_range(self, start, end): # Returns true if the date is between start and end
        '''print(str(self.year) + " " + str(self.month) + " " + str(self.day))
        print(str(start.year) + " " + str(start.month) + " " + str(start.day))
        print(str(end.year) + " " + str(end.month) + " " + str(end.day))'''
        if self.is_later_than(start) and end.is_later_than(self):
            return True
        else:
            return False
        

########## Currently ignores the fact that some services will run into the next day #######################
##### The table of all stops is generated each time that data is read... #####
#####

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
    

def create_stop_table(filename, op_list, day_filter, date_filter, c):

    global num_entries, operator_index
    date_range_from = date_entry(date_filter[0])
    date_range_to = date_entry(date_filter[1])

    list_of_journeys = []
    journey_code_dict = {}

    xml_tree = ET.parse(filename)
    root = xml_tree.getroot()    

    #Get the useful portions of the file
    points = root.find('ns:StopPoints', ns)
    point = points.findall("ns:AnnotatedStopPointRef", ns)
    services = root.find("ns:Services", ns)
    service = services.findall("ns:Service", ns)
    journey_sections = root.find("ns:JourneyPatternSections", ns)
    journey_section = journey_sections.findall("ns:JourneyPatternSection", ns)
    vehicle_journeys = root.find("ns:VehicleJourneys", ns)
    vehicle_journey = vehicle_journeys.findall("ns:VehicleJourney", ns)
    operators = root.find("ns:Operators", ns)
    operator = operators.findall("ns:Operator", ns)

    #Dictionary of all stoprefs
    for stop in point:
        ref = stop.find('ns:StopPointRef', ns).text
        com = stop.find('ns:CommonName', ns).text
        stop_dict[ref] = com
        row = [ref,com]

        c.execute('INSERT OR IGNORE INTO stops VALUES(?,?)', row)

    #Dictionary for the possible journeys of each service
    for section in journey_section:
        journey_id = section.get("id")
        
        links = section.findall("ns:JourneyPatternTimingLink", ns)
        running_time = 0
        for link in links:
            from_ref = link.find("ns:From", ns).find("ns:StopPointRef", ns).text
            to_ref = link.find("ns:To", ns).find("ns:StopPointRef", ns).text
            time = link.find("ns:RunTime", ns).text

            split_time = [time[-1], time[2:-1]]
            if split_time[0] == 'S':
                running_time += int(split_time[1])
            if split_time[0] == 'M':
                running_time += int(split_time[1]) * 60
            if split_time[0] == 'H':
                running_time += int(split_time[1]) * 60 * 60

            journey_dict.setdefault(journey_id, [])
            journey_dict[journey_id].append(
                (from_ref, to_ref, running_time))

    #Build dict for operators
    for op in operator:
        o_id = op.attrib["id"]
        name = op.find("ns:OperatorShortName", ns).text #full name of operator
        print(o_id, name)
        operator_name_dict[o_id] = name

    #Get service details
    header = ["Service", "Line", "Operator", "Start Date", "End Date"]
    for serv in service:
        line = []
        service_code = serv.find("ns:ServiceCode", ns).text
        line_name = serv.find("ns:Lines", ns).find("ns:Line", ns).find("ns:LineName", ns).text
        
        op_period = serv.find("ns:OperatingPeriod", ns)
        start_date = date_entry([x for x in reversed(op_period.find("ns:StartDate", ns).text.split('-'))])
        end_date = date_entry([x for x in reversed(op_period.find("ns:EndDate", ns).text.split('-'))])
        
        valid_serv = date_range_from.within_range(start_date, end_date) or date_range_to.within_range(start_date, end_date)\
                     or start_date.within_range(date_range_from, date_range_to) or end_date.within_range(date_range_from, date_range_to)

        operator = serv.find("ns:RegisteredOperatorRef", ns).text   #reference id of operator
        long_name = serv.find("ns:Description", ns).text
        mode = serv.find("ns:Mode", ns).text

        stand_serv = serv.find("ns:StandardService", ns)

        line.extend((service_code, line_name, operator, start_date, end_date, long_name))

        #service_dict.setdefault(service_code, [])
        service_dict[service_code] = [line_name, operator, start_date, end_date, long_name, mode, valid_serv]
        
        for journey_pattern in stand_serv.findall("ns:JourneyPattern", ns):
            direction = journey_pattern.find("ns:Direction", ns).text
            for journey_pattern_section_ref in journey_pattern.findall("ns:JourneyPatternSectionRefs", ns):
                line.extend(
                    (journey_pattern_section_ref.text, direction, journey_dict.get(journey_pattern_section_ref.text)))

        test_stops.append(line)

    #Get timetable details
    for journey in vehicle_journey:
        operator = journey.find("ns:OperatorRef", ns).text
        days_of_week = journey.find("ns:OperatingProfile", ns).find("ns:RegularDayType", ns).find(
            "ns:DaysOfWeek", ns)
        if days_of_week == None:    #If no days/ holidays only, skip and go to next entry
            continue
        days_of_week = [x.tag for x in days_of_week]                #If service runs on mondays tuesdays and fridays ['{ns}Monday', '{ns}Tuesday', '{ns}Friday']
        days = [x.split("}")[1] for x in days_of_week]              #['Monday', 'Tuesday', 'Friday']
        days = [x if x in day_filter else '' for x in days]         #If tuesday and monday in filter = ['Monday', 'Tuesday', '']
        day_bin = [0 for d in all_days]                             #[0,0,0,0,0,0,0,0]

        # Check for special days of operation
        '''special_operation = []
        special_non_operation = []
        for daterange in journey.find("ns:OperatingProfile",ns).find(
            "ns:SpecialDaysOperation",ns).find("ns:DaysOfOperation",ns).findall("ns:DateRange",ns):
            pair = [date_entry([x for x in reversed(daterange.find("ns:StartDate",ns).text.split('-'))]), \
                               date_entry([x for x in reversed(daterange.find("ns:EndDate",ns).text.split('-'))])]
            special_operation.append(pair)

        for daterange in journey.find("ns:OperatingProfile",ns).find(
            "ns:SpecialDaysOperation",ns).find("ns:DaysOfNonOperation",ns).findall("ns:DateRange",ns):
            pair = [date_entry([x for x in reversed(daterange.find("ns:StartDate",ns).text.split('-'))]), \
                               date_entry([x for x in reversed(daterange.find("ns:EndDate",ns).text.split('-'))])]
            special_operation.append(pair)

        for pair in special_operation:
            valid_sched = date_range_from.within_range(pair[0], pair[1]) or date_range_to.within_range(pair[0], pair[1])\
                          or pair[0].within_range(date_range_from, date_range_to) or pair[1].within_range(date_range_from, date_range_to)'''
                               
        

        departure_time = journey.find("ns:DepartureTime", ns).text
        journey_pattern_ref = journey.find("ns:JourneyPatternRef", ns).text
        journey_code = journey.find("ns:VehicleJourneyCode", ns).text
        service_ref = journey.find("ns:ServiceRef", ns).text

        pattern_ref_dict.setdefault(journey_pattern_ref, time_entry(journey_pattern_ref))
        journey_code_dict.setdefault(journey_code, [])
        valid_sched = False
        for d in days:
            if d != '':     #If at least one day is in filter flag the entry as valid 
                valid_sched = True                                                  #When reaching 'Monday' schedule is deemed valid
                pattern_ref_dict[journey_pattern_ref].add_time(d, departure_time)   #pattern_ref -> 'Monday',11:30
                day_bin[day_filter.index(d)] = 1                                    #[1,1,0,0,0,0,0]

        day_bin = ", ".join([str(x) for x in day_bin])
        journey_code_dict[journey_code].extend((service_ref, journey_pattern_ref, day_bin, departure_time, valid_sched))

    for key in journey_code_dict:
        
        ser = journey_code_dict[key][0]     #service_dict key
        valid = journey_code_dict[key][4] and service_dict[ser][6]
        if not valid: # If the service is not required, skip
            continue
        jou = journey_code_dict[key][1]     #journey_dict key
        tot_time = journey_dict[jou][-1][2] #The final entry for the cumulative running time
        dep_time = journey_code_dict[key][3]#The time the service departs
        operator = service_dict[ser][1]     #Operator of the service

        ### If not in the operator list, add ###
        if operator not in operator_num_dict:
            operator_num_dict[operator] = str(operator_index)
            operator_index += 1

        #Create a string containing all routes that can be stored in an sql db
        circular = False
        if len(journey_dict[jou]) > 1:
            if journey_dict[jou][0][0] == journey_dict[jou][-1][1]: #Check if the route ends at the same stop as it starts at: circular route
                circular = True
            route = ", ".join([x[0] for x in journey_dict[jou]])
            route = route + ', ' + journey_dict[jou][-1][1]
        else:       #If there is only one entry the alternative method is needed
            route = journey_dict[jou][0][0] + ", " + journey_dict[jou][0][1]

        ### Load route into SQL db to perform node lookup...###
        c.execute("CREATE TABLE IF NOT EXISTS route (ATCO)")
        for stop in route.split(", "):
            c.execute("INSERT INTO route VALUES(?)", [stop])
        c.execute('''SELECT route.ATCO, lookup.join_N
FROM route
INNER JOIN lookup ON route.ATCO = lookup.ATCOCode''')
        nodes = c.fetchall()
        nodes = [x[1] for x in nodes]

        nodes = ", ".join([x[0] for x in groupby(nodes)])
        c.execute("DELETE FROM route")
        #If the length of the route is 1 or less, there was an error mathcing to unique nodes
        if len(nodes.split(',')) <= 1:
            flagged_routes[route] = nodes
            #continue
        #################################################

        split_time = [int(x) for x in dep_time.split(":")]
        mid_time = find_mid(split_time, tot_time)
        hour = int(mid_time[0])
        mid_time = ':'.join([str(x) for x in mid_time])
        mode = service_dict[ser][5]

        if operator not in operator_mode_dict:
            operator_mode_dict[operator] = mode

        if mode not in mode_num_dict: #Check that the mode is not an unknown
            print("Mode not available: " + mode)
            mode_num_dict[mode] = mode # Add a dummy value

        #op_list.add(operator_name_dict[operator])   #(Add to the operator list for GUI)
        op_list.add(operator)
        
        list_of_journeys.append([       #Being added twice?
            ser, service_dict[ser][4],\
            service_dict[ser][0], \
            circular, \
            operator, \
            mode_num_dict[mode], \
            journey_code_dict[key][2], \
            dep_time, \
            tot_time, \
            mid_time, \
            hour, \
            jou, \
            route, \
            nodes])
        #list_of_journeys[-1][-1] + ", " + journey_dict[jou][-1][1]

        num_entries += 1

    for row in list_of_journeys:
        c.execute("INSERT INTO services VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)

    '''with open("journeys.csv", "a", newline='') as csvfile:
        writer = csv.writer(csvfile)
        for row in list_of_journeys:
            print(row[9])
            c.execute("INSERT INTO services VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        #c.execute("SELECT * FROM services")
        c.execute("SELECT Service_Name, Mid_Time, Count(*) FROM services GROUP BY Route_ID, Mid_Time")
        rows = c.fetchall()
        writer.writerows(rows)'''

def print_lin_file(infile, outlin, operator_lookup, headway_defs, log):

    log.add_message("Printing LIN File")

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    num_dict = {}
    mode_dict = {}
    mode_num_dict = {}
    
    headway_names = [x.lstrip(' ') for x in headway_defs[1].split(',')]

    with open(infile, "r") as db:
        reader = csv.reader(db)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        c.execute(create_query)
        for data in reader:
            c.execute(query, data)

    with open(operator_lookup, "r") as file:
        reader = csv.reader(file)
        headers = next(reader)
        lines = []
        for row in reader:
            lines.append(row)
        for line in lines:
            num_dict[line[1]] = line[2]
            mode_dict[line[1]] = line[0]

    with open("mode_lookup.csv", "r") as file:
        reader = csv.reader(file)
        headers = next(reader)
        lines = []
        for row in reader:
            lines.append(row)
        for line in lines:
            print(line[0], line[1])
            mode_num_dict[line[0]] = line[1]
    
    with open(outlin, "w", newline='') as file:
        log.add_message("Writing line file\n")
        file.write(";;<<PT>><<LINE>>;;\n")
        c.execute("SELECT Line_Name, Long_Name, Mode, Operator, Circular, Times, Headways, Nodes FROM all_serv")
        wrapper = TextWrapper(70)
        rows = c.fetchall()
        for row in rows:
            circ = "F"
            if row[4] == True:
                circ = "T"
            op_num = num_dict.get(row[3])
            mode = mode_dict.get(row[3]).lower()
            mode = mode_num_dict.get(mode)
            result = 'LINE NAME="' + row[0] + '", ' + 'LONGNAME="' + row[1] + '", ' + 'ALLSTOPS=F, MODE=' + mode + ', OPERATOR=' + op_num + ', '
            result += 'ONEWAY=T, CIRCULAR=' + circ + ', '
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
            result += 'N=' + row[-1]

            result = wrapper.wrap(result)
            file.write('\n\t'.join(result))
            file.write('\n')
    log.add_message("Finished Printing LIN File", color="GREEN")
    conn.close()

def XML_post_filter(period, op_list, infile, outfile, outlinfile, operator_file, headway_defs, log):

    log.add_message("Filtering in post\n")

    operator_code_dict = {}

    with open(operator_file, "r") as file:
        reader = csv.reader(file)
        columns = next(reader)
        for row in reader:
            operator_code_dict[row[1]] = row[2]

    operators = op_list
    
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
    query = "SELECT * FROM all_serv WHERE Operator IN (" + ','.join('?' * len(operators)) + ")"
    filtered_data = c.execute(query, operators)

    with open(outfile, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        rows = filtered_data.fetchall()
        writer.writerows(rows)
        
    conn.close()

    log.add_message("Done\n", color="GREEN")
            

def import_XML_data(xml_dir, station_lookup, node_lookup, operator_file, out_headways_file, op_fun, selected_days, date_filter, headway_defs, widgets):

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
    c.execute('CREATE TABLE IF NOT EXISTS naptan (ATCOCode, NaptanCode, Easting, Northing, Longitude, Latitude)')
    c.execute('CREATE TABLE IF NOT EXISTS services (Service_Name, Long_Name, Line_Name, Circular, Operator, Mode, Day, Departure_time, Running_Time, Mid_Time, Hour, Route_ID, Route, Nodes)')
    
    global num_entries

    op_list = set()

    day_filter = [all_days[i] if selected_days[i] == 1 else '' for i in range(0, len(selected_days))]

    ##### Load the lookup table into SQL #####
    with open(node_lookup, "r") as lookup:
        reader = csv.reader(lookup)
        columns = next(reader)
        query = "INSERT INTO lookup({0}) VALUES ({1})"
        create_query = "CREATE TABLE IF NOT EXISTS lookup (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        c.execute(create_query)
        for data in reader:
            c.execute(query, data)
    ##########################################
    ## Write mode lookup table ##
    with open("mode_lookup.csv", "w", newline="") as lookup:
        writer = csv.writer(lookup)
        writer.writerow(["Mode", "Num"])
        for key in mode_num_dict:
            writer.writerow([key, mode_num_dict[key]])
    ##############################

    with open(outfile,"w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Service", "LongName", "LineName", "Circular", "Operator", "Mode", "Day", "DepartureTime", "RunningTime", "MidTime", "Hour", "Route_id", "Route"])
        log.add_message("Cleared file: " + outfile + "\n")
    #xml_dir = current_dir + "\Test Data\Test"   #Testing few files
    #xml_dir = current_dir + "\Test Data\Scotland_TL_Data"       #All files
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
        
    for xml_file in os.listdir(xml_dir):
        log.add_message("- Currently reading: " + xml_file + '\n')
        create_stop_table(xml_dir + "\\" + xml_file, op_list, day_filter, date_filter, c)
        progress.step(1.0/dir_len*99.9)
    log.add_message(str(num_entries) + " entries found\n")

    with open(outfile, "a", newline='') as csvfile:
        writer = csv.writer(csvfile)
        c.execute("SELECT * FROM services")
        rows = c.fetchall()
        writer.writerows(rows)

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
                mode = operator_mode_dict.get(key)
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
    h_insert = "WHEN t.range='{0}' THEN {1} "
    h_insert_2 = "WHEN Hour BETWEEN {0} AND {1} THEN '{2}' "
    h_all_insert = ""
    h_all_insert_2 = ""
    for i in range(0,len(h_lengths)):
        h_all_insert += h_insert.format(h_names[i], h_lengths[i])
        h_all_insert_2 += h_insert_2.format(int(h_periods[i]), int(h_periods[i+1])-1, h_names[i])

    headway_query = '''CREATE TABLE all_serv AS
SELECT Service_Name, Long_Name, Line_Name, Operator, Circular,
    Mode, Route_ID, GROUP_CONCAT(range) AS Times, GROUP_CONCAT(Headway) as Headways, Route, Nodes
FROM (
        SELECT t.Service_Name, t.Long_Name, t.Line_Name, t.Operator, t.Circular,
                t.Mode, t.Route_ID, t.range, COUNT(*) AS NumberOfServices,
                CASE ''' + h_all_insert + '''END/COUNT(*) AS Headway,
                t.Route, t.Nodes
        FROM (
                SELECT Service_Name, Long_Name, Line_Name, Operator, Circular, Mode, Route_ID,
                        CASE ''' + h_all_insert_2 + '''END AS range,
                        Route, Nodes
                FROM services) t
        GROUP BY t.Service_Name, t.Route, t.range) AS Headways
WHERE (((Headways.[Headway]) Is Not Null))
GROUP BY Route'''

    c.execute(headway_query)

    ###### Run an SQL query to calculate headways for each service ######
#    c.execute('''CREATE TABLE all_serv AS
#SELECT Service_Name, Long_Name, Line_Name, Operator, Circular,
#    Mode, Route_ID, GROUP_CONCAT(range) AS Times, GROUP_CONCAT(Headway) as Headways, Route, Nodes
#FROM (
#    SELECT t.Service_Name, t.Route_ID, t.range, Count(*) AS NumberOfServices, t.circular, t.Mode,
#        CASE WHEN t.range='AM' THEN 180
#        WHEN t.range='Mid' THEN 360
#        WHEN t.range='PM' THEN 180 END/Count(*) AS Headway,
#        t.Route, t.Nodes, t.Long_Name, t.Line_Name, t.Operator
#    FROM (
#        SELECT Service_Name, Long_Name, Line_Name, Operator, Circular, Mode, Day, Route, Nodes, Route_ID,
#            CASE WHEN Hour BETWEEN 7 AND 9 THEN 'AM'
#            WHEN Hour BETWEEN 10 AND 15 THEN 'Mid'
#            WHEN Hour BETWEEN 16 AND 18 THEN 'PM' END AS range
#        FROM services) t
#    GROUP BY t.Service_Name, t.Route, t.range)  AS Headways
#WHERE (((Headways.[Headway]) Is Not Null))
#GROUP BY Route;''')

#    c.execute('''SELECT Service_Name, Long_Name, Line_Name, Hour, Route, Nodes, Route_ID,
#            CASE WHEN Hour BETWEEN 7 AND 9 THEN 'AM'
#            WHEN Hour BETWEEN 10 AND 15 THEN 'Mid'
#            WHEN Hour BETWEEN 16 AND 18 THEN 'PM' END AS range
#        FROM services''')


    with open(out_headways_file, "w", newline='') as csvfile:
        c.execute("SELECT * FROM all_serv")
        rows = c.fetchall()
        writer = csv.writer(csvfile)
        writer.writerow( ["Service_Name", "Long_Name", "Line_Name", "Operator","Circular", "Mode", "Route_ID", "Times", "Headways", "Route_ATCO", "Nodes"])
        writer.writerows(rows)
    
    ###### Print out all the flagged routes #######
    with open(flagged_file, "w") as flags:
        writer = csv.writer(flags)
        writer.writerow(["Route", "Nodes"])
        for route in flagged_routes:
            writer.writerow([route, flagged_routes[route]])

    ###### 

    ###### Used to make a lookup of all NAPTAN stops to ATCO Codes ######
    ## Used for assigning nodes to stops using GIS ##
    log.add_message("Loading lookup table\n")
    try:
        with open(station_lookup,'r') as lookup:
            dr = csv.DictReader(lookup)
            to_db = [(i['ATCOCode'], i['NaptanCode'], i['Easting'], i['Northing'], i['Longitude'], i['Latitude']) for i in dr]
        c.executemany('INSERT INTO naptan VALUES(?,?,?,?,?,?);', to_db)
        log.add_message("Performing table join\n")
        c.execute('''SELECT stops.ATCO, stops.Comm_Name, naptan.NaptanCode, naptan.Easting, naptan.Northing, naptan.Longitude, naptan.Latitude
    FROM stops
    INNER JOIN naptan ON stops.ATCO = naptan.ATCOCode
    GROUP BY stops.ATCO''')
        rows = c.fetchall()
        with open('used_naptan_stops.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ATCOCode", "CommonName", "NaptanCode", "Easting", "Northing", "Longitude", "Latitude"])
            writer.writerows(rows)

    except IOError:
        log.add_message("Could Not Open Naptan to ATCO Lookup",color="RED")
        log.add_message("Provide 'Stops_reduced.csv', Containing:",color="RED")
        log.add_message("ATCOCode, NaptanCode, Easting, Northing, Longitude, Latitude",color="RED")

        '''print("All modes used are: ")
        for k in mode_num_dict:
            print(mode_num_dict[k])'''

    log.add_message("Done\n", color="GREEN")
    ######################################################################

    conn.commit()
    c.close()
    conn.close()

    button['state'] = 'normal'

