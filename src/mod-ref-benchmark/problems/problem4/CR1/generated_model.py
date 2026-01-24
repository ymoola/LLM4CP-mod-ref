import json
from cpmpy import *

with open('input_data.json') as f:
    data = json.load(f)

fixed_cost = data['fixed_cost']
capacities = data['capacities']
supply_cost = data['supply_cost']
revenue = data['revenue']

n_warehouses = len(capacities)
n_stores = len(revenue)

w = intvar(0, n_warehouses - 1, shape=n_stores, name='w')
o = boolvar(shape=n_warehouses, name='o')
min_cost = min(min(row) for row in supply_cost)
max_cost = max(max(row) for row in supply_cost)
c = intvar(min_cost, max_cost, shape=n_stores, name='c')

model = Model()

for j in range(n_warehouses):
    model += sum(w == j) <= capacities[j]

for i in range(n_stores):
    model += o[w[i]] == 1

for i in range(n_stores):
    model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

total_revenue = sum(revenue)
model.maximize(total_revenue - sum(c) - fixed_cost * sum(o))

if model.solve():
    w_vals = [int(v.value()) for v in w]
    o_vals = [int(v.value()) for v in o]
    profit_val = int(total_revenue - sum(v.value() for v in c) - fixed_cost * sum(o_vals))
    output = {"w": w_vals, "o": o_vals, "profit": profit_val}
    print(json.dumps(output))
else:
    print(json.dumps({"w": [], "o": [], "profit": None}))