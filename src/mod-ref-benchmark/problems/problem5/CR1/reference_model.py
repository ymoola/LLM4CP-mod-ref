from cpmpy import *
import json
import itertools

def build_model():
    # 9 digits: a,b,c,d,e,f,g,h,i
    digits = intvar(1, 9, shape=9, name="digits")
    a,b,c,d,e,f,g,h,i = digits

    model = Model()

    # All digits must be distinct
    model += AllDifferent(digits)

    # Define the three fraction components:
    num = [a, d, g]
    den = [
        10*b + c,
        10*e + f,
        10*h + i
    ]

    # For all 6 permutations of the three fractions: sum must equal 1
    for perm in itertools.permutations([0,1,2]):
        lhs = num[perm[0]] * den[perm[1]] * den[perm[2]] + \
              num[perm[1]] * den[perm[0]] * den[perm[2]] + \
              num[perm[2]] * den[perm[0]] * den[perm[1]]
        rhs = den[0] * den[1] * den[2]
        model += (lhs == rhs)

    return model, digits


if __name__ == "__main__":
    model, digits = build_model()

    if not model.solve():
        print(json.dumps({"unsat": True}))
    else:
        print(json.dumps({"digits": digits.value().tolist()}))