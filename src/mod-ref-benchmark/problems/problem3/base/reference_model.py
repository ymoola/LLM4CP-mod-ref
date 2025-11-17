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

    # 1. Cover each task exactly once
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 1)

    # 2. Minimize number of selected shifts
    model.minimize(sum(x))

    return model, x


if __name__ == "__main__":
    # Load external input data
    with open("input_data.json") as f:
        data = json.load(f)

    n_tasks = data["n_tasks"]
    shifts = data["shifts"]

    model, x = build_model(n_tasks, shifts)
    model.solve()

    selected = [int(v) for v in x.value()]
    num_selected = sum(selected)

    print(json.dumps({
        "selected_shifts": selected,
        "num_selected": int(num_selected)
    }))