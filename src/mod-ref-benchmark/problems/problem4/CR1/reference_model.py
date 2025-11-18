from cpmpy import *
import json

def build_model(fixed_cost, capacities, supply_cost, revenue):
    n_warehouses = len(capacities)
    n_stores = len(supply_cost)

    # Decision variables
    w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")
    c = intvar(0, max(max(row) for row in supply_cost), shape=n_stores, name="c")

    model = Model()

    # 1. Capacity constraints
    for j in range(n_warehouses):
        model += sum(w[i] == j for i in range(n_stores)) <= capacities[j]

    # 2. Store must be served by an open warehouse
    for i in range(n_stores):
        model += o[w[i]] == 1

    # 3. Compute supply cost c[i]
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

    # Objective: maximize revenue - (warehouse fixed cost + supply costs)
    total_revenue = sum(revenue[i] for i in range(n_stores))
    total_opening_cost = sum(o[j] * fixed_cost for j in range(n_warehouses))
    total_supply_cost = sum(c)

    profit = total_revenue - total_opening_cost - total_supply_cost
    model.maximize(profit)

    return model, w, o, profit


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, w, o, profit = build_model(
        data["fixed_cost"],
        data["capacities"],
        data["supply_cost"],
        data["revenue"]
    )

    model.solve()

    print(json.dumps({
        "w": w.value().tolist(),
        "o": [int(v) for v in o.value().tolist()],
        "profit": int(profit.value())
    }))