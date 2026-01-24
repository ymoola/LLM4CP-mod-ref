from cpmpy import *
import json
import itertools

# Load parameters from input_data.json (if any)
with open('input_data.json', 'r') as f:
    input_data = json.load(f)

# Decision variables
digits = intvar(1, 9, shape=9, name="digits")
a, b, c, d, e, f, g, h, i = digits

model = Model()

# All digits must be distinct
model += AllDifferent(digits)

# Define two-digit numbers
BC = 10 * b + c
EF = 10 * e + f
HI = 10 * h + i

# Groups of (numerator, denominator)
groups = [(a, BC), (d, EF), (g, HI)]

# Add permutation constraints
for perm in itertools.permutations(groups, 3):
    n1, d1 = perm[0]
    n2, d2 = perm[1]
    n3, d3 = perm[2]
    model += n1 * d2 * d3 + n2 * d1 * d3 + n3 * d1 * d2 == d1 * d2 * d3

# Solve the model
if model.solve():
    solution = [int(digits[j].value()) for j in range(9)]
    print(json.dumps({"digits": solution}))
else:
    print(json.dumps({"digits": None}))