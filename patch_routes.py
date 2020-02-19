import csv
import math

class Queue:
    def __init__(self):
        self.num_elements = 0
        self.elements = []
    def pop(self):# Get first in queue
        first_elem = self.elements[0]
        del self.elements[0]
        self.num_elements -= 1
        return first_elem
    def push(self, element):# Put element at the back of the queue 
        self.elements.append(element)
        self.num_elements += 1
    def is_empty(self):
        return self.num_elements == 0
        
def valid_path(path, adjacency_dict):
    if type(path) is type(""):
        path = path.split("-")
    for i in range(len(path) - 1):
        try:
            if path[i+1] not in adjacency_dict[path[i]]:
                return False
        except KeyError:
            # node is not in available nodes: invalid
            return False
    return True
    
class ColumnNotFoundError(Exception):
    def __init__(self, file, column):
        super(ColumnNotFoundError, self).__init__("%s not found in %s" % (column, file))
        self.column = column 
        self.file = file
        
def get_unique_links(unpatched_file):
    
    with open(unpatched_file, "r") as file:
        reader = csv.DictReader(file)
        node_seqs = []
        possible_node_columns = ["Node", "node", "N", "join_N", "Nodes", "nodes"]
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
                node_seqs.append(row[node_column].split(","))
            except KeyError:
                node_seqs.append(row[node_column].split(","))
            
    unique_pairs = set()
    
    # Loop over all the sequences of nodes 
    for seq in node_seqs:
        # Loop over all nodes in the sequence (except the last)
        for i in range(0, len(seq)-1):
            # Get the next assigned node
            # If the node is not repeated add link to the set 
            next_index = next((j+ i + 1 for j, x in enumerate(seq[i+1:]) if 
                               x != "999999" and x != "-1"), None) 
            if next_index is None:
                continue 
            if seq[i] != seq[next_index]:
                unique_pairs.add(tuple((seq[i], seq[next_index])))
                
    print("Number of unique pairs is %s" % len(unique_pairs))
                
    return unique_pairs
    
def create_adjacency_dict(node_file, link_file, zone_min=0, zone_max=999, 
                          is_rail=False):
    # Build list of all nodes
    with open(node_file, "r") as file:
        reader = csv.DictReader(file)
        nodes = []
        for row in reader:
            nodes.append(row["Node"])
    # Store connected nodes in a set for each node
    adj_dict = {node:set() for node in nodes}
    len_dict = {}
    with open(link_file, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                n1 = row["ANode"]
                n2 = row["BNode"]
                try:
                    dist = row["Length"]
                except KeyError:
                    dist = row["DISTANCE"]
                # Do not include links that connect to zones (Preceded by a 'C')
                if (n1[0] == "C" or 
                    n2[0] == "C" or 
                    zone_min <= int(n1) <= zone_max or 
                    zone_min <= int(n2) <= zone_max):
                    print("Nodes identified as zones %s or %s" % (n1, n2))
                    continue
#                if (is_rail is not True and 
#                    (int(n1) > 100000 or int(n2) > 100000)):
#                    continue
                adj_dict[n1].add(n2)
                len_dict[(n1, n2)] = float(dist)
                if is_rail is True:
                    adj_dict[n2].add(n1)
                    len_dict[(n2, n1)] = float(dist)
            except KeyError as e:
                print("%s not found in node file" % e)
                if (n1[0] == "C" or 
                    n2[0] == "C" or 
                    zone_min <= int(n1) <= zone_max or 
                    zone_min <= int(n2) <= zone_max):
                    continue
    print("Length of node dict is %s" % len(nodes))
    print("Length of link dict is %s" % len(adj_dict))
    print("Length of distance dict is %s" % len(len_dict))
    return adj_dict, nodes, len_dict, len(nodes)
    
# Returns a list of nodes giving the shortest path between origin and destination 
def breadth_first_search(adjacency_dict, origin, destination, node_list):
    q = Queue()
    q.push(origin)
    previous_node = {}
    visited_nodes = {node:False for node in node_list}
    visited_nodes[origin] = True
    # Check that the destination is connected to the network
    if len(adjacency_dict.get(destination, [])) < 1:
        return False
    while q.is_empty() is False:
        node = q.pop()
        if node not in node_list: break # If the node is not in the node_lookup file, skip this
        for adj_node in adjacency_dict[node]:
            if adj_node not in node_list: continue
            if visited_nodes[adj_node] == False:
                q.push(adj_node)
                visited_nodes[adj_node] = True
                previous_node[adj_node] = node
                if adj_node == destination:
                    full_path = [adj_node]
                    start_node = adj_node
                    while start_node != origin:
                        full_path.append(previous_node[start_node])
                        start_node = previous_node[start_node]
                    return full_path
    return False

def is_invalid(node):
    return node in ["-1", "999999"]

def dijkstras(adjacency_dict, distance_dict, origin, destination,
                node_list, max_depth=500, line_store=None, verbose=False):
    if is_invalid(origin) or is_invalid(destination):
        return False
    if verbose is True:
        print("Running Dijkstras for %s - %s" % (str(origin), str(destination)))
    shortest_path_set = set()
    dists_from_origin = {x:math.inf for x in node_list if node_list}
    prev_node_path = {x:[] for x in node_list}
    node = origin
    dists_from_origin[node] = 0
    while len(shortest_path_set) < max_depth:
        # Add to set
        shortest_path_set.add(node)
        # Update distances
        for adj_node in adjacency_dict[node]:
            try:
                distance = dists_from_origin[node] + distance_dict[(node, adj_node)]
                if distance < dists_from_origin[adj_node]:
                    dists_from_origin[adj_node] = distance
                    prev_node_path[adj_node] = prev_node_path[node] + [node]
                    if line_store is not None:
                        line_store.append((list(prev_node_path[adj_node] + [adj_node]), False))
            except KeyError as k:
                if verbose is True:
                    print("%s not in dict" % k)
                continue
        # Choose new node
        for node in sorted(dists_from_origin, key=dists_from_origin.get):
            if node not in shortest_path_set:
                # The node is valid - do next loop
                break
    if line_store is not None:
        line_store.append((list(prev_node_path[destination]) + [destination], True))
    if destination not in shortest_path_set:
        return False
    if verbose is True:
        print(prev_node_path[destination])
    return list(reversed(prev_node_path[destination] + [destination]))
    
    
def create_paths(adjacency_dict, distance_dict,
                 unique_pairs, node_list, patch_override_file,
                 working_sequence=None, use_distance=True,
                 max_distance=500):

    path_data = []
    unmatched_paths = []
    overridden_paths = []
    dummy_nodes = ["-1", "999999"]
    
    print("Creating Paths")
    
    # Get the user overrides from file 
    with open(patch_override_file, "r") as file:
        data = file.readlines()
        for row in data:
            if row[0] in ["R", "S"]:
                row = row.strip("\n")
                t, a, b, path = row.split(":")
                if valid_path(path, adjacency_dict) is False:
                    print("Invalid Path Given %s" % path)
                path_data.append([a, b, path])
                overridden_paths.append((a, b))
                if t == "R":
                    r_path = "-".join(path.split("-")[1:-1])
                    if valid_path(r_path, adjacency_dict) is False:
                        print("Invalid Path Given %s" % r_path)
                    path_data.append([b, a, r_path])
                    overridden_paths.append((b, a))
                    
    num_unique = len(unique_pairs)
    one_percent = num_unique // 100
    successful_paths = 0
                    
    for i, (n1, n2) in enumerate(unique_pairs):
        try:
            if (i % one_percent) == 0:
                print("Finding path for %d/%d node_pairs: %d successful" % (
                        i,num_unique,successful_paths))
        except ZeroDivisionError:
            print("Few services to patch")
        if (n1, n2) not in overridden_paths:
            
            if use_distance is False:
                path = breadth_first_search(adjacency_dict, n1, n2, node_list)
            else:
                path = dijkstras(adjacency_dict, distance_dict, 
                                 n1, n2, node_list, line_store=working_sequence,
                                 max_depth=max_distance)
            successful_paths += 1
            print(n1,n2,path)
            if path == False:
                if n1 not in dummy_nodes and n2 not in dummy_nodes:
                    unmatched_paths.append([n1,n2])
                    successful_paths -= 1
            else:
                path_data.append([n1, n2, "-".join(list(reversed(path[1:-1])))])
                
        
                
    print("Finished Finding Paths")
        
    return path_data, unmatched_paths
    
# Use the results to correct the sequences and remove any double nodes
def patch_sequences(unpatched_file, patch_override_file, paths, 
                    output_file, progress_inc, patch_others=False):

    # Create a dictionary for all unique pairs of nodes required, 1 for each direction
    #path_dict = dict(list({(n1,n2):l.split("-") for n1,n2,l in paths}.items()) + list({(n2,n1):list(reversed(l.split("-"))) for n1,n2,l in paths}.items()))
    # Only use single direction 
    path_dict = dict(list({(n1,n2):l.split("-") for n1,n2,l in paths}.items()))
    no_path_found = []
    # # Get the user overrides from file 
    # with open(patch_override_file, "r") as file:
        # data = file.readlines()
        # for row in data:
            # if row[0] in ["R", "S"]:
                # row = row.strip("\n")
                # t, a, b, path = row.split(":")
                # path_dict[(a, b)] = [x for x in path.split("-")]
                # if t == "R":
                    # path_dict[(b, a)] = [x for x in reversed(path.split("-"))]
    
    print("Patching File")
    
    with open(unpatched_file, "r") as file:
        reader = csv.reader(file)
        headers = next(reader)
        try:
            node_index = headers.index("Nodes")
        except ValueError:
            node_index = headers.index("nodes")
        if patch_others is True:
            pass_index = headers.index("pass_times")
            tiploc_index = headers.index("route")
        data = [row for row in reader]
    patched_nodes = []
    patched_all_pass_times = []
    patched_all_tiplocs = []
    num_services = len(data)
    for line_index in range(num_services):
    #for seq in (x[node_index].split(',') for x in data):
        
        seq = data[line_index][node_index].split(",")
        if patch_others is True:
            pass_times = data[line_index][pass_index].split(",")
            tiplocs = data[line_index][tiploc_index].split(",")
        # Get indices to remove 
        #rem_indices = [i for i, x in enumerate(seq) if (x == "999999" and i != 0 and i != len(seq)-1)]
        if patch_others is True:
            rem_indices = [i for i, x in enumerate(seq) if x == "999999"]
        else:
            rem_indices = [i for i, x in enumerate(seq) if x == "-1"]
        # Remove any unmatched stations from sequences
        for i in sorted(rem_indices, reverse=True):
            del seq[i]
            if patch_others is True:
                del pass_times[i]
                del tiplocs[i]
        
        # The first and last stations must be stops (no -)
        seq[-1] = seq[-1].strip("-")
        patched_seq = [seq[0].strip("-")]
        if patch_others is True:
            patched_pass_times = [pass_times[0].strip("-")]
            patched_tiplocs = [tiplocs[0]]
            pass_times[-1] = pass_times[-1].strip("-")
        
        for i in range(0, len(seq)-1):
            if seq[i] == seq[i+1] or seq[i+1] == "-1":# If it's a double up: skip 
                continue
            try:
                inter = path_dict[(seq[i], seq[i+1])]
                if inter == [""]:
                    patched_seq += [seq[i+1]]
                    if patch_others is True:
                        patched_pass_times += [pass_times[i+1]]
                        patched_tiplocs += [tiplocs[i+1]]
                else:
                    patched_seq += ["-" + x for x in inter] + [seq[i+1]]
                    if patch_others is True:
                        patched_pass_times += ["-9999" for x in inter] + [pass_times[i+1]]
                        patched_tiplocs += ["XXXXX" for x in inter] + [tiplocs[i+1]]
            except KeyError as e:
                print("Could not find a path for ", e)
                no_path_found.append(e)
                patched_seq += [seq[i+1]]
                if patch_others is True:
                    patched_pass_times += [pass_times[i+1]]
                    patched_tiplocs += [tiplocs[i+1]]
                continue
                
            
        # Make sure that junctions are noted with a -
        if patch_others is True:
            no_stop_indices = [i for i, time in enumerate(patched_pass_times) if time[0] == "-"]
            for index in no_stop_indices:
                if patched_seq[index][0] != "-":
                    patched_seq[index] = "-" + patched_seq[index]
            patched_all_pass_times.append(patched_pass_times)
            patched_all_tiplocs.append(patched_tiplocs)
            
        patched_nodes.append(patched_seq)
#        progress_inc(1.0 / num_services * 100)
            
    print("Saving to new file")
            
    with open(output_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        if patch_others is True:
            for line, patched_seq, pass_times, tiplocs in zip(data, patched_nodes, patched_all_pass_times, patched_all_tiplocs):
                line[node_index] = ",".join(patched_seq)
                line[pass_index] = ",".join(pass_times)
                line[tiploc_index] = ",".join(tiplocs)
                writer.writerow(line)
        else:
            for line, patched_seq in zip(data, patched_nodes):
                line[node_index] = ",".join(patched_seq)
                writer.writerow(line)
                
    print("Finished Patching File")
                
    return no_path_found
                
def patch_selected(node_file, link_file, unpatched_file,
                   patched_file, path_file, override_file, 
                   error_file, type="general", progress_inc=None,
                   working_sequence=[], use_distance=True, max_distance=500):
                   
    if type == "rail":
        patch_others = True 
    else:
        patch_others = False
    # Zone max and zone min determine the nodes which are zones 
    zone_max = 999
    zone_min = 0
    # Progress bar when patching incremented using progress_inc 
    if progress_inc is None:
        progress_inc = lambda x: None
        
    adjacency_dict, node_list, distance_dict, node_num = create_adjacency_dict(
            node_file, link_file, zone_max=zone_max, 
            zone_min=zone_min, is_rail=patch_others)
    if max_distance > node_num:
        max_distance = node_num - 1
        
    print(max_distance)
    
    unique_pairs = get_unique_links(unpatched_file)
    paths, errors = create_paths(adjacency_dict, distance_dict, unique_pairs, 
                                 node_list, override_file, 
                                 working_sequence=working_sequence, 
                                 use_distance=use_distance, 
                                 max_distance=max_distance)
    with open(path_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["A", "B", "PATH"])
        writer.writerows(paths)
    with open(error_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["A", "B"])
        writer.writerows(errors)
    no_path = patch_sequences(unpatched_file, override_file, paths, 
                              patched_file, progress_inc, patch_others=patch_others)
#    for path in no_path:
#        print(path, path in unique_pairs)
    
#    if working_sequence is not None:
#        with open("line_sequences.txt", "w", newline="") as file:
#            for line, end_line in working_sequence:
#                file.write(" ".join(line) + " " + str(end_line) + "\n\r")
    return len(paths), len(errors)
    
def create_override_file(path_file, override_file):
    with open(path_file, "r") as file:
        r = csv.DictReader(file)
        paths = {(row["A"], row["B"]):row["PATH"] for row in r}
        
    with open(override_file, "w", newline="") as file:
        for ab, path in paths.items():
            file.write("S:%s:%s:%s\r\n" % (ab[0], ab[1], path))
     
def distance_breadth_first_search(adjacency_dict, distance_dict, origin, 
                                  destination, node_list, max_depth=100):
    q = Queue()
    q.push((origin,0))
    previous_node = {}
    previous_cost = {}
    visited_nodes = {node:False for node in node_list}
    visited_nodes[origin] = True
    full_paths = {}
    # Check that the destination is connected to the network
    if len(adjacency_dict.get(destination, [])) < 1:
        return False
    while q.is_empty() is False:
        node, depth = q.pop()
        if node not in node_list:
            break # If the node is not in the node_lookup file, skip this - shouldn't happen
        if depth > max_depth:
            continue
        for adj_node in adjacency_dict[node]:
            if adj_node not in node_list: continue
            if visited_nodes[adj_node] == False:
                q.push((adj_node, depth+1))
                visited_nodes[adj_node] = True
                previous_node[adj_node] = node
                previous_cost[adj_node] = distance_dict[(node, adj_node)]
                if adj_node == destination:
                    full_node_path = [adj_node]
                    full_cost = 0
                    start_node = adj_node
                    while start_node != origin:
                        full_node_path.append(previous_node[start_node])
                        full_cost += previous_cost[start_node]
                        start_node = previous_node[start_node]
                    full_paths[full_cost] = full_node_path
                    # If the node is adjacent to the origin -> depth is 1, don't look for any others
                    if depth == 1:
                        break
    if len(full_paths) > 0:
        print(full_paths)
        return full_paths[min(full_paths)]
    else:
        return False
