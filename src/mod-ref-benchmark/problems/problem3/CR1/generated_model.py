import json
from cpmpy import *

data = json.load(open('input_data.json'))
n_tasks = data['n_tasks']
shifts = data['shifts']

n_shifts = len(shifts)
x = boolvar(shape=n_shifts, name='x')
model = Model()

for t in range(n_tasks):
    covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
    model += (sum(covering) == 2)

model.minimize(sum(x))

solution = model.solve()
if solution:
    x_vals = [int(v.value()) for v in x]
else:
    x_vals = None

print(json.dumps({'x': x_vals}))