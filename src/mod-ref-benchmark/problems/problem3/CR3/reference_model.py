from cpmpy import *
import json

# Load data
with open("input_data.json") as f:
    data = json.load(f)

n_tasks = data["n_tasks"]
shifts = data["shifts"]
shift_durations = data["shift_durations"]
H = data["H"]

n_shifts = len(shifts)

# Decision variables
x = boolvar(shape=n_shifts, name="x")

model = Model()

# 1. Cover each task exactly once
for t in range(n_tasks):
    covering = [i for i in range(n_shifts) if t in shifts[i]]
    assert len(covering) > 0, f"Task {t} has no covering shift"
    model += sum(x[i] for i in covering) == 1

# 2. Duration constraint
model += sum(x[i] * shift_durations[i] for i in range(n_shifts)) <= H

# 3. Objective: minimize the number of selected shifts
model.minimize(sum(x))

# Solve
if not model.solve():
    print("UNSAT INSTANCE — no valid schedule under duration limit H")
    exit()

selected = [int(v) for v in x.value()]
num_selected = sum(selected)

print(json.dumps({
    "x": selected,
    "num_selected": int(num_selected)
}))