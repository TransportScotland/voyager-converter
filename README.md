# Voyager Converter
Python tool for creating Cube Voyager File Lines files

## Specification
Process data in CIF (Common Interface File) and TransXChange format and map this to a model network
as a Cube Voyager public transport line file:

### Data Sources
1. Rail:
    - MSN files - containing station information (format = CIF)
    - MCA files - containing timetable information (format = CIF)
2. Bus:
    - XML files - containing all information about a service (format = TransXChange)
3. Other Files:
    - Model Definition Files (required) - CSV files of every node and link between nodes in the model
    - Cube Node lookup files (required) - CSV files mapping each rail station or bus stop to a node within the 
      network
        
The resulting data was then to be output in the form of a Cube Voyager input file. The Cube attributes
contained in the output are listed below.
    
  Attribute    |Bus            |Rail                    |Description
---------------|---------------|------------------------|----------------------------------------------- 
Line name      |From Data      |Generated               |Line identifier used by Cube
Long name      |From Data      |From Data               |Origin to Destination
Mode           |From Data      |From Data               |A unique number for each mode of transport. Generated if not defined by user
Operator       |From Data      |From Data               |A unique number for each transport operator. Generated if not defined by user
One-Way        |True           |True                    |Data provides services in a one way format
Circular       |False          |False                   |Assumed that all service do not match Cube's "Circular" criteria
Headways       |Calculated     |Calculated              |Minutes between services, in a certain period
Crowd Curves   |N/A            |From Optional Data      |Defined within the code
Seated Capacity|N/A            |From Optional Data      |Rolling stock data can be specified if available
Crush Capacity |N/A            |From Optional Data      |Rolling stock data can be specified if available
LOADDISTFAC    |N/A            |Assumed 100             |Default Value is 100
Nodes          |From Data      |From Data (includes RTs)|Stopping list from the data source is converted to Cube Nodes
    
### Headways
Calculated as the number of minutes between services in a given period.
The mid time of each route is found and all services within a period, e.g. 07:00 - 10:00 are
counted.
The time in minutes, e.g. 180, is then divided by the number of services.
    
### Compressing Routes
Services are compressed by grouping together those with identical stopping routes.
E.g. if one service stops at a station that another passes, but is otherwise identical, these 
are treated as separate services.
If a service has variations in the route it can take, these are taken as separate lines indicated 
with the suffix "-{letter}". E.g. if a bus service X21 has 2 possible routes, these will be called
X21-a and X21-b.
    
### Filtering Routes
To filter the services used, a day and date is input.
Certain traffic operators can be filtered in post-processing
    
## Requirements
The Cube Voyager network must already exist with a set of Cube Nodes and Links

Required files (see existing versions for format):
1. Rail:
   - MSN File - containing station info (Common Interface File)
   - MCA File - containing timetable info (Common Interface File)
   - Rail Node Lookup - maps TIPLOC to Cube Node
   - Rolling Stock (optional) - seating and crush capacity for each origin-destination pair and time period
2. Bus:
   - XML Directory - directory that contains all XML files to be processed (TransXChange format)
   - Bus Node Lookup - maps ATCO to Cube Node
3. Other:
   - Operator to Mode Lookup - service operators assigned a number for Cube and mode (Bus/Rail). Will be created as long as a path is specified
   - Node File (patching interface) - every relevant node in the network
   - Link File (patching interface) - every relevant link in the network
   - Patching Override file - overrides for the patching process, see file for formatting guidance
  
Optional Files (for other features):
1. sequence_patch.txt - Used in the "Sequence Replace" process to replace node sequences in a Cube Lin file.
2. LIN Summary Files, for use when running the "Extended Summary":
   - Urban Areas - Containing 2 columns: "N" contains the Cube node number, "urban_area" contains an ID relating to a built-up area (0 if not urban)
   - Node Local Authority - Containing 2 columns: "N" contains the Cube node number, "LA" contains an ID relating to a local authority
   - Node Cordons - Containing 2 columns: "N" contains the Cube node number, "CORDON" contains an ID relating to a custom cordon area
   - Node Coordinates - Containing 3 columns: "N" contains the Cube node number, "X" contains the x coordinate and "Y" the y coordinate (units must be metres)

Software requirements are:
- Python 3 (packages listed in requirements.txt)


## Usage
1. In 'General Options', select the day and date of interest. Ensure all file locations are specified
2. In 'Bus/Rail Import', select the data Input files then press "Import Data" and wait for the data to be processed
3. Add the desired operators to the 'Keep' pane and press "Filter Operators"
4. Open the patching interface and browse for the Node File and Link File. Press "Patch Routes".
5. When finished patching, close the patching interface.
6. Specify the output file path, and press "Print LIN File"

### Intermediate Files
Various intermediate files are produced when the tool is run, these can be used to check that the services being extracted are sensible.
1. Bus (note that these are the default file names):
   - individual_routes.csv - containing the relevant raw data extracted from the XML files, in CSV format
   - headways.csv - containing the services aggregated by time period and route, with headways calculated
   - headways_filtered_operators.csv - filtered version of headways.csv
   - headways_patched.csv - output file of the bus node patching process
2. Rail (note that these are the default file names):
   - mca_out.csv - containing the relevant raw data extracted from the MCA file, in CSV format
   - mca_out_head.csv - containing the services aggregated by time period and route, with headways calculated
   - mca_out_head_patched.csv - output file of the rail node patching process
        
### Other Tabs
##### Assign Operators
Used to assign properties to each operator
(Operator to Mode Lookup must be present)
    
##### Sequence Replace
Used to replace every occurence of a node sequence in a Line file
The sequences must be specified in the 'Changes File' in the format specified
Output is a new Line file (does not overwrite)

##### LIN Summary
Outputs a CSV of the lines file for analysis and checking based on movements between urban areas. The "Extended Summary" will also include service distance, and movements between local authorities and custom cordons.

##### LIN Renumber (incomplete)
Renumbers rail services based on a base LIN file so that services that are close to equivalent (based on origin/destination, operator and route) keep the same number as the base version. Creates a file "Alternative Lookup" that is expanded when unmatched services are found. This file can be used in the same process as an input so that these unmatched services also retain their number.

