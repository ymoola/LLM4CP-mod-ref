from cpmpy import *
import json

def build_model(fixed_cost, capacities, supply_cost, revenue):
    n_warehouses = len(capacities)
    n_stores = len(revenue)

    w = intvar(0, n_warehouses-1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")
    min_cost = min(min(row) for row in supply_cost)
    max_cost = max(max(row) for row in supply_cost)
    c = intvar(min_cost, max_cost, shape=n_stores, name="c")
    profit = intvar(-10**9, 10**9, name="profit")

    model = Model()

    for j in range(n_warehouses):
        model += sum(w == j) <= capacities[j]
    for i in range(n_stores):
        model += o[w[i]] == 1
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

    model += profit == sum(revenue) - sum(c) - fixed_cost * sum(o)
    model.maximize(profit)

    return model, w, o, profit

with open('input_data.json') as f:
    data = json.load(f)

model, w, o, profit = build_model(
    data['fixed_cost'],
    data['capacities'],
    data['supply_cost'],
    data['revenue']
)

model.solve(log=None)

solution = {
    "w": [int(v.value()) for v in w],
    "o": [int(v.value()) for v in o],
    "profit": int(profit.value())
}

print(json.dumps(solution))