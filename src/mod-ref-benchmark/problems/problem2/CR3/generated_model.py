from cpmpy import *
import json

def build_model(n_slots, n_templates, n_var, demand):
    ub = max(demand)
    production = intvar(1, ub, shape=n_templates, name="production")
    layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")
    max_load = intvar(0, ub, name="max_load")
    model = Model()
    for i in range(n_templates):
        model += (sum(layout[i]) == n_slots)
    for v in range(n_var):
        model += (sum(production * layout[:, v]) >= demand[v])
    for i in range(n_templates):
        model += (production[i] <= max_load)
    model.minimize(max_load)
    return model, production, layout, max_load

with open("input_data.json", "r") as f:
    data = json.load(f)

n_slots = data["n_slots"]
n_templates = data["n_templates"]
n_var = data["n_var"]
demand = data["demand"]

model, production, layout, max_load = build_model(n_slots, n_templates, n_var, demand)
model.solve()
result = {
    "production": production.value().tolist(),
    "layout": layout.value().tolist(),
    "max_load": int(max_load.value())
}
print(json.dumps(result))