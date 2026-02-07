from cpmpy import *
import json


def build_model(fixed_cost, capacities, costs, capacity_expanded, upgrade_cost):
    """
    Build the CPMPy model for the Warehouse Location Problem.
    """
    n_warehouses = len(capacities)
    n_stores = len(costs)

    # Decision variables
    w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")
    upgrade = boolvar(shape=n_warehouses, name="upgrade")

    min_cost = min(min(row) for row in costs)
    max_cost = max(max(row) for row in costs)
    c = intvar(min_cost, max_cost, shape=n_stores, name="c")

    model = Model()

    # 1. Capacity constraints
    for j in range(n_warehouses):
        model += sum(w == j) <= capacities[j] + (capacity_expanded[j] - capacities[j]) * upgrade[j]

    # 2. Supplier warehouse must be open
    for i in range(n_stores):
        model += o[w[i]] == 1

    for j in range(n_warehouses):
        model += upgrade[j] <= o[j]

    # 3. Assign supply cost c[i] = costs[i][w[i]]
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * costs[i][j] for j in range(n_warehouses))

    # Objective: minimize supply + warehouse opening cost
    if isinstance(upgrade_cost, (list, tuple)):
        upgrade_term = sum(upgrade_cost[j] * upgrade[j] for j in range(n_warehouses))
    else:
        upgrade_term = upgrade_cost * sum(upgrade)
    model.minimize(sum(c) + fixed_cost * sum(o) + upgrade_term)

    return model, w, o, c, upgrade


with open("input_data.json", "r") as f:
    data = json.load(f)

fixed_cost = data["fixed_cost"]
capacities = data["capacities"]
capacity_expanded = data["capacity_expanded"]
upgrade_cost = data["upgrade_cost"]
costs = data["supply_cost"]

model, w, o, c, upgrade = build_model(fixed_cost, capacities, costs, capacity_expanded, upgrade_cost)
has_solution = model.solve()

if has_solution:
    w_val = [int(v) for v in w.value().tolist()]
    o_val = [int(v) for v in o.value().tolist()]
    upgrade_val = [int(v) for v in upgrade.value().tolist()]
    if isinstance(upgrade_cost, (list, tuple)):
        upgrade_total = sum(upgrade_cost[j] * upgrade_val[j] for j in range(len(upgrade_val)))
    else:
        upgrade_total = upgrade_cost * sum(upgrade_val)
    total_cost = int(sum(c.value()) + fixed_cost * sum(o_val) + upgrade_total)
else:
    w_val = []
    o_val = []
    upgrade_val = []
    total_cost = None

print(json.dumps({"w": w_val, "o": o_val, "upgrade": upgrade_val, "total_cost": total_cost}))