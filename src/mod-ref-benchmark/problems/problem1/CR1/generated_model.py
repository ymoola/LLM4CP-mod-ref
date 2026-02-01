"""
Car Sequencing baseline model
--------------------------------
"""

from cpmpy import *
import json

def build_model(at_most, per_slots, demand, requires):
    requires = cpm_array(requires)
    n_cars = sum(demand)
    n_options = len(at_most)
    n_types = len(demand)

    # Decision variables
    sequence = intvar(0, n_types - 1, shape=n_cars, name="sequence")
    setup = boolvar(shape=(n_cars, n_options), name="setup")

    # Model definition
    model = Model()

    # 1. Demand satisfaction
    model += [sum(sequence == t) == demand[t] for t in range(n_types)]

    # 2. Option consistency
    for s in range(n_cars):
        for o in range(n_options):
            model += (setup[s, o] == requires[sequence[s], o])

    # 3. Capacity per option (no more than at_most[o] cars per per_slots[o] window)
    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            slot_range = range(s, s + per_slots[o])
            model += (sum(setup[slot_range, o]) <= at_most[o])

    # 4. Limit consecutive identical car types to at most two
    for s in range(n_cars - 2):
        model += (sequence[s] != sequence[s+1]) | (sequence[s+1] != sequence[s+2])

    return model, sequence

if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)
    at_most = data["at_most"]
    per_slots = data["per_slots"]
    demand = data["demand"]
    requires = data["requires"]

    model, sequence = build_model(at_most, per_slots, demand, requires)
    if model.solve():
        result = {"sequence": sequence.value().tolist()}
        print(json.dumps(result))
    else:
        print(json.dumps({"sequence": None}))