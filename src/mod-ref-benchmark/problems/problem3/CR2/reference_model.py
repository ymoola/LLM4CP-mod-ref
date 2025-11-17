from cpmpy import *
import json

# Load data
with open("input_data.json") as f:
    data = json.load(f)

n_tasks = data["n_tasks"]
shifts = data["shifts"]
shift_costs = data["shift_costs"]

n_shifts = len(shifts)

assert n_shifts == len(shift_costs), f"lengths not the same, got {len(shift_costs)}"

# Decision variables: x[i] = 1 iff shift i is selected
x = boolvar(shape=n_shifts, name="x")

model = Model()

# Coverage: each task covered exactly once
for t in range(n_tasks):
    covering = [i for i in range(n_shifts) if t in shifts[i]]
    model += sum(x[i] for i in covering) == 1

# Objective: minimize total cost
total_cost = sum(x[i] * shift_costs[i] for i in range(n_shifts))
model.minimize(total_cost)


if not model.solve():
    print("UNSAT INSTANCE — no feasible assignment of shifts covers every task exactly once")
    exit()

print(json.dumps({
    "x": [int(val) for val in x.value().tolist()],
    "total_cost": int(total_cost.value())
}))