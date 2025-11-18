import json
from cpmpy import *

def build_model(capacities, supply_cost, allowed, fixed_cost):
    n_warehouses = len(capacities)
    n_stores = len(supply_cost)
    w = intvar(0, n_warehouses-1, shape=n_stores, name="w")
    o = boolvar(shape=n_warehouses, name="o")
    min_cost = min(min(row) for row in supply_cost)
    max_cost = max(max(row) for row in supply_cost)
    c = intvar(min_cost, max_cost, shape=n_stores, name="c")
    model = Model()
    for j in range(n_warehouses):
        model += sum(w == j) <= capacities[j]
    for i in range(n_stores):
        model += o[w[i]] == 1
    for i in range(n_stores):
        model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))
    for i in range(n_stores):
        for j in range(n_warehouses):
            if allowed[i][j] == 0:
                model += w[i] != j
    model.minimize(sum(c) + fixed_cost * sum(o))
    return model, w, o, c

if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)
    capacities = data["capacities"]
    supply_cost = data["supply_cost"]
    allowed = data["allowed"]
    fixed_cost = data.get("fixed_cost", 0)
    model, w, o, c = build_model(capacities, supply_cost, allowed, fixed_cost)
    if model.solve():
        w_sol = [int(v) for v in w.value()]
        o_sol = [int(v) for v in o.value()]
        c_sol = [int(v) for v in c.value()]
        total_cost = sum(c_sol) + fixed_cost * sum(o_sol)
        print(json.dumps({"w": w_sol, "o": o_sol, "total_cost": total_cost}))
