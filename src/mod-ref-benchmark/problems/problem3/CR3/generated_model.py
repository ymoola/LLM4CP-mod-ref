import json
from cpmpy import *

data = json.load(open('input_data.json'))
n_tasks = data['n_tasks']
shifts = data['shifts']
shift_durations = data['shift_durations']
H = data['H']

n_shifts = len(shifts)
x = boolvar(shape=n_shifts, name='x')
model = Model()

for t in range(n_tasks):
    covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
    model += (sum(covering) == 1)

model += (sum(x[i] * shift_durations[i] for i in range(n_shifts)) <= H)
model.minimize(sum(x))

model.solve(log_output=False)

result = {"x": [int(v) for v in x.solution()]}
print(json.dumps(result))
