from cpmpy import *
import json


def build_model(
    deck_width,
    deck_length,
    n_containers,
    width,
    length,
    classes,
    separation,
    restricted_regions
):
    n = n_containers

    # Bottom-left coordinates of containers
    x = intvar(0, deck_width, shape=n, name="x")
    y = intvar(0, deck_length, shape=n, name="y")

    model = Model()

    # Containers must stay inside deck
    for i in range(n):
        model += x[i] + width[i] <= deck_width
        model += y[i] + length[i] <= deck_length

    # Non-overlapping containers with class-based separation
    for i in range(n):
        for j in range(i + 1, n):
            c1 = classes[i] - 1
            c2 = classes[j] - 1
            sep = separation[c1][c2]

            model += (
                (x[i] + width[i] + sep <= x[j]) |
                (x[j] + width[j] + sep <= x[i]) |
                (y[i] + length[i] + sep <= y[j]) |
                (y[j] + length[j] + sep <= y[i])
            )

    # CR2: container rectangles must not overlap any restricted region
    # restricted region format: [rx, ry, rw, rl]
    for k, region in enumerate(restricted_regions):
        if not isinstance(region, list) or len(region) != 4:
            raise ValueError("Each restricted_regions entry must be [rx, ry, rw, rl]")

        rx, ry, rw, rl = region
        if not (isinstance(rx, int) and isinstance(ry, int) and isinstance(rw, int) and isinstance(rl, int)):
            raise ValueError("restricted_regions entries must be integer rectangles [rx, ry, rw, rl]")
        if rw <= 0 or rl <= 0:
            raise ValueError(f"Restricted region {k} must have positive size: {region}")
        if rx < 0 or ry < 0 or rx + rw > deck_width or ry + rl > deck_length:
            raise ValueError(f"Restricted region {k} must lie inside the deck: {region}")

        for i in range(n):
            model += (
                (x[i] + width[i] <= rx) |
                (rx + rw <= x[i]) |
                (y[i] + length[i] <= ry) |
                (ry + rl <= y[i])
            )

    return model, x, y


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, x, y = build_model(
        data["deck_width"],
        data["deck_length"],
        data["n_containers"],
        data["width"],
        data["length"],
        data["classes"],
        data["separation"],
        data["restricted_regions"]
    )

    if model.solve():
        solution = {
            "x": x.value().tolist(),
            "y": y.value().tolist()
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
