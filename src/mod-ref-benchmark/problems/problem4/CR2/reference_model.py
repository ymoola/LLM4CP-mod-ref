from cpmpy import *
import json

def build_model(capacities, supply_cost, fixed_cost, allowed):
    n_stores = len(supply_cost)
    n_warehouses = len(supply_cost[0])

    # Variables
    w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")

    model = Model()

    # 1. Feasibility constraint: store i may only be assigned to allowed warehouses
    for i in range(n_stores):
        model += sum((w[i] == j) * allowed[i][j] for j in range(n_warehouses)) == 1

    # 2. Capacity constraints
    for j in range(n_warehouses):
        model += sum(w[i] == j for i in range(n_stores)) <= capacities[j]

    # 3. Warehouse must be open to serve a store
    for i in range(n_stores):
        model += o[w[i]] == 1

    # 4. Supply cost variables
    c = intvar(0, max(max(row) for row in supply_cost), shape=n_stores, name="c")
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

    # 5. Objective: minimize supply cost + opening cost
    total_cost = sum(c) + sum(o[j] * fixed_cost for j in range(n_warehouses))
    model.minimize(total_cost)

    return model, w, o, total_cost


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    capacities = data["capacities"]
    supply_cost = data["supply_cost"]
    fixed_cost = data["fixed_cost"]
    allowed = data["allowed"]

    model, w, o, total_cost = build_model(capacities, supply_cost, fixed_cost, allowed)
    model.solve()

    print(json.dumps({
        "w": w.value().tolist(),
        "o": [int(v) for v in o.value().tolist()],
        "total_cost": int(total_cost.value())
    }))