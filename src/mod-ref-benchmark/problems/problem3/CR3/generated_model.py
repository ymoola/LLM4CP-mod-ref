from cpmpy import *
import json
import numpy as np


def build_model(n_tasks, shifts, shift_durations, H):
    """
    Build the CPMPy model for the Bus Driver Scheduling (Set Partitioning) problem.
    - n_tasks: integer number of tasks
    - shifts: list of lists, where shifts[i] is a list of task indices covered by shift i
    - shift_durations: list of integers where shift_durations[i] is the duration of shift i
    - H: integer maximum total duration allowed across all selected shifts
    """

    n_shifts = len(shifts)
    assert len(shift_durations) == n_shifts

    # Decision variables
    x = boolvar(shape=n_shifts, name="x")   # x[i] = 1 iff shift i is selected

    model = Model()

    # 1. Cover each task exactly once
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 1)

    # 3. Total duration of selected shifts must not exceed H
    model += (sum(x[i] * shift_durations[i] for i in range(n_shifts)) <= H)

    # 2. Minimize number of selected shifts
    model.minimize(sum(x))

    return model, x

if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)
    n_tasks = data["n_tasks"]
    shifts = data["shifts"]
    shift_durations = data["shift_durations"]
    H = data["H"]

    model, x = build_model(n_tasks, shifts, shift_durations, H)
    if model.solve():
        x_sol = [int(val) for val in x.value()]
    else:
        x_sol = []
    print(json.dumps({"x": x_sol}))
