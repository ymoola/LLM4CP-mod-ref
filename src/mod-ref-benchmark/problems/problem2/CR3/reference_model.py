from cpmpy import *
import json

with open("input_data.json") as f:
    data = json.load(f)

n_slots = data["n_slots"]
n_templates = data["n_templates"]
n_var = data["n_var"]
demand = data["demand"]

ub = max(demand)

model = Model()

production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_var, shape=(n_templates, n_var), name="layout")
max_load = intvar(1, ub, name="max_load")

# Fill slots
for i in range(n_templates):
    model += sum(layout[i, :]) == n_slots

# Demand satisfaction
for v in range(n_var):
    model += sum(production[i] * layout[i, v] for i in range(n_templates)) >= demand[v]

# CR3: max_load is maximum of production
for i in range(n_templates):
    model += production[i] <= max_load

# Objective: minimize the maximum load
model.minimize(max_load)

model.solve()

print(json.dumps({
    "production": production.value().tolist(),
    "layout": layout.value().tolist(),
    "max_load": int(max_load.value())
}))