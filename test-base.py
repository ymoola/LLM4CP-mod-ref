import json
from cpmpy import Model, intvar

with open("input_data.json", "r") as f:
    data = json.load(f)

lower = int(data["lower_bound"])
upper = int(data["upper_bound"])

x = intvar(lower, upper, name="x")
model = Model(x >= lower, x <= upper)

if not model.solve():
    raise RuntimeError("No solution found")

print(json.dumps({"x": int(x.value())}))
