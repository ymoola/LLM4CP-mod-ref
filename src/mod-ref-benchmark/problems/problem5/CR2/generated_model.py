import json
from cpmpy import *

def build_model():
    digits = intvar(1, 9, shape=9, name="digits")
    a, b, c, d, e, f, g, h, i = digits
    model = Model()
    model += AllDifferent(digits)
    BC = 10 * b + c
    EF = 10 * e + f
    HI = 10 * h + i
    model += a * EF * HI + d * BC * HI + g * BC * EF == BC * EF * HI
    model += BC < EF
    model += EF < HI
    return model, digits

def main():
    with open('input_data.json') as f:
        _ = json.load(f)
    model, digits = build_model()
    if model.solve():
        solution = [int(digits[k].value()) for k in range(9)]
        out = {"digits": solution}
    else:
        out = {"digits": []}
    print(json.dumps(out))

if __name__ == "__main__":
    main()
