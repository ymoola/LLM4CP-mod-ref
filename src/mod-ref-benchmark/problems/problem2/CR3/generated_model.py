import json
from cpmpy import *

# Load parameters from input_data.json
with open('input_data.json', 'r') as f:
    data = json.load(f)

n_slots = data['n_slots']
n_templates = data['n_templates']
n_var = data['n_var']
demand = data['demand']

ub = max(demand)  # upper bound on production counts

# Decision variables
production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")
max_load = intvar(1, ub, name="max_load")

model = Model()

# 1. All slots in each template must be filled
for i in range(n_templates):
    model += (sum(layout[i]) == n_slots)

# 2. Demand satisfaction
for v in range(n_var):
    model += (sum(production * layout[:, v]) >= demand[v])

# 3. max_load constraints
for i in range(n_templates):
    model += (production[i] <= max_load)

# Objective: minimize the maximum production load
model.minimize(max_load)

# Solve
model.solve(log=False)

# Extract solution
production_sol = [int(production[i].value()) for i in range(n_templates)]
layout_sol = [[int(layout[i, j].value()) for j in range(n_var)] for i in range(n_templates)]
max_load_sol = int(max_load.value())

# Output solution in required JSON format
print(json.dumps({
    "production": production_sol,
    "layout": layout_sol,
    "max_load": max_load_sol
}))