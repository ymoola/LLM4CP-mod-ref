from cpmpy import *
import json

# Load input data
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

# Each type must appear exactly according to demand
model += [sum(sequence == t) == demand[t] for t in range(n_types)]

# Ensure setup matches the car type’s requirements
for s in range(n_cars):
    for o in range(n_options):
        model += (setup[s, o] == requires[sequence[s], o])

# Capacity constraints for each option
for o in range(n_options):
    for s in range(n_cars - per_slots[o]):
        model += (sum(setup[s:s+per_slots[o], o]) <= at_most[o])

# Solve
model.solve()
print(json.dumps({"sequence": sequence.value().tolist()}))