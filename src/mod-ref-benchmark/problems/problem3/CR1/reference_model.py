from cpmpy import *
import json

# Load data
with open("input_data.json") as f:
    data = json.load(f)

nTasks = data["n_tasks"]
shifts = data["shifts"]
nShifts = len(shifts)

def build_model(nTasks, shifts):
    nShifts = len(shifts)

    # Decision variable: x[i] = 1 if shift i is selected
    x = boolvar(shape=nShifts, name="x")

    model = Model()

    # CR1: Each task must be covered exactly twice
    for t in range(nTasks):
        covering_shifts = [x[i] for i, s in enumerate(shifts) if t in s]
        model += (sum(covering_shifts) == 2)

    # Objective: minimize number of selected shifts
    model.minimize(sum(x))

    return model, x

model, x = build_model(nTasks, shifts)
model.solve()

selected = [int(v) for v in x.value()]
num_selected = sum(selected)

print(json.dumps({
    "x": selected,
    "num_selected": int(num_selected)
}))