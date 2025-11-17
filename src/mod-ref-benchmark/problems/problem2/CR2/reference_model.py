from cpmpy import *
import json

# Load data
with open("input_data.json") as f:
    data = json.load(f)

n_slots = data["n_slots"]
n_templates = data["n_templates"]
n_var = data["n_var"]
demand = data["demand"]

# Upper bound for production
ub = max(demand)

# Decision variables
production = intvar(1, ub, shape=n_templates, name="production")
layout = intvar(0, n_var, shape=(n_templates, n_var), name="layout")

model = Model()

# 1. Slot-fill constraint
for i in range(n_templates):
    model += (sum(layout[i, :]) == n_slots)

# 2. Demand satisfaction
for v in range(n_var):
    model += (sum(production * layout[:, v]) >= demand[v])

# === CR2: Minimum Template Diversity ===
# Each template must contain at least 3 variations
for i in range(n_templates):
    model += (sum(layout[i, v] > 0 for v in range(n_var)) >= 3)

# Objective: minimize total production
model.minimize(sum(production))

model.solve()

print(json.dumps({
    "layout": layout.value().tolist(),
    "production": production.value().tolist()
}))