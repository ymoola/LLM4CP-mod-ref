from cpmpy import *
import json
import numpy as np


def build_model(n_tasks, shifts, shift_costs):
    """
    Build the CPMPy model for the Bus Driver Scheduling (Set Partitioning) problem.
    - n_tasks: integer number of tasks
    - shifts: list of lists, where shifts[i] is a list of task indices covered by shift i
    - shift_costs: list of integers, where shift_costs[i] is the cost of shift i
    """

    n_shifts = len(shifts)
    # Ensure provided shift_costs align with shifts
    assert len(shift_costs) == n_shifts, "shift_costs must have same length as shifts"

    # Decision variables
    x = boolvar(shape=n_shifts, name="x")   # x[i] = 1 iff shift i is selected

    model = Model()

    # 1. Cover each task exactly once
    for t in range(n_tasks):
        covering = [x[i] for i, shift in enumerate(shifts) if t in shift]
        model += (sum(covering) == 1)

    # 2. Minimize total cost of selected shifts
    model.minimize(sum(shift_costs[i] * x[i] for i in range(n_shifts)))

    return model, x


with open('input_data.json', 'r') as f:
    data = json.load(f)

n_tasks = data['n_tasks']
shifts = data['shifts']
shift_costs = data['shift_costs']

model, x = build_model(n_tasks, shifts, shift_costs)

if not model.solve():
    raise ValueError("No solution found")

x_sol = [int(val) for val in x.value()]
total_cost = int(sum(shift_costs[i] * x_sol[i] for i in range(len(shifts))))

print(json.dumps({"x": x_sol, "total_cost": total_cost}))