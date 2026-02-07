from cpmpy import *
import json

def build_model():
    digits = intvar(1, 9, shape=9, name="digits")
    a, b, c, d, e, f, g, h, i = digits

    model = Model()

    model += AllDifferent(digits)

    BC = 10*b + c
    EF = 10*e + f
    HI = 10*h + i

    model += BC < EF
    model += EF < HI

    model += a * EF * HI + d * BC * HI + g * BC * EF == BC * EF * HI

    return model, digits

input_data = {}
with open("input_data.json", "r") as f:
    input_data = json.load(f)

model, digits = build_model()

if "digits" in input_data and input_data["digits"]:
    model += digits == input_data["digits"]

solution_found = model.solve()

output = {}
if solution_found:
    output["digits"] = [int(v) for v in digits.value().tolist()]
else:
    output["digits"] = None

print(json.dumps(output))