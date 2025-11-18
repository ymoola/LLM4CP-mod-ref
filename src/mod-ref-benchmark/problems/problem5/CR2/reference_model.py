from cpmpy import *
import json

def build_model():
    # 9 distinct digits 1..9
    digits = intvar(1, 9, shape=9, name="digits")
    a, b, c, d, e, f, g, h, i = digits

    model = Model()

    # Distinctness
    model += AllDifferent(digits)

    # Denominators
    BC = 10 * b + c
    EF = 10 * e + f
    HI = 10 * h + i

    # CR2: denominator ordering constraint
    model += (BC < EF)
    model += (EF < HI)

    # Original arithmetic constraint:
    # a/(BC) + d/(EF) + g/(HI) == 1
    model += (
        a * EF * HI +
        d * BC * HI +
        g * BC * EF  == BC * EF * HI
    )

    return model, digits


if __name__ == "__main__":
    # Load dummy
    with open("input_data.json") as f:
        _ = json.load(f)

    model, digits = build_model()

    if model.solve():
        print(json.dumps({
            "digits": digits.value().tolist()
        }))
    else:
        print(json.dumps({"digits": [None]*9}))