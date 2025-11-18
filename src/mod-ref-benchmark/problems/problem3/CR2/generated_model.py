from cpmpy import *
import json

def build_model(n_tasks, shifts, shift_costs):
    n_shifts = len(shifts)
    x = boolvar(shape=n_shifts, name="x")
    model = Model()
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 1)
    model.minimize(sum(x[i] * shift_costs[i] for i in range(n_shifts)))
    return model, x

def main():
    with open('input_data.json') as f:
        data = json.load(f)
    n_tasks = data["n_tasks"]
    shifts = data["shifts"]
    shift_costs = data["shift_costs"]
    model, x = build_model(n_tasks, shifts, shift_costs)
    if model.solve():
        solution = [int(v) for v in x.value()]
        total_cost = sum(shift_costs[i] * solution[i] for i in range(len(solution)))
        print(json.dumps({"x": solution, "total_cost": int(total_cost)}))
    else:
        print(json.dumps({"x": None, "total_cost": None}))

if __name__ == "__main__":
    main()
