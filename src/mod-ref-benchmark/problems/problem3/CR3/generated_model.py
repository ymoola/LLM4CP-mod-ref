import json
from cpmpy import *

def build_model(n_tasks, shifts, shift_durations, H):
    n_shifts = len(shifts)
    x = boolvar(shape=n_shifts, name="x")
    model = Model()
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 1)
    model += (sum(x[i] * shift_durations[i] for i in range(n_shifts)) <= H)
    model.minimize(sum(x))
    return model, x

with open('input_data.json') as f:
    data = json.load(f)

n_tasks = data['n_tasks']
shifts = data['shifts']
shift_durations = data['shift_durations']
H = data['H']

model, x = build_model(n_tasks, shifts, shift_durations, H)

if model.solve():
    result = {"x": [int(v) for v in x.value()]}
    print(json.dumps(result))
else:
    print(json.dumps({"x": None}))