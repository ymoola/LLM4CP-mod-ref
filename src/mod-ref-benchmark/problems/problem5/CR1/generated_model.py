from cpmpy import *
import json

def build_model():
    """
    Base CPMPy model for the N-Fractions puzzle.
    No external parameters; this is a fixed-structure CSP.
    """

    # Decision variables
    digits = intvar(1, 9, shape=9, name="digits")
    a, b, c, d, e, f, g, h, i = digits

    model = Model()

    # All digits must be distinct
    model += AllDifferent(digits)

    # Fraction equation:
    # a/(BC) + d/(EF) + g/(HI) = 1
    #
    # Multiply both sides by BC * EF * HI:
    # a*EF*HI + d*BC*HI + g*BC*EF = BC*EF*HI
    BC = 10*b + c
    EF = 10*e + f
    HI = 10*h + i

    model += a * EF * HI + d * BC * HI + g * BC * EF == BC * EF * HI
    model += a * HI * EF + g * BC * EF + d * BC * HI == BC * EF * HI
    model += d * BC * HI + a * EF * HI + g * BC * EF == BC * EF * HI
    model += d * HI * BC + g * BC * EF + a * EF * HI == BC * EF * HI
    model += g * BC * EF + a * EF * HI + d * BC * HI == BC * EF * HI
    model += g * EF * BC + d * BC * HI + a * EF * HI == BC * EF * HI

    return model, digits

if __name__ == "__main__":
    with open('input_data.json') as f:
        input_data = json.load(f)
    model, digits = build_model()
    if model.solve():
        res_digits = [int(v) for v in digits.value().tolist()]
    else:
        res_digits = []
    print(json.dumps({"digits": res_digits}))