import json
from cpmpy import *

data = json.load(open('input_data.json'))
n_slots = data['n_slots']
n_templates = data['n_templates']
n_var = data['n_var']
demand = data['demand']

ub = max(demand) if demand else 1

production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")
max_load = intvar(1, ub, name="max_load")

model = Model()

# Slot usage constraint
for i in range(n_templates):
    model += (sum(layout[i]) == n_slots)
    model += (production[i] <= max_load)

# Demand satisfaction
for v in range(n_var):
    model += (sum(production * layout[:, v]) >= demand[v])

# Objective: minimize maximum production load
model.minimize(max_load)

if model.solve():
    out = {
        "production": production.value().tolist(),
        "layout": layout.value().tolist(),
        "max_load": max_load.value()
    }
else:
    out = {}
print(json.dumps(out))