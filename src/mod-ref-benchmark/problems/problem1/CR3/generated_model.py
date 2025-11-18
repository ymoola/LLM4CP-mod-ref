import json
from cpmpy import *
def build_model(at_most, per_slots, demand, requires):
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
    violations = []
    for o in range(n_options):
        windows = n_cars - per_slots[o]
        viol = boolvar(shape=windows, name=f"violation_o{o}")
        violations.append(viol)
        for s in range(windows):
            slot_slice = slice(s, s + per_slots[o])
            model += (viol[s] == (sum(setup[slot_slice, o]) > at_most[o]))
    total_violations = intvar(0, n_cars * n_options, name="total_violations")
    model += (total_violations == sum([sum(v) for v in violations]))
    model.minimize(total_violations)
    return model, sequence, total_violations

def main():
    with open('input_data.json') as f:
        data = json.load(f)
    at_most = data['at_most']
    per_slots = data['per_slots']
    demand = data['demand']
    requires = data['requires']
    model, sequence, total_violations = build_model(at_most, per_slots, demand, requires)
    if model.solve():
        seq_vals = [int(sequence[i]) for i in range(len(sequence))]
        total_val = int(total_violations.value())
        solution = {"sequence": seq_vals, "total_violations": total_val}
        print(json.dumps(solution))
    else:
        print(json.dumps({"sequence": None, "total_violations": None}))

if __name__ == "__main__":
    main()
