from cpmpy import *
import json, itertools

def build_model():
    # Load numeric parameters from input_data.json (if any)
    with open('input_data.json') as f:
        input_data = json.load(f)

    # Decision variables
    digits = intvar(1, 9, shape=9, name='digits')
    a, b, c, d, e, f, g, h, i = digits

    model = Model()

    # All digits distinct
    model += AllDifferent(digits)

    # Denominator numbers
    BC = 10 * b + c
    EF = 10 * e + f
    HI = 10 * h + i

    nums = [a, d, g]
    dens = [BC, EF, HI]

    # Add constraints for all permutations of the three fractions
    for perm in itertools.permutations(range(3), 3):
        num1, num2, num3 = [nums[p] for p in perm]
        den1, den2, den3 = [dens[p] for p in perm]
        model += (
            num1 * den2 * den3
            + num2 * den1 * den3
            + num3 * den1 * den2
            == den1 * den2 * den3
        )

    return model, digits

model, digits = build_model()
solver = Solver(name='gurobi')
solver.add(model)
solver.solve(logOutput=False)

solution = [int(digits[i].value()) for i in range(9)]
print(json.dumps({"digits": solution}))