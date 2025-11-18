import json
from cpmpy import *

with open('input_data.json') as f:
    data = json.load(f)

fixed_cost = data['fixed_cost']
capacities = data['capacities']
capacity_expanded = data['capacity_expanded']
upgrade_cost = data['upgrade_cost']
supply_cost = data['supply_cost']

n_warehouses = len(capacities)
n_stores = len(supply_cost)

w = intvar(0, n_warehouses - 1, shape=n_stores, name='w')
o = boolvar(shape=n_warehouses, name='o')
upgrade = boolvar(shape=n_warehouses, name='upgrade')

min_cost = min(min(row) for row in supply_cost)
max_cost = max(max(row) for row in supply_cost)
c = intvar(min_cost, max_cost, shape=n_stores, name='c')

model = Model()

for j in range(n_warehouses):
    delta = capacity_expanded[j] - capacities[j]
    model += sum(w == j) <= capacities[j] + upgrade[j] * delta

for i in range(n_stores):
    model += o[w[i]] == 1

for j in range(n_warehouses):
    model += upgrade[j] <= o[j]

for i in range(n_stores):
    model += c[i] == sum((w[i] == j) * supply_cost[i][j] for j in range(n_warehouses))

model.minimize(sum(c) + fixed_cost * sum(o) + upgrade_cost * sum(upgrade))

model.solve(log_output=False)

solution = {
    'w': [int(v) for v in w.value()],
    'o': [int(v) for v in o.value()],
    'upgrade': [int(v) for v in upgrade.value()],
    'total_cost': int(model.objective_value())
}

print(json.dumps(solution))