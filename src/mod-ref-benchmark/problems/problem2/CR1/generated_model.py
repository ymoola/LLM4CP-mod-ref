from cpmpy import *
import json

def build_model(n_slots, n_templates, n_var, demand, alpha_num, alpha_den):
    """
    Base CP model for the Template Design problem.
    - n_slots: integer, slots per template
    - n_templates: integer, number of templates
    - n_var: integer, number of variations
    - demand: list[int], demand per variation
    - alpha_num: integer numerator of load-balance ratio
    - alpha_den: integer denominator of load-balance ratio (>0)
    """
    assert alpha_den > 0, "alpha_den must be > 0"
    assert alpha_num >= alpha_den, "alpha_num/alpha_den must be >= 1"

    ub = max(demand)  # upper bound on production counts

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

    # 2b. Load balancing between templates
    for i in range(n_templates):
        for j in range(n_templates):
            model += (production[i] * alpha_den <= production[j] * alpha_num)

    # 3. Objective: minimize number of printed sheets
    model.minimize(sum(production))

    return model, production, layout

with open("input_data.json", "r") as f:
    data = json.load(f)

n_slots = data["n_slots"]
n_templates = data["n_templates"]
n_var = data["n_var"]
demand = data["demand"]
alpha_num = data["alpha_num"]
alpha_den = data["alpha_den"]

model, production, layout = build_model(n_slots, n_templates, n_var, demand, alpha_num, alpha_den)

if model.solve():
    production_sol = [int(production[i].value()) for i in range(n_templates)]
    layout_sol = [[int(layout[i, j].value()) for j in range(n_var)] for i in range(n_templates)]
    print(json.dumps({"production": production_sol, "layout": layout_sol}))
else:
    print(json.dumps({"production": [], "layout": []}))