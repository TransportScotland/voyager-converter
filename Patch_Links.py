import os
import csv
import sqlite3

links_file = "links.csv"
filler_file = "CSTM_Network_Filler_V1.1.txt"
output_file = "links_test_patched.txt"
main_in = "mca_out_head.csv"

class connection_container:
    def __init__(self, start, end, link=[], flag=''):
        self.first = start
        self.last = end
        self.inter = link
        self.type = flag
        self.exists = False
    def add_inter(self, link):
        if link.type == 'R':
            if self.first == link.first and self.last == link.last:
                self.inter = link.inter
        elif link.type == 'P':
            first_i = -1
            last_i = -1
            try:
                first_i = link.inter.index(self.first)
                last_i = link.inter.index(self.last)

                # If there are no intermediates, skip
                if abs(first_i - last_i) == 1:
                    return
                if first_i < last_i:
                    self.inter = link.inter[first_i+1:last_i]
                    self.inter = ["-" + x for x in self.inter]
                elif first_i > last_i:
                    self.inter = ["-" + link.inter[i] for i in range(first_i-1, last_i,-1)]
                #print(self.first, self.last, self.inter, link.inter[first_i], link.inter[last_i])

            except ValueError:
                return


# Create a file containing all unique 2 node sequences for patching later
# unpatched_file = all filtered services
# unique_links = file to write all the unique links in the services
# lookup_file = file containing link paths in the model
# patched_file = file to write the servvices with patched nodes to
def get_unique_links(unpatched_file, lookup_file, patched_file, log):

    log.add_message("Patching Node Routes\n")

    unique_links = "unique_links.txt"

    #Nodes are the final column stored in the file
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    try:
        with open(unpatched_file, "r") as db:
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
                with open(unique_links, "w", newline="") as out:
                    writer = csv.writer(out)
                    writer.writerows(links)
            except IOError:
                log.add_message("Failed to access Station output file\nCheck that it is not already open\n")
                return
    except IOError:
        log.add_message("Generate an unpatched file first by importing and filtering data in the 'Import Rail' tab", color="RED")
    conn.close()

    match_all_links(unpatched_file, unique_links, lookup_file, patched_file, log)

def match_all_links(unpatched_file, unique_links, lookup_file, patched_file, log):

    link_pairs = []
    filler_pairs = []
    new_link_lookup = "intermediate_link_lookup.txt"

    # Load in unique links that are needed
    with open(unique_links,'r') as file:
        for line in file:
            line = line.split(',')
            line = [x.rstrip('\n') for x in line]
            link_pairs.append(connection_container(line[0],line[1]))

    #Load in link lookup file
    with open(lookup_file, 'r') as file:
        headers = next(file)
        for line in file:
            line = line.split(',')
            line = [x.rstrip('\n') for x in line]
            if line[0] == "P":
                filler_pairs.append(connection_container(line[1],line[2],line[1:],line[0]))
            else:
                filler_pairs.append(connection_container(line[1],line[2],line[3:],line[0]))

    # for each unique pair search for the intermediate nodes
    for pair in link_pairs:
        for filler_pair in filler_pairs:
            pair.add_inter(filler_pair)

    # Write to a new lookup file
    with open(new_link_lookup, 'w') as file:
        for pair in link_pairs:
            if pair.inter == []:
                file.write(str(pair.first) + "," + \
                       str(pair.last) + \
                       '\n')
            else:
                file.write(str(pair.first) + "," + \
                           str(pair.last) + "," + \
                           ','.join(pair.inter) + '\n')

    patch_all_routes(unpatched_file, new_link_lookup, patched_file, log)

def patch_all_routes(unpatched_file, link_lookup, patched_file, log):

    conn = sqlite3.connect(':memory:')
    c = conn.cursor()

    columns = []

    with open(unpatched_file, 'r') as file:
        reader = csv.reader(file)
        columns = next(reader)
        query = "INSERT INTO all_serv({0}) VALUES ({1})"
        create_query = "CREATE TABLE all_serv (" + ','.join(columns) + ")"
        query = query.format(','.join(columns), ','.join('?' * len(columns)))
        c.execute(create_query)
        for data in reader:
            c.execute(query, data)

    lookups = []
    with open(link_lookup, 'r')as file:
        for line in file:
            line = line.split(',')
            line = [x.rstrip('\n') for x in line]
            lookups.append(connection_container(line[0],line[1],line[2:]))

    c.execute("SELECT stat_seq_nodes FROM all_serv")
    routes_patch = [[x[0],[]] for x in c.fetchall()]
    for route in routes_patch:
        original = route[0].split(', ')
        new = []
        for index in range(0,len(original) - 1):
            new.append(original[index])
            for lookup in lookups:
                if lookup.first == original[index] and lookup.last == original[index+1]:
                    for node in lookup.inter:
                        new.append(node)
        new.append(original[-1])
        route[1] = ', '.join(new)

    c.execute("CREATE TABLE patched (old, new)")
    c.executemany("INSERT INTO patched VALUES (?,?)",routes_patch)
    query = "SELECT {0},patched.new FROM all_serv INNER JOIN patched ON all_serv.stat_seq_nodes == patched.old"
    query = query.format(','.join(columns))
    c.execute(query)
    data = c.fetchall()

    with open(patched_file, "w",newline='') as csvfile:
        writer = csv.writer(csvfile)
        columns.append("patched_nodes")
        writer.writerow(columns)
        writer.writerows(data)

    conn.close()

    log.add_message("Finished Patching Routes",color="GREEN")
