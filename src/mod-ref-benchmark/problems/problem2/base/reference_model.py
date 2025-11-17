from cpmpy import *
import json

def build_model(n_slots, n_templates, n_var, demand):
    """
    Base CP model for the Template Design problem.
    - n_slots: integer, slots per template
    - n_templates: integer, number of templates
    - n_var: integer, number of variations
    - demand: list[int], demand per variation
    """

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

    # 3. Objective: minimize number of printed sheets
    model.minimize(sum(production))

    return model, production, layout


if __name__ == "__main__":
    # Load input data
    with open("input_data.json") as f:
        data = json.load(f)

    n_slots = data["n_slots"]
    n_templates = data["n_templates"]
    n_var = data["n_var"]
    demand = data["demand"]

    model, production, layout = build_model(
        n_slots, n_templates, n_var, demand
    )

    model.solve()

    print(json.dumps({
        "production": production.value().tolist(),
        "layout": layout.value().tolist()
    }))