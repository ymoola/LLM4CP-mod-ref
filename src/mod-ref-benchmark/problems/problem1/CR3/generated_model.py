from cpmpy import *
import json

def build_model(at_most, per_slots, demand, requires):
    requires = cpm_array(requires)
    n_cars = sum(demand)
    n_options = len(at_most)
    n_types = len(demand)

    sequence = intvar(0, n_types - 1, shape=n_cars, name="sequence")
    setup = boolvar(shape=(n_cars, n_options), name="setup")
    violations = intvar(0, n_cars, shape=(n_options, n_cars), name="violations")
    total_violations = intvar(0, n_cars * n_options, name="total_violations")

    model = Model()

    model += [sum(sequence == t) == demand[t] for t in range(n_types)]

    for s in range(n_cars):
        for o in range(n_options):
            model += (setup[s, o] == requires[sequence[s], o])

    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            slot_range = range(s, s + per_slots[o])
            model += (sum(setup[slot_range, o]) <= at_most[o] + violations[o, s])

    model += (total_violations == sum(violations[o, s] for o in range(n_options) for s in range(n_cars - per_slots[o])))
    model.minimize(total_violations)

    return model, sequence, total_violations

if __name__ == "__main__":
    with open("input_data.json", "r") as f:
        data = json.load(f)
    at_most = data["at_most"]
    per_slots = data["per_slots"]
    demand = data["demand"]
    requires = data["requires"]

    model, sequence, total_violations = build_model(at_most, per_slots, demand, requires)
    if model.solve():
        seq_val = [int(v) for v in sequence.value().tolist()]
        total_val = int(total_violations.value())
    else:
        seq_val = []
        total_val = None
    print(json.dumps({"sequence": seq_val, "total_violations": total_val}))