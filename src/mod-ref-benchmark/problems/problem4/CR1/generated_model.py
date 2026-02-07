from cpmpy import *
import json


def build_model(fixed_cost, capacities, costs, revenue):
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
    sum_revenue = sum(revenue)
    min_profit = sum_revenue - (n_stores * max_cost + fixed_cost * n_warehouses)
    max_profit = sum_revenue - (n_stores * min_cost)
    profit = intvar(min_profit, max_profit, name="profit")

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

    # Objective: maximize profit = revenue - (supply + warehouse opening cost)
    model += (profit == sum(revenue) - (sum(c) + fixed_cost * sum(o)))
    model.maximize(profit)

    return model, w, o, c, profit


with open("input_data.json") as f:
    data = json.load(f)

fixed_cost = data["fixed_cost"]
capacities = data["capacities"]
costs = data["supply_cost"]
revenue = data["revenue"]

model, w, o, c, profit = build_model(fixed_cost, capacities, costs, revenue)

output = {}
if model.solve():
    output["w"] = [int(v) for v in w.value().tolist()]
    output["o"] = [int(v) for v in o.value().tolist()]
    output["profit"] = int(profit.value())

print(json.dumps(output))