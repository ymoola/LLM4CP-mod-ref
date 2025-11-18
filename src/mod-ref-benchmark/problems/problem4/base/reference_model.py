from cpmpy import *
import json


def build_model(fixed_cost, capacities, costs):
    """
    Build the CPMPy model for the Warehouse Location Problem.
    """
    n_warehouses = len(capacities)
    n_stores = len(costs)

    # Decision variables
    w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")

    min_cost = min(min(row) for row in costs)
    max_cost = max(max(row) for row in costs)
    c = intvar(min_cost, max_cost, shape=n_stores, name="c")

    model = Model()

    # 1. Capacity constraints
    for j in range(n_warehouses):
        model += sum(w == j) <= capacities[j]

    # 2. Supplier warehouse must be open
    for i in range(n_stores):
        model += o[w[i]] == 1

    # 3. Assign supply cost c[i] = costs[i][w[i]]
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * costs[i][j] for j in range(n_warehouses))

    # Objective: minimize supply + warehouse opening cost
    model.minimize(sum(c) + fixed_cost * sum(o))

    return model, w, o, c



if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    fixed_cost = data["fixed_cost"]
    capacities = data["capacities"]
    costs = data["supply_cost"]

    model, w, o, c = build_model(fixed_cost, capacities, costs)

    model.solve()

    print(json.dumps({
        "w": w.value().tolist(),
        "o": [int(val) for val in o.value().tolist()],
        "c": c.value().tolist(),
        "total_cost": int(sum(c.value()) + fixed_cost * sum(o.value()))
    }))