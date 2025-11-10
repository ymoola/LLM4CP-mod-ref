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

model = Model()
model += [sum(sequence == t) == demand[t] for t in range(n_types)]
for s in range(n_cars):
    for o in range(n_options):
        model += (setup[s, o] == requires[sequence[s], o])

# CR1: tighten air-conditioning constraint
for s in range(n_cars - 4):
    model += (sum(setup[s:s+4, 0]) <= 1)

for o in range(1, n_options):
    for s in range(n_cars - per_slots[o]):
        model += (sum(setup[s:s+per_slots[o], o]) <= at_most[o])

model.solve()
print(json.dumps({"sequence": sequence.value().tolist()}))