import json
from cpmpy import *

def build_model(at_most, per_slots, demand, requires, gap_limit):
    requires = cpm_array(requires)
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

    effective_gap = min(gap_limit, n_cars) if n_cars > 0 else 0
    if effective_gap > 0:
        for t in range(n_types):
            for s in range(n_cars - effective_gap + 1):
                slot_range = range(s, s + effective_gap)
                model += (sum(sequence[slot_range] == t) >= 1)

    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            slot_range = range(s, s + per_slots[o])
            model += (sum(setup[slot_range, o]) <= at_most[o])

    return model, sequence

def main():
    with open("input_data.json", "r") as f:
        data = json.load(f)
    at_most = data["at_most"]
    per_slots = data["per_slots"]
    demand = data["demand"]
    requires = data["requires"]
    gap_limit = data["gap_limit"]

    model, sequence = build_model(at_most, per_slots, demand, requires, gap_limit)
    if model.solve():
        solution = {"sequence": [int(v) for v in sequence.value().tolist()]}
    else:
        solution = {}
    print(json.dumps(solution))

if __name__ == "__main__":
    main()