# voyager-converter
Documentation for CIF and TransX -> Cube Voyager File converter

## Specification

The intent of these Python scripts is to parse and process data from publicly available
sources, in the form of:

- Rail:
  - MSN files - containing station information
  - MCA files - containing timetable information
  - (another source) - containing information on train capacity etc.
- Bus and Other:
  - XML files - containing all information about a service
        
The resulting data was then to be output in the form of a Cube Voyager input file,
containing for each service:
    
Attribute      |Bus            |Rail               |Description
---------------|---------------|-------------------|----------------------------------------------- 
Line name      |From XML       |Auto-Generated     |(Unique identidier)
Long name      |From XML       |Auto-Generated     |(Describes start/end)
Mode           |From XML       |All the same       |(A unique number for each mode of transport)
Operator       |From XML       |From MCA           |(A unique number for each transport operator)
One-Way        |Generally True |Generally True     |(If service is one way)
Circular       |Calculated     |Generally False    |(If service is circular)
Headways       |Calculated     |Calculated         |(Minutes between services, in a certain period)
Crowd Curves   |N/A            |-                  |(-)
Seated Capacity|N/A            |-                  |(-)
Crush Capacity |N/A            |-                  |(-)
LOADDISTFAC    |N/A            |Assumed 100        |(-)
Nodes          |Lookup Table   |Lookup Table       |(List of Voyager nodes instead of stations)
    
### Headways
These have been calculated as the number of minutes between services in a given period.
The mid time of each route is found and all services within a period, e.g. 07:00 - 10:00 are
counted.
The time in minutes, e.g. 180, is then divided by the number of services.
    
### Compressing Routes
Services are compressed by grouping together those with the exact same stopping routes.
E.g. if one service stops at a station that another passes, but is otherwise identical, these 
are treated as separate services.
    
### Filtering Routes
It was intended that the user can specify a certain day of the week and date range, and 
the script will only extract services that run on this day. 
Additionally, specific traffic operators can be specified to be filtered in post-processing
    
### GUI
A GUI was needed to allow the user to specify options, including:
- Locations of files
- Filtering options
- Headway periods
- Progress of the processing
- Other tools - Patching, Assigning operators


## Requirements

It is assumed that a network of Cube Voyager nodes has been produced

The files required to run the tool are:
- Rail:
  - MSN file - containing station info (Common Interface File)
  - MCA file - containing timetable info (Common Interface File)
  - Voyager Node Lookup - .csv file mapping TIPLOCs to Voyager Node
    - Format - Station Name(SName), TIPLOC, Alpha, Origin of data(Data_Source), EASTING, NORTHING, Cube_Node
  - Voyager Link Filler - .txt containing intermediate links between nodes
    - Format - flag, start, finish, intermediate nodes
      - (flag = R) first 2 nodes are start and finish nodes, others are intermediate nodes 
      - (flag = P) sequence of connecting nodes, no start or finish
- Bus:
  - XML directory - directory that contains all XML files to be processed (TransXChange schema)
  - Voyager Node Lookup - .csv file mapping ATCO to Voyager Node
    - Initially generated from running the tool and getting all needed stops, then using GIS to map these to the nearest Voyager Node.
  - Format - ATCOCode, CommonName, NaptanCode, Easting, Northing, Longitude, Latitude, Node(join_N), join_LA, join_X, join_Y, join_SCHEME, join_AMEND_NO, join_NAME, distance
- Python scripts:
  - CreateGUI.py - Main script (run this)
  - BusTab.py - Tab for importing TransXChange files 
  - RailTab.py - Tab for importing CIF files 
  - OperatorTab.py - Tab for assigning operators 
  - PatchTab.py - Tab for patching rail nodes
  - CIF_Import_V6.py - Processing CIF files 
  - TransX_Bus.py - Processing TransXChange files 
  - Patch_Links.py - Adds intermediate nodes 
  - user_func_V2.py - Common classes and functions
                
Other requirements are:
- Python 3
        
## Usage

The tool is started by running the CreateGUI.py script

### RAIL Tab
Imports Rail timetables

- Day Definitions - Select the day to be processed 
- Date and Line Defintions - Select the date range to process and the 'Line' number to begin auto-generating at (default=1000)
- Select Files:
  - MSN - Input .MSN file
  - MCA - Input .MCA file
  - All Services - .csv to print all services to 
  - Operator Lookup - .csv where to generate/lookup operator numbers (will be appended to if new operators are found)
  - Station Lookup - .csv will create/use lookup of station names
  - Node Lookup - .csv used to lookup known Voyager Nodes
  - Filtered Output - .csv where to save filtered services 
  - Patched Output - .csv where to save final output with patched nodes 
  - LIN Output - .lin where to write Voyager LIN file 
  - Link Lookup - .txt Lookup of intermediate nodes - see requirements section
- Select Operators - Allows selection of operators to include in the filtered output (press read operators above to load all rail operators without processing the whole MCA file)
- Headway Definition -  Allows user to define headway periods 
- Save Valid Schedules - Post-processing filtering by operator 
- Log - Progress and error messages
- Progress - Progress bar for reading MCA file
    
#### Usage
- A day must be selected, date range given, headways defined, and all files specified before processing. (Defaults are provided)
- To process, press 'Read MSN' and then 'Read MCA'.
- When done, operators must be added to the right pane using the middle buttons
- Press 'Update Valid Schedules' then proceed to patching via PATCH tab
    
### BUS Tab
Imports bus timetables

- Day Definitions - Select the day to be processed 
- Date and Line Defintions - Select the date range to process and the 'Line' number to begin auto-generating at (default=1000)
- Select Files:   XML Directory - Directory of XML files
  - Full Output - .csv to print all services to 
  - Filtered Output - .csv where to save filtered services 
  - Operator Lookup - .csv where to generate/lookup operator numbers (will be appended to if new operators are found)
  - Node Lookup - .csv used to lookup known Voyager Nodes
  - Patched Output - .csv where to save final output with patched nodes (not currently used)
  - LIN Output - .lin where to write Voyager LIN file 
- Select Operators - Allows selection of operators to include in the filtered output 
- Headway Definition - Allows user to define headway periods 
- Save Valid Schedules - Post-processing filtering by operator 
- Log - Progress and error messages
- Progress - Progress bar for reading MCA file
                
#### Usage
- A day must be selected, date range given, headways defined, and all files specified before processing. (Defaults are provided)
- To process, press 'Read Files'.
- When done, operators must be added to the right pane using the middle buttons
- Press 'Update Valid Schedules' 
        
### OPERATORS Tab
Manage Operators modes.

- Main Pane - Will contain list of all operators in lookup 
- Read Operators - Press to load operator lookup
- Save Operators - Press to overwrite operator lookup with the current list 
- Delete Selected - Remove all selected operators 
- Current Mode/Number - Displays the properties of the selected operators 
- Desired Mode/Update Operators - Changes the mode of the selected operators to the desired Mode 
- Filter Modes/Operators - Only shows operators with the selected modes
    
### PATCH Tab
- Filtered Services - The filtered output previously produced
- Patched Services - Output file with patched nodes
- Node Lookup - Lookup for intermediate nodes 
- Log - Log messages
    
    
## Not Implemented
- Support multiple rail input files 
- Patch routes other than rail
- Support selecting multiple days - Average?
- Carlisle may have been assigned a previously assigned node
