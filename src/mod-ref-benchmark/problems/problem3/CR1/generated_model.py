from cpmpy import *
import json
import numpy as np


def build_model(n_tasks, shifts):
    """
    Build the CPMPy model for the Bus Driver Scheduling (Set Partitioning) problem.
    - n_tasks: integer number of tasks
    - shifts: list of lists, where shifts[i] is a list of task indices covered by shift i
    """

    n_shifts = len(shifts)

    # Decision variables
    x = boolvar(shape=n_shifts, name="x")   # x[i] = 1 iff shift i is selected

    model = Model()

    # 1. Cover each task exactly twice
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 2)

    # 2. Minimize number of selected shifts
    model.minimize(sum(x))

    return model, x

with open("input_data.json", "r") as f:
    data = json.load(f)

n_tasks = data["n_tasks"]
shifts = data["shifts"]

model, x = build_model(n_tasks, shifts)
if not model.solve():
    raise ValueError("No solution found")

solution = {
    "x": [int(v) for v in x.value()]
}

print(json.dumps(solution))