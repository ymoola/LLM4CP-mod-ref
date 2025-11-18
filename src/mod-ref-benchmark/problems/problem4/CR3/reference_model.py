from cpmpy import *
import json

def build_model(capacities, capacity_expanded, upgrade_cost, supply_cost, fixed_cost):
    n_stores = len(supply_cost)
    n_warehouses = len(supply_cost[0])

    # Decision vars
    w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")       # assignment
    o = boolvar(shape=n_warehouses, name="o")                       # open warehouse
    u = boolvar(shape=n_warehouses, name="upgrade")                 # upgraded warehouse

    model = Model()

    # 1. A store can only be supplied by an open warehouse
    for i in range(n_stores):
        model += o[w[i]] == 1

    # 2. True capacity = base_capacity + upgrade * (expanded - base)
    for j in range(n_warehouses):
        cap_base = capacities[j]
        cap_exp = capacity_expanded[j]
        model += sum(w[i] == j for i in range(n_stores)) <= cap_base + u[j] * (cap_exp - cap_base)

    # 3. Supply cost variables
    max_cost = max(max(row) for row in supply_cost)
    c = intvar(0, max_cost, shape=n_stores, name="c")

    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

    # 4. Objective: minimize supply cost + opening cost + upgrade cost
    total_cost = (
        sum(c) +
        sum(o[j] * fixed_cost for j in range(n_warehouses)) +
        sum(u[j] * upgrade_cost[j] for j in range(n_warehouses))
    )

    model.minimize(total_cost)
    return model, w, o, u, total_cost


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, w, o, u, total_cost = build_model(
        data["capacities"],
        data["capacity_expanded"],
        data["upgrade_cost"],
        data["supply_cost"],
        data["fixed_cost"]
    )

    model.solve()

    print(json.dumps({
        "w": w.value().tolist(),
        "o": [int(v) for v in o.value().tolist()],
        "upgrade": [int(v) for v in u.value().tolist()],
        "total_cost": int(total_cost.value())
    }))