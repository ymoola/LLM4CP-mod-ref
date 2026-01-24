from cpmpy import *
import json

data = json.load(open('input_data.json'))
fixed_cost = data['fixed_cost']
capacities = data['capacities']
capacity_expanded = data['capacity_expanded']
upgrade_cost = data['upgrade_cost']
supply_cost = data['supply_cost']

n_warehouses = len(capacities)
n_stores = len(supply_cost)

w = intvar(0, n_warehouses - 1, shape=n_stores, name="w")
o = boolvar(shape=n_warehouses, name="o")
upgrade = boolvar(shape=n_warehouses, name="upgrade")

min_cost = min(min(row) for row in supply_cost)
max_cost = max(max(row) for row in supply_cost)
c = intvar(min_cost, max_cost, shape=n_stores, name="c")

model = Model()

for j in range(n_warehouses):
    model += sum(w == j) <= capacities[j] + upgrade[j] * (capacity_expanded[j] - capacities[j])

for i in range(n_stores):
    model += o[w[i]] == 1

for j in range(n_warehouses):
    model += upgrade[j] <= o[j]

for i in range(n_stores):
    model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

model.minimize(sum(c) + fixed_cost * sum(o) + upgrade_cost * sum(upgrade))

model.solve()

w_vals = [int(v) for v in w.value()]
o_vals = [int(v) for v in o.value()]
upgrade_vals = [int(v) for v in upgrade.value()]
total_cost = sum(c.value()) + fixed_cost * sum(o_vals) + upgrade_cost * sum(upgrade_vals)

print(json.dumps({"w": w_vals, "o": o_vals, "upgrade": upgrade_vals, "total_cost": total_cost}))