from cpmpy import *
import json

def build_model(n_slots, n_templates, n_var, demand):
    ub = max(demand)  # upper bound on production counts

    production = intvar(1, ub, shape=n_templates, name="production")
    layout = intvar(0, n_slots, shape=(n_templates, n_var), name="layout")

    model = Model()

    # 1. All slots in each template must be filled
    for i in range(n_templates):
        model += (sum(layout[i]) == n_slots)
    # Minimum diversity: each template must contain at least 3 distinct variations
    used = [[layout[i, v] > 0 for v in range(n_var)] for i in range(n_templates)]
    for i in range(n_templates):
        model += (sum(used[i]) >= 3)

    # 2. Demand satisfaction
    for v in range(n_var):
        model += (sum(production * layout[:, v]) >= demand[v])

    # 3. Objective: minimize number of printed sheets
    model.minimize(sum(production))

    return model, production, layout

if __name__ == "__main__":
    with open("input_data.json", "r") as f:
        data = json.load(f)
    n_slots = data["n_slots"]
    n_templates = data["n_templates"]
    n_var = data["n_var"]
    demand = data["demand"]

    model, production, layout = build_model(n_slots, n_templates, n_var, demand)
    if not model.solve():
        raise ValueError("No solution found")
    result = {
        "layout": layout.value().tolist(),
        "production": production.value().tolist()
    }
    print(json.dumps(result))