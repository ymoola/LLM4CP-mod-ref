import json
from cpmpy import *

with open('input_data.json') as f:
    data = json.load(f)

n_slots = data['n_slots']
n_templates = data['n_templates']
n_var = data['n_var']
demand = data['demand']
alpha_num = data['alpha_num']
alpha_den = data['alpha_den']

ub = max(demand)

production = intvar(1, ub, shape=n_templates, name='production')
layout = intvar(0, n_slots, shape=(n_templates, n_var), name='layout')

model = Model()

for i in range(n_templates):
    model += sum(layout[i]) == n_slots

for v in range(n_var):
    model += sum(production * layout[:, v]) >= demand[v]

for i in range(n_templates):
    for j in range(n_templates):
        if i != j:
            model += production[i] * alpha_den <= production[j] * alpha_num

model.minimize(sum(production))

if model.solve():
    solution = {"var1": production.value().tolist(), "var2": layout.value().tolist()}
    print(json.dumps(solution))
else:
    print(json.dumps({"status": "no solution"}))