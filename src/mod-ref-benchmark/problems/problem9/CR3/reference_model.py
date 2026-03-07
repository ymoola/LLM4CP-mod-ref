from cpmpy import *
import json


def build_model(deck_width, deck_length, n_containers, width, length, classes, separation, priority):
    n = n_containers

    if len(width) != n or len(length) != n or len(classes) != n or len(priority) != n:
        raise ValueError("width, length, classes, and priority must all have length n_containers")

    # Bottom-left coordinates of containers
    x = intvar(0, deck_width, shape=n, name="x")
    y = intvar(0, deck_length, shape=n, name="y")

    # CR3: load[i] = 1 if container i is loaded
    load = boolvar(shape=n, name="load")

    total_value = intvar(0, sum(priority), name="total_value")

    model = Model()

    # Loaded containers must stay inside deck
    for i in range(n):
        model += load[i].implies(x[i] + width[i] <= deck_width)
        model += load[i].implies(y[i] + length[i] <= deck_length)

    # Non-overlap/separation only required between loaded containers
    for i in range(n):
        for j in range(i + 1, n):
            c1 = classes[i] - 1
            c2 = classes[j] - 1
            sep = separation[c1][c2]

            non_overlap = (
                (x[i] + width[i] + sep <= x[j]) |
                (x[j] + width[j] + sep <= x[i]) |
                (y[i] + length[i] + sep <= y[j]) |
                (y[j] + length[j] + sep <= y[i])
            )

            model += (load[i] & load[j]).implies(non_overlap)

    model += total_value == sum(load[i] * priority[i] for i in range(n))
    model.maximize(total_value)

    return model, x, y, load, total_value


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, y, load, total_value = build_model(
        data["deck_width"],
        data["deck_length"],
        data["n_containers"],
        data["width"],
        data["length"],
        data["classes"],
        data["separation"],
        data["priority"]
    )

    if model.solve():
        solution = {
            "x": x.value().tolist(),
            "y": y.value().tolist(),
            "load": [int(v) for v in load.value().tolist()],
            "total_value": int(total_value.value())
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
