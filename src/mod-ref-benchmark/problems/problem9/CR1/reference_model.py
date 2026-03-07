from cpmpy import *
import json


def build_model(deck_width, deck_length, n_containers, width, length, classes, separation):
    n = n_containers

    # Bottom-left coordinates of containers
    x = intvar(0, deck_width, shape=n, name="x")
    y = intvar(0, deck_length, shape=n, name="y")

    # CR1: rotation decision (0=no rotation, 1=rotated 90 degrees)
    rot = boolvar(shape=n, name="rot")

    min_dim = min(min(width), min(length))
    max_dim = max(max(width), max(length))
    eff_w = intvar(min_dim, max_dim, shape=n, name="eff_w")
    eff_l = intvar(min_dim, max_dim, shape=n, name="eff_l")

    model = Model()

    # Effective dimensions under rotation
    for i in range(n):
        model += eff_w[i] == rot[i] * length[i] + (1 - rot[i]) * width[i]
        model += eff_l[i] == rot[i] * width[i] + (1 - rot[i]) * length[i]

    # Containers must stay inside deck
    for i in range(n):
        model += x[i] + eff_w[i] <= deck_width
        model += y[i] + eff_l[i] <= deck_length

    # Non-overlapping containers with class-based separation
    for i in range(n):
        for j in range(i + 1, n):
            c1 = classes[i] - 1
            c2 = classes[j] - 1
            sep = separation[c1][c2]

            model += (
                (x[i] + eff_w[i] + sep <= x[j]) |
                (x[j] + eff_w[j] + sep <= x[i]) |
                (y[i] + eff_l[i] + sep <= y[j]) |
                (y[j] + eff_l[j] + sep <= y[i])
            )

    return model, x, y, rot


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, y, rot = build_model(
        data["deck_width"],
        data["deck_length"],
        data["n_containers"],
        data["width"],
        data["length"],
        data["classes"],
        data["separation"]
    )

    if model.solve():
        solution = {
            "x": x.value().tolist(),
            "y": y.value().tolist(),
            "rot": [int(v) for v in rot.value().tolist()]
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
