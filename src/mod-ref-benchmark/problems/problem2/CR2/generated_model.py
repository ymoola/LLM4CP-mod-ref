import json
from cpmpy import *

data = json.load(open('input_data.json'))
n_slots = data['n_slots']
n_templates = data['n_templates']
n_var = data['n_var']
demand = data['demand']

ub = max(demand) if demand else 0

production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")

model = Model()

for i in range(n_templates):
    model += sum(layout[i]) == n_slots

for v in range(n_var):
    model += sum(production * layout[:, v]) >= demand[v]

for i in range(n_templates):
    model += sum(layout[i, v] > 0 for v in range(n_var)) >= 3

for i in range(n_templates - 1):
    model += production[i] <= production[i + 1]

model.minimize(sum(production))

model.solve()

layout_vals = [[int(layout[i, v].value()) for v in range(n_var)] for i in range(n_templates)]
production_vals = [int(production[i].value()) for i in range(n_templates)]

print(json.dumps({"layout": layout_vals, "production": production_vals}))