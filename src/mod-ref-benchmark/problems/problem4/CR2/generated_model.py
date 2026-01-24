import json
from cpmpy import *

with open('input_data.json') as f:
    data = json.load(f)

fixed_cost = data['fixed_cost']
capacities = data['capacities']
supply_cost = data['supply_cost']
allowed = data['allowed']

n_warehouses = len(capacities)
n_stores = len(supply_cost)

w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
o = boolvar(shape=n_warehouses, name="o")

min_cost = min(min(row) for row in supply_cost)
max_cost = max(max(row) for row in supply_cost)
c = intvar(min_cost, max_cost, shape=n_stores, name="c")

model = Model()

# Capacity constraints
for j in range(n_warehouses):
    model += sum(w == j) <= capacities[j]

# Allowed warehouse constraints
for i in range(n_stores):
    for j in range(n_warehouses):
        if allowed[i][j] == 0:
            model += w[i] != j

# Supplier must be open
for i in range(n_stores):
    model += o[w[i]] == 1

# Supply cost assignment
for i in range(n_stores):
    model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

# Objective
model.minimize(sum(c) + fixed_cost * sum(o))

if model.solve():
    w_vals = w.value().tolist()
    o_vals = [int(v) for v in o.value()]
    total_cost = int(sum(c.value()) + fixed_cost * sum(o_vals))
    output = {
        "w": w_vals,
        "o": o_vals,
        "total_cost": total_cost
    }
    print(json.dumps(output))
else:
    print(json.dumps({"status":"No solution"}))
