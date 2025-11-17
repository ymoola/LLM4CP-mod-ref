from cpmpy import *
import json

with open("input_data.json") as f:
    data = json.load(f)

n_slots = data["n_slots"]
n_templates = data["n_templates"]
n_var = data["n_var"]
demand = data["demand"]
alpha_num = data["alpha_num"]
alpha_den = data["alpha_den"]

ub = max(demand)

model = Model()

production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_var, shape=(n_templates, n_var), name="layout")

# All slots filled
for i in range(n_templates):
    model += sum(layout[i, :]) == n_slots

# Demand satisfaction
for v in range(n_var):
    model += sum(production[i] * layout[i, v] for i in range(n_templates)) >= demand[v]

# CR1: Load balance constraint (integer version)
for i in range(n_templates):
    for j in range(n_templates):
        model += production[i] * alpha_den <= production[j] * alpha_num

# Minimize number of printed sheets
model.minimize(sum(production))

model.solve()

print(json.dumps({
    "production": production.value().tolist(),
    "layout": layout.value().tolist()
}))