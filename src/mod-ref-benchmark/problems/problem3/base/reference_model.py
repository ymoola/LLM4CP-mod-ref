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

