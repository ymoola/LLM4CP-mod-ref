from cpmpy import *
import json

with open("input_data.json") as f:
    data = json.load(f)

at_most = data["at_most"]
per_slots = data["per_slots"]
demand = data["demand"]
requires = cpm_array(data["requires"])

n_cars = sum(demand)
n_options = len(at_most)
n_types = len(demand)

sequence = intvar(0, n_types - 1, shape=n_cars, name="sequence")
setup = boolvar(shape=(n_cars, n_options), name="setup")
viol = boolvar(shape=(n_options, n_cars), name="viol")  # new relaxation variables

model = Model()

# Base constraints
model += [sum(sequence == t) == demand[t] for t in range(n_types)]
for s in range(n_cars):
    for o in range(n_options):
        model += (setup[s, o] == requires[sequence[s], o])

# Soft capacity constraints with violation allowance
for o in range(n_options):
    for s in range(n_cars - per_slots[o]):
        slot_range = range(s, s + per_slots[o])
        model += (sum(setup[slot_range, o]) <= at_most[o] + viol[o, s])

# Objective: minimize total violations
model.minimize(sum(viol))

model.solve()

print(json.dumps({
    "sequence": sequence.value().tolist(),
    "total_violations": int(sum(viol.value().flatten()))
}))