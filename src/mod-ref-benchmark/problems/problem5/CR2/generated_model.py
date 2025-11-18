import json
from cpmpy import *

def build_model():
    digits = intvar(1, 9, shape=9, name="digits")
    a, b, c, d, e, f, g, h, i = digits

    model = Model()
    model += AllDifferent(digits)

    BC = 10*b + c
    EF = 10*e + f
    HI = 10*h + i

    model += a * EF * HI + d * BC * HI + g * BC * EF == BC * EF * HI
    model += BC < EF
    model += EF < HI

    return model, digits

if __name__ == "__main__":
    # Load any input parameters (none used in this model)
    try:
        with open("input_data.json", "r") as f:
            input_data = json.load(f)
    except Exception:
        input_data = {}

    model, digits = build_model()
    if model.solve():
        solution = [int(val) for val in digits.value()]
        print(json.dumps({"digits": solution}))
    else:
        print(json.dumps({"digits": []}))