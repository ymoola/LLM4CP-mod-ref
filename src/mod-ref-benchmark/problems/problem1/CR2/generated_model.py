from cpmpy import *
import json

# Load data
with open('input_data.json') as f:
    data = json.load(f)
at_most = data['at_most']
per_slots = data['per_slots']
demand = data['demand']
requires = data['requires']
gap_limit = data['gap_limit']

requires = cpm_array(requires)
n_cars = sum(demand)
n_options = len(at_most)
n_types = len(demand)

# Decision variables
sequence = intvar(0, n_types - 1, shape=n_cars, name="sequence")
setup = boolvar(shape=(n_cars, n_options), name="setup")

# Model
model = Model()

# 1. Demand satisfaction
model += [sum(sequence == t) == demand[t] for t in range(n_types)]

# 2. Option consistency
for s in range(n_cars):
    for o in range(n_options):
        model += (setup[s, o] == requires[sequence[s], o])

# 3. Capacity per option
for o in range(n_options):
    for s in range(n_cars - per_slots[o]):
        slot_range = range(s, s + per_slots[o])
        model += (sum(setup[slot_range, o]) <= at_most[o])

# 4. Spacing constraint: each type appears at least once in every window of size gap_limit
if gap_limit <= n_cars:
    for t in range(n_types):
        for s in range(n_cars - gap_limit + 1):
            model += (sum(sequence[s:s+gap_limit] == t) >= 1)

# Solve
model.solve()

# Prepare solution
solution = {"sequence": [int(v) for v in sequence.value()]}
print(json.dumps(solution))
