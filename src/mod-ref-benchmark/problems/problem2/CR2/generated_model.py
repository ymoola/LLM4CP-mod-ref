from cpmpy import *
import json

# Load parameters
with open('input_data.json', 'r') as f:
    data = json.load(f)

n_slots = data['n_slots']
n_templates = data['n_templates']
n_var = data['n_var']
demand = data['demand']

ub = max(demand)

# Decision variables
production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")

model = Model()

# 1. All slots in each template must be filled
for i in range(n_templates):
    model += (sum(layout[i]) == n_slots)

# 2. Demand satisfaction
for v in range(n_var):
    model += (sum(production * layout[:, v]) >= demand[v])

# 3. Minimum diversity: at least three distinct variations per template
for i in range(n_templates):
    model += (sum([layout[i][v] > 0 for v in range(n_var)]) >= 3)

# 4. Objective: minimize number of printed sheets
model.minimize(sum(production))

# Solve
model.solve(log_output=False)

# Extract solution
layout_solution = [[layout[i, v].as_long() for v in range(n_var)] for i in range(n_templates)]
production_solution = [production[i].as_long() for i in range(n_templates)]

print(json.dumps({"var1": layout_solution, "var2": production_solution}))
