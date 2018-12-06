# CIF Import Script

import os
import os.path
import csv
import sqlite3
import tkinter as tk
from textwrap import TextWrapper
from user_func_V2 import left, right, mid, check_valid_schedule, calc_jt, clear_serv_var, date_entry, find_mid, time_diff

os.chdir(os.path.dirname(__file__))

#################### File Paths ####################

mypath=os.path.dirname(__file__)
input_folder = 'Inputs'
input_path = os.path.join(mypath, input_folder)

################### Assign output files and Databases #######



############### Declare dictionaries and variables #################
Dict_TIPLOC_SNames={}           # TIPLOC -> Station name
operator_index = 1              # Counter for Cube Voyager operator number
operator_num_dict = {}          # Operator name -> Cube Voyager operator number
operator_mode_dict = {}         # Maps an operator -> a mode of transport e.g. "RAIL" or "BUS"
mode_num_dict = {               # Mode name -> Cube Voyager mode number
        "URBAN" : "1", "BUS" : "2", "RAIL" : "3", "SUBWAY" : "4", "FERRY" : "5", "TRAM" : "6"}
line_num_dict = {}              # Route -> line number
junction_node = '888888'        # Cube node number assigned to junction stations
out_of_model = '999999'         # Cube node number assigned to stations not included in the Cube model

# Function specific to preliminary Scotland model, checks if it crosses border
# Likely only temporarily useful
def crosses_border(node):
    #If it goes through Carlisle
    if node == "100800":
        return True
    #If it goes through Berwick upon Tweed
    if node == "100334":
        return True
    return False

#################### Import Station Names ####################

# Main function to read MSN files that contains most station information
# Populates the relevant dictionary - Dict_TIPLOC_SNames
#
# args: T1_MSN_Path     = MSN file location (to read)
#       Stat_path       = Station information file location (to write)
#       log             = Log from the GUI
#
def import_station_names(T1_MSN_Path, Stat_Path, log):

    try:
        with open(Stat_Path, 'w') as myfile:
            pass
    except IOError:
        log.add_message("Failed to access Station output file\nCheck that it is not already open\n",color="RED")
        return

    with open(T1_MSN_Path,'r') as T1_MSN:

        Stations_List = ['SName','TIPLOC','Alpha','Easting',\
                         'Northing','Data_Source']

        if Stat_Path == "":
            Stat_Path = "Stat_Name_Test_Dummy.csv"

        try:
            with open(Stat_Path,'w',newline='') as myfile:

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
            log.add_message("Failed to access Station output file\nCheck that it is not already open\n",color="RED")
            return

    log.add_message("Read MSN station names\n", color="GREEN")


# Main function to read and import timetable info from an MCA file                                              #
#                                                                                                               #
# args: T1_MCA_Path             = File path of the MCA file                                                     #
#       stat_path               = File path of station information                                              #
#       save_timetables_path    = File path to save all timetables to                                           #
#       SName_Voyager           = File path of Cube Voyager lookup                                              #
#       operator_file           = File path to read and save 'operator' -> 'Cube operator number' lookup        #
#       update_ops              = Points to function that updates the operators in the GUI                      #
#       selected_days           = List of the days to be filtered out -                                         #
#                                       e.g. [0,1,0,0,0,0,0,0] for only Tuesday                                 #
#       date_filter             = List representing the date range -                                            #
#                                       e.g. [[01,01,2014],[01,01,2022]] for the range 01/01/2014-01/01/2022    #
#       line_start              = The initial line number to start at                                           #
#       headway_defs            = Strings of user defined headway periods and names                             #
#       widgets                 = Tuple that must contain the following widgets from the GUI                    #
#                                       (Log, Button linked to this function, Progress bar)                     #
#################################################################################################################
def import_timetable_info(T1_MCA_Path, stat_path, save_timetables_path, SName_Voyager, \
                          operator_file, update_ops, selected_days, date_filter, \
                          line_start, headway_defs,  widgets):

    global operator_index
    line_counter = 0
    # File where flagged stops are outputted
    flagged_file = "flagged_stops.csv"
    # File where all services (no headways) are outputted
    all_timetables_file = "mca_out.csv"
    ops = set()

    ###### Check that the given arguments are valid ######
    if len(widgets) != 3:
        print("Incorrect number of widgets supplied\n")
        return

    log = widgets[2]

    headway_def = headway_defs[0].split(',')
    headway_names = headway_defs[1].split(',')
    headway_def = [int(x.strip(' ')) for x in headway_def]

    if len(headway_def) != len(headway_names)+1:
        log.add_message("Headway period and name mismatch\nMust have 1 less headway name than period", color="RED")
        return
    for i in range(1,len(headway_def)):
        if headway_def[i] <= headway_def[i-1]:
            log.add_message("Headways given are invalid\n", color="RED")
            return
    try:
        with open(save_timetables_path, 'w') as myfile:
            pass
        with open(operator_file, 'a') as myfile:
            pass
        with open(stat_path, 'a') as myfile:
            pass
        with open(flagged_file, 'w') as myfile:
            pass
        with open(all_timetables_file, 'w') as myfile:
            pass
    except IOError:
        log.add_message("Failed to access an output file\nCheck that they are not already open\n", color="RED")
        return
    try:
        with open(SName_Voyager, 'r') as myfile:
            pass
    except IOError:
        log.add_message("Failed to access the Cube lookup file\n", color="RED")

    ## Assign other widgets to local variables ##
    progress = widgets[0]
    button = widgets[1]
    progress_frame = progress.winfo_parent()
    progress_frame = progress._nametowidget(progress_frame)

    button['state'] = 'disabled'

    ## Create SQL database in memory and create all tables ##
    con=sqlite3.connect(':memory:')
    cur=con.cursor()
    cur.execute('CREATE TABLE Station_Names(SName, TIPLOC, Alpha,\
            Easting, Northing, Data_Source)')
    cur.execute('CREATE TABLE SName_Lookup(Station, TIPLOC, Alpha, Node)')
    #cur.execute("CREATE TABLE mode_lookup(Mode, Operator, Operator_Number)")
    cur.execute("CREATE TABLE flagged_stops(SName, TIPLOC, Node, Reason)")
    cur.execute('CREATE TABLE CIF_Import(transtype, uniqueID, firstdate, lastdate,\
                            mon, tue, wed, thu, fri, sat, sun, bankhols, status, catgry,\
                            t_identity, headcode, serv_code, power, timing, tclass, sleepers,\
                            reservs, sbrand, TOC, o_stat, TIPLOC, statname, node, arrive, \
                            depart, pass_time, begintime, numstations, t_stat, finsihtime, \
                            midtime, fromto, long_name, line, journey_time, offsets, \
                            running_times, stat_seq,o_stat_node)')

    log.add_message("Reading all timetables\n")

    ########## Create lookup of station name and Cube nodes #########

    ## Load Station names from MSN output file ##
    with open(stat_path, "r") as stat_names:
        reader = csv.reader(stat_names)
        columns = next(reader)
        query = "INSERT INTO Station_Names VALUES (?,?,?,?,?,?)"
        for row in reader:
            cur.execute(query, row)
    log.add_message(" Read station name file\n")

    ## Open Voyager node lookup and read it into SQL ##
    with open(SName_Voyager,'r') as voy_node:
        Station_Line=csv.reader(voy_node, delimiter=',')

        ## Skip first line as it contains field names ##
        header_row=csv.reader(voy_node)
        headers=next(header_row)

        for row in Station_Line:
            Station=row[0]
            TIPLOC=row[1]
            Node=row[6]
            Alpha=row[2]

            cur.execute('INSERT INTO SName_Lookup VALUES(?,?,?,?)',\
                            [Station,TIPLOC,Alpha,Node])

    log.add_message(" Read station lookup file\n")

    ## Load in operator lookup ##
    with open(operator_file, "r") as file:
        if not file.read(1):
            pass
        else:
            reader = csv.reader(file)
            columns = next(reader)
            for row in reader:
                operator_num_dict[row[1]] = row[2]
                operator_mode_dict[row[1]] = row[0]

    print(operator_num_dict, operator_mode_dict)

    ## Get the size of the MCA file (in lines) for the GUI ##
    filesize = 0
    with open(T1_MCA_Path,'r') as T1_MCA:
        filesize = sum(1 for line in T1_MCA)
    step_interval = filesize / 100
    counter = 0

    ## Begin reading MCA timetables ##
    with open(T1_MCA_Path,'r') as T1_MCA:

        log.add_message(" Reading MCA file\n")

        ## Set up empty dictionary of CIF IDs for check in new schedule import ##
        Dict_CIF_IDs={}

        ignore_serv=False
        Check_stn=False
        T1_TOC1=[]

        ## Store timetable data here to save using SQL inserts each line ##
        timetables = []

        for line in T1_MCA:
            k=-1

            counter += 1
            progress.step(1.0/filesize*100.0)

            ## Get Header info
            if left(line,2)=='HD':
                schedule_header_info='; Mainframe Identity: ' + mid(line,2,20)\
                        + '\n' + '; Date of Extract: ' + mid(line,22,6) +\
                        '\n' + '; Time of Extract: ' + mid(line,28,4) + '\n' +\
                        '; File Reference: ' + mid(line,32,7) + '\n' +\
                        '; Last File Reference: ' + mid(line,39,7) + '\n' +\
                        '; Type of Extract: ' + mid(line,46,1) + '\n' +\
                        '; CIF Version: ' + mid(line,47,1) + '\n' +\
                        '; Extract Start Date: ' + mid(line,48,6) + '\n' +\
                        '; Extract End Date: ' + mid(line,54,6) + '\n' +\
                        '; Schedule Data' + '\n' +\
                        'transtype,uniqueID,TOC,firstdate,lastdate, ' +\
                        'mon,tue,wed,thu,fri,sat,sun,bankhols,' +\
                        'status,catgry,t_identity,headcode,serv_code,power,' +\
                        'timing,tclass,sleepers,reservs,sbrand,begintime,' +\
                        'finishtime,numstations,o_stat,t_stat,fromto,' +\
                        'TIPLOCs,arrive_times,depart_times,pass_times'

            ## Get TIPLOC station data if it is not already in stat_name
            elif left(line,2)=='TI':
                line_TIPLOC=mid(line,2,7).strip()
                if line_TIPLOC in Dict_TIPLOC_SNames:
                    Check_stn=True
                else:
                    Check_stn=False

                if Check_stn==False:
                    with open(stat_path,'a',newline='') as myfile:
                        SName=mid(line,18,26).strip()
                        TIPLOC=mid(line,2,7).strip()
                        Alpha=mid(line,53,3).strip()
                        if Alpha=='':
                            Alpha='ZZZ' #Dummy Alpha Code
                        Easting='ZZZ'
                        Northing='ZZZ'
                        Data_Source='MCA'
                        Dict_TIPLOC_SNames[TIPLOC]=SName
                        Stations_List=[SName,TIPLOC,Alpha,\
                                       Easting,Northing,Data_Source]
                        wr=csv.writer(myfile)
                        wr.writerow(Stations_List)
                        cur.execute('INSERT INTO Station_Names \
                        VALUES(?,?,?,?,?,?)',[SName, TIPLOC, Alpha, \
                        Easting, Northing, Data_Source])
                        con.commit()

            ## Get basic schedule information ##
            ## If it is required - set flag ##
            ## If it is not required - go to the next schedule ##
            elif left(line,2)=='BS':

                clear_serv_var()

                # Days the service runs and the filtered days from GUI
                timetable_days = [mid(line,x,1) for x in range(21,29)]
                selected_days = [str(x) for x in selected_days]

                # Dates the service runs and the filtered dates from GUI
                firstdate = [mid(line,9,6)[i:i+2] for i in range(0,6,2)]
                lastdate = [mid(line,15,6)[i:i+2] for i in range(0,6,2)]
                running_dates = [date_entry(reversed(firstdate)),date_entry(reversed(lastdate))]

                # Filter the service
                valid = check_valid_schedule(line,selected_days, timetable_days, running_dates, date_filter)
                if not valid:
                    ignore_serv=True

                else:
                    # Check line hasn't previously been imported based on uniqueID
                    if mid(line,3,6) in Dict_CIF_IDs:
                        ignore_serv=True
                    else:
                        ignore_serv=False

                if ignore_serv==False:
                    k+=1
                    transtype=mid(line,2,1)
                    uniqueID=mid(line,3,6)
                    Dict_CIF_IDs[uniqueID]=k
                    firstdate=mid(line,9,6)
                    lastdate=mid(line,15,6)
                    mon=mid(line,21,1)
                    tue=mid(line,22,1)
                    wed=mid(line,23,1)
                    thu=mid(line,24,1)
                    fri=mid(line,25,1)
                    sat=mid(line,26,1)
                    sun=mid(line,27,1)
                    bankhols=mid(line,28,1)
                    status=mid(line,29,1)
                    catgry=mid(line,30,2)
                    t_identity=mid(line,32,4)
                    headcode=mid(line,36,4)
                    serv_code=mid(line,41,8)
                    power=mid(line,50,3)
                    timing=mid(line,53,4)
                    tclass=mid(line,66,1)
                    sleepers=mid(line,67,1)
                    reservs=mid(line,68,1)
                    sbrand=mid(line,74,4)

            elif ignore_serv==False:
                ## Extra basic schedule info
                if left(line,2)=='BX':

                    # Get operator - TOC
                    TOC=mid(line,11,2)

                    ## Add operator to GUI list ##
                    ops.add(TOC)
                    if TOC not in operator_num_dict:
                        operator_num_dict[TOC] = str(operator_index)
                        operator_index += 1

                    # Check if TOC is already in list - add if not
                    new_op=False
                    if TOC!='  ':
                        if len(T1_TOC1)==0:
                            T1_TOC1.append(TOC)
                        else:
                            for vcount in range(0,len(T1_TOC1)):
                                if TOC in T1_TOC1:
                                    new_op=False
                                    break
                                else:
                                    new_op=True
                        if new_op==True:
                            T1_TOC1.append(TOC)

                ## Origin station
                elif left(line,2)=='LO':

                    numstations=0
                    o_stat=mid(line,2,8).strip()
                    stat_seq=o_stat
                    stat_seq_node = ''
                    statname=''
                    #node=''
                    arrive='-'
                    depart = ''
                    pass_time = ''
                    begintime = ''

                    # If this field is BUS then it is a bus service,
                    # assume any other are train
                    mode = mid(line,22,3).strip()
                    if mode != "BUS":
                        mode = "RAIL"
                    if operator_mode_dict.get(TOC) == None:
                        operator_mode_dict[TOC] = mode

                    # Lookup node
                    o_stat_qry=cur.execute('SELECT Node FROM SName_Lookup WHERE TIPLOC=?',(o_stat,))
                    o_stat_record=cur.fetchone()

                    ########## Handle un-matched CIF codes ##########
                    # If the origin is not matched - assume not in model - skip and flag
                    if o_stat_record==None:
                        o_stat_node='X'
                        cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(o_stat),o_stat,o_stat_node, "Unmatched origin"])
                        continue
                    #Check if the stop is flagged as a junction
                    else:
                        o_stat_node=o_stat_record[0]
                        # If it is a Junction - skip and flag
                        if o_stat_node == junction_node:
                            cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(o_stat),o_stat,o_stat_node,"Junction as origin"])
                            continue
                        #If it is not in model - skip
                        if o_stat_node == out_of_model:
                            continue
                    ###################################################

                    # Start the node sequence
                    stat_seq_node=o_stat_node

                    depart=str(mid(line,15,4))
                    pass_time=str(mid(line,15,4))
                    begintime=str(mid(line,15,4))
                    numstations+=1

                ## Intermediate stops
                elif left(line,2)=='LI':

                    TIPLOC=mid(line,2,8).strip()

                    # Lookup node
                    li_stat_qry=cur.execute('SELECT Node FROM SName_Lookup WHERE TIPLOC=?',(TIPLOC,))
                    li_stat_record=cur.fetchone()

                    # Flag if this is the first station in the model
                    first_stat = False

                    ######### Handle un-matched CIF codes ############
                    if li_stat_record==None:

                        # If the node is not matched - flag and skip it
                        li_stat_node='X'
                        if str(mid(line,25,4)) == '0000':
                            cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(TIPLOC),TIPLOC,li_stat_node,"Unmatched point passed - Likely a junction"])
                        else:
                            cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(TIPLOC),TIPLOC,li_stat_node,"Unmatched point stopped at"])
                        continue
                    else:
                        li_stat_node=li_stat_record[0]
                        #If the stop is not in the model - not in scotland - then skip it
                        if li_stat_node == out_of_model:
                            continue
                        #If it is a junction that is being passed - skip it
                        #If it is a junction that is being stopped at - skip and flag it
                        if li_stat_node == junction_node:
                            if str(mid(line,29,4)) == '0000':
                                continue
                            else:
                                cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(TIPLOC),TIPLOC,li_stat_node,"'Junction' stopped at"])
                                continue

                        #If the node is on the border alter the start/end node
                        if crosses_border(li_stat_node):
                            #Check if this is the first station within the model
                            if stat_seq_node == '':
                                first_stat = True

                        # If it is not assigned a node in the lookup file...
                        if li_stat_node == '':
                            cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(TIPLOC),TIPLOC,li_stat_node,"Node is blank in lookup"])
                            continue
                    ###################################################

                    #node=''
                    statname=''
                    if mid(line,20,4)=='    ':
                        pass_time+=', '+str(mid(line,29,4))
                    else:
                        pass_time+=', '+str(mid(line,20,4))

                    # If it is the first station don't add leading comma
                    if first_stat:
                        stat_seq = TIPLOC
                        stat_seq_node = li_stat_node
                        arrive = '-'
                        depart = str(mid(line,29,4))
                    else:
                        stat_seq+=', '+TIPLOC
                        stat_seq_node+=', '+li_stat_node
                        arrive+=', '+str(mid(line,25,4))
                        depart+=', '+str(mid(line,29,4))

                    numstations+=1

                elif left(line,2)=='LT':

                    t_stat=mid(line,2,8).strip()

                    # Lookup node
                    t_stat_qry=cur.execute('SELECT Node FROM SName_Lookup WHERE TIPLOC=?',(t_stat,))
                    t_stat_record=cur.fetchone()

                    ########### Handle un-matched CIF codes ################

                    # Flag if not in the Cube model so that the final station is correct
                    not_in_model = False

                    if t_stat_record==None:
                        t_stat_node='X'
                        cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(t_stat),t_stat,t_stat_node,"Unmatched end point"])
                        continue
                    else:
                        t_stat_node=t_stat_record[0]
                        # If it is a junction - flag and skip
                        # If it is not in model - DO NOT SKIP but raise flag for end time to be handles
                        if t_stat_node == junction_node:
                            cur.execute("INSERT INTO flagged_stops VALUES(?,?,?,?)", [Dict_TIPLOC_SNames.get(t_stat),t_stat,t_stat_node,"Junction is end point"])
                            continue
                        if t_stat_node == out_of_model:
                            not_in_model = True

                    if not_in_model:
                        finishtime = depart.split(',')[-1]
                    else:
                        stat_seq+=', '+t_stat
                        stat_seq_node+=', '+t_stat_node
                        node=''
                        statname=''
                        arrive+=', '+str(mid(line,15,4))
                        depart+=', -'
                        pass_time+=', '+str(mid(line,15,4))
                        finishtime=str(mid(line,15,4))
                        numstations+=1

                    fromto=o_stat+'_'+stat_seq.split(',')[-1]

                    #Generate the long name from start and end stations
                    long_name = Dict_TIPLOC_SNames[o_stat.lstrip(' ')] + ' -> ' + Dict_TIPLOC_SNames[stat_seq.split(',')[-1].lstrip(' ')]

                    #Generate the line name from the user starting number
                    if line_num_dict.get(stat_seq) == None:
                        line_num_dict[stat_seq] = line_start + line_counter
                        line_counter += 1
                    line_name = line_num_dict[stat_seq]

                    # Check if a service has only one stop
                    if begintime == '' or finishtime == '' or begintime == finishtime:
                        continue

                    journey_time=calc_jt(begintime,finishtime)
                    midtime = int(find_mid(begintime.lstrip(), finishtime.lstrip()).replace(":",""))

                    # Save the cumulative running times
                    rt = [time_diff(begintime.lstrip(), x) for x in pass_time.split(', ')]
                    rt = ','.join(rt)

                    #Calc Offsets? Line below is placeholder to prevent error
                    offsets=0

                    # Skips the service if it is not in the model
                    if '1' not in stat_seq_node:
                        continue
                    else:
                        node = ''
                        timetables.append([transtype, uniqueID, firstdate,\
                                lastdate, mon, tue, wed, thu, fri, sat,\
                                sun, bankhols, status, catgry, \
                                t_identity, headcode, serv_code, power,\
                                timing, tclass, sleepers, reservs, \
                                sbrand, TOC, o_stat, TIPLOC, statname,\
                                node, arrive, depart, pass_time,\
                                begintime, numstations, t_stat,\
                                finishtime, midtime, fromto, long_name,\
                                line_name, journey_time, offsets, rt, stat_seq,\
                                stat_seq_node])

        # Load into database
        cur.executemany("INSERT INTO CIF_Import VALUES(?,?,?,?,\
                                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,\
                                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,\
                                ?,?,?,?)", timetables)

        log.add_message(" Finished with MCA file\n")

    log.add_message("Writing results to file\n")

    ## Write all timetables to file
    data=cur.execute('SELECT * FROM CIF_Import')
    with open(all_timetables_file,'w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['transtype','uniqueID','firstdate','lastdate',\
                        'mon','tue','wed','thu','fri','sat','sun','bankhols','status','catgry',\
                        't_identity','headcode','serv_code','power','timing','tclass','sleepers',\
                        'reservs','sbrand','TOC','o_stat','TIPLOC','statname','node','arrive',\
                        'depart','pass_time','begintime','numstations','t_stat','finsihtime',\
                        'midtime', 'fromto','long_name', 'line'\
                         'journey_time','offsets','running_times', 'stat_seq','stat_seq_nodes'])
        writer.writerows(data)

    ## Print a file with all flagged stops ##
    with open(flagged_file, "w", newline="") as csvfile:
        cur.execute("SELECT DISTINCT * FROM flagged_stops")
        rows = cur.fetchall()
        writer = csv.writer(csvfile)
        writer.writerow( ["Station Name", "TIPLOC", "Node", "reason"])
        writer.writerows(rows)

    ## Execute a SQL query to calculate headways and compress stops ##
    ## Includes: uniqueID, serv_code, TOC, TIPLOC, Times,
    ##       Headways, running_times, stat_seq, stat_seq_nodes


    h_periods = headway_def
    h_lengths = [int(h_periods[i]-h_periods[i-1])*60 for i in range(1, len(h_periods))]
    h_names = headway_names
    h_insert = "WHEN t.range='{0}' THEN {1} "
    h_insert_2 = "WHEN midtime BETWEEN {0} AND {1} THEN '{2}' "
    h_all_insert = ""
    h_all_insert_2 = ""
    for i in range(0,len(h_lengths)):
        h_all_insert += h_insert.format(h_names[i], h_lengths[i])
        h_all_insert_2 += h_insert_2.format(int(h_periods[i])*100, int(h_periods[i+1])*100, h_names[i])

    headway_query = '''CREATE TABLE all_serv AS
SELECT uniqueID, serv_code, TOC, TIPLOC, GROUP_CONCAT(range) AS Times,
    GROUP_CONCAT(Headway) as Headways, running_times, long_name, line, stat_seq, stat_seq_nodes
FROM (
    SELECT t.uniqueID, t.serv_code, t.TOC, t.TIPLOC, t.running_times, t.range, COUNT(*) AS NumberOfServices,
            CASE ''' + h_all_insert + '''END/COUNT(*) AS Headway, t.stat_seq, t.stat_seq_nodes, t.long_name, t.line
    FROM (
            SELECT serv_code, uniqueID, TOC, TIPLOC, running_times, CASE ''' + h_all_insert_2 + '''END AS range,
                    stat_seq, o_stat_node AS stat_seq_nodes, long_name, line
            FROM CIF_Import) t
    GROUP BY t.serv_code, t.stat_seq, t.range) AS Headways
WHERE (((Headways.[Headway]) Is Not Null))
GROUP BY stat_seq'''

    cur.execute(headway_query)

    ## Save to file so that post-processing functions can use it quickly ##
    columns = ['line', 'long_name','TOC','Times','Headways','running_times','stat_seq','stat_seq_nodes']
    select_query = "SELECT {0} FROM all_serv".format(','.join(columns))
    data=cur.execute(select_query)
    with open(save_timetables_path,'w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(columns)
        writer.writerows(data)

    #Write the operator dictionary to file, if it doesn't exist
    # Format
    # Mode(e.g. RAIL):Operator_Name:Operator_Number
    with open(operator_file, "a+",newline="") as file:
        file.seek(0)
        columns = "Mode,Operator Code,Operator Number,Operator Name\n"
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

        for key in operator_num_dict:
            if key not in operators_in_lookup:
                mode = operator_mode_dict[key]
                while str(op_i) in operator_nums_in_lookup:
                    op_i += 1
                if operator_num_dict[key] not in operator_nums_in_lookup:
                    operators_to_append.append(mode + "," + key + "," + operator_num_dict[key] + ",-")
                    operator_nums_in_lookup.add(operator_num_dict[key])
                else:
                    operators_to_append.append(mode + "," + key + "," + str(op_i) + ",-")
                    operator_nums_in_lookup.add(str(op_i))
                    op_i += 1
        for line in operators_to_append:
            file.write(line + '\n')

    # Close SQL Database
    con.close()

    # Update the GUI
    update_ops(ops)
    button['state'] = 'normal'

    log.add_message("Finished reading timetables\n", color="GREEN")

# Function that prints the Cube Voyager Line file
# args: infile          = File that contains the information to be written
#                               (output from import_timetable_info)
#       outlin          = Line file to write to
#       operator_lookup = Lookup file of operators to Cube operator numbers
#       log             = Log for the GUI
#
##################################################################################
def print_rail_lin(infile, outlin, operator_lookup, headway_defs, log):

    log.add_message("Printing LIN File")

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    num_dict = {}

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
            if line[0] == "RAIL":
                num_dict[line[1]] = line[2]

    with open(outlin, "w", newline='') as file:
        log.add_message("Writing line file\n")

        file.write(";;<<PT>><<LINE>>;;\n")
        c.execute("SELECT line, long_name, TOC, Times, Headways, running_times, stat_seq_nodes, patched_nodes FROM all_serv")
        wrapper = TextWrapper(70)
        rows = c.fetchall()
        for row in rows:
            circ = "F"
            mode_num = mode_num_dict["RAIL"]
            if row[4] == True:
                circ = "T"
            result = 'LINE NAME="' + row[0] + '", ' + 'LONGNAME="' + row[1] + '", ' + 'MODE=' + mode_num + \
                     ', OPERATOR=' + num_dict[row[2]] + ', '
            result += 'ONEWAY=T, CIRCULAR=F, '
            times = [x.strip(' ') for x in row[3].split(',')]
            headways = [x.strip(' ') for x in row[4].split(',')]
            format_head = [str(0) for x in range(0,len(headway_names))]
            h_query = ""
            #r_labels = ["AM","Mid","PM"]
            for h in times:
                index = headway_names.index(h)
                format_head[index] = str(headways[times.index(h)])
            for i in range(0,len(format_head)):
                h_query += "HEADWAY[{0}]={1}, ".format(headway_names[i], format_head[i])
            result += h_query
            result += 'CROWDCURVE[1]=1, CROWDCURVE[2]=1, CROWDCURVE[3]=1, CROWDCURVE[4]=1, CROWDCURVE[5]=1, '
            result += 'SEATCAP=999, CRUSHCAP=999, LOADDISTFAC=100, CROWDCURVE[1]=1, '

            rt = [x for x in row[5].split(',')]
            n_rt = [x for x in row[6].split(', ')]
            n = [x for x in row[7].split(', ')]
            line_n_rt = []
            after_stop = True
            for node in n:
                if after_stop:
                    line_n_rt.append("N=" + node)
                    after_stop = False
                else:
                    line_n_rt.append(node)
                if node in n_rt and n.index(node) > 0:
                    line_n_rt.append("RT=" + rt[n_rt.index(node)])
                    after_stop = True
            line_n_rt = ', '.join(line_n_rt)

            result += line_n_rt

            result = wrapper.wrap(result)
            file.write('\n\t'.join(result))
            file.write('\n')
    log.add_message("Finished Printing LIN File", color="GREEN")
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
        query = "SELECT * FROM all_serv WHERE TOC IN (" + ','.join('?' * len(op_nums)) + ")"
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
