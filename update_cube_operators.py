# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 16:42:46 2019

@author: japeach
"""

import csv

old_lin = "rail_lin.lin"
new_lin = "updated_rail_lin.lin"

old_operators = "Operator_Codes.csv"
new_operators = "TMfS18 Updated Operator Lookup.csv"

def update_cube_operators(old_lin, new_lin, new_operators, old_operators):
    with open(old_lin, "r") as file:
        init_data = [x for x in file.readlines()]
    with open(old_operators, "r") as file:
        r = csv.reader(file)
        old_ops = {x[2]:x[1] for x in r}
    with open(new_operators, "r") as file:
        r = csv.reader(file)
        new_ops = {x[1]:x[2] for x in r}
        
    op_lookup = {"OPERATOR=%s" % old_num:"OPERATOR=%s" % new_ops.get(old_ops[old_num]) 
                    for old_num, old_code in old_ops.items()}
        
    op_idxs = [i for i, x in enumerate(init_data) if "OPERATOR" in x]
    
    replaced_ops = [init_data[idx].split(", ") for idx in op_idxs]
    for i in range(len(replaced_ops)):
        for j in range(len(replaced_ops[i])):
            if replaced_ops[i][j].strip() in op_lookup:
                old_op = replaced_ops[i][j].strip()
                new_op = op_lookup[replaced_ops[i][j].strip()]
            else:
                old_op = replaced_ops[i][j].strip()
                new_op = old_op
            replaced_ops[i][j] = replaced_ops[i][j].replace(old_op, new_op)
        replaced_ops[i] = ", ".join(replaced_ops[i])
    
    final_data = [x if i not in op_idxs else replaced_ops[op_idxs.index(i)] 
                                for i, x in enumerate(init_data)]
    
    with open(new_lin, "w", newline="") as file:
        for line in final_data:
            file.write(line)
        
