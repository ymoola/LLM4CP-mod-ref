from cpmpy import *
import json


def build_model(capacities, orders, min_fill_percent):
    """
    Steel Mill Slab Design Problem - CR2

    CR2: Every used slab must be filled to at least a specified minimum
    percentage of its selected capacity.

    capacities: list of allowed slab sizes
    orders: list of {"size": int, "color": int}
    min_fill_percent: integer minimum fill percentage for every used slab
    """

    if not (0 <= min_fill_percent <= 100):
        raise ValueError("min_fill_percent must be between 0 and 100")

    n_orders = len(orders)
    n_slabs = n_orders

    sizes = [o["size"] for o in orders]
    colors = [o["color"] for o in orders]

    max_capacity = max(capacities)

    # Empty slabs incur no loss; positive loads use the smallest feasible slab.
    possible_losses = [0] + [
        min(c for c in capacities if c >= load) - load
        for load in range(1, max_capacity + 1)
    ]

    all_colors = sorted(set(colors))
    color_to_idx = {c: idx for idx, c in enumerate(all_colors)}
    n_colors = len(all_colors)

    # sb[i] = slab assigned to order i
    sb = intvar(0, n_slabs - 1, shape=n_orders, name="sb")

    # ld[j] = total load on slab j
    ld = intvar(0, max_capacity, shape=n_slabs, name="ld")

    # ls[j] = loss on slab j
    ls = intvar(0, max(possible_losses), shape=n_slabs, name="ls")

    # use_color[j,c] = 1 iff slab j contains at least one order of color c
    use_color = boolvar(shape=(n_slabs, n_colors), name="use_color")

    model = Model()

    # ------------------------------------------------
    # 1. Compute slab loads
    # ------------------------------------------------
    for j in range(n_slabs):
        model += ld[j] == sum(sizes[i] * (sb[i] == j) for i in range(n_orders))

    # ------------------------------------------------
    # 2. Compute slab losses from slab loads
    # ------------------------------------------------
    allowed_pairs = [(load, possible_losses[load]) for load in range(max_capacity + 1)]
    for j in range(n_slabs):
        model += Table([ld[j], ls[j]], allowed_pairs)

    # ------------------------------------------------
    # 3. Link slab usage to colors
    # ------------------------------------------------
    for j in range(n_slabs):
        for i in range(n_orders):
            cidx = color_to_idx[colors[i]]
            model += (sb[i] == j).implies(use_color[j, cidx])

    # ------------------------------------------------
    # 4. At most two colors per slab
    # ------------------------------------------------
    for j in range(n_slabs):
        model += sum(use_color[j, c] for c in range(n_colors)) <= 2

    # ------------------------------------------------
    # 5. CR2: every used slab must meet the minimum
    # fill percentage of its chosen capacity
    # ------------------------------------------------
    for j in range(n_slabs):
        model += (ld[j] > 0).implies(
            100 * ld[j] >= min_fill_percent * (ld[j] + ls[j])
        )

    # ------------------------------------------------
    # 6. Objective: minimize total loss
    # ------------------------------------------------
    model.minimize(sum(ls))

    return model, sb, ld, ls


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, sb, ld, ls = build_model(
        data["capacities"],
        data["orders"],
        data["min_fill_percent"]
    )

    if model.solve(time_limit=10):
        solution = {
            "order_to_slab": sb.value().tolist(),
            "slab_loads": ld.value().tolist(),
            "slab_losses": ls.value().tolist(),
            "total_loss": sum(ls.value().tolist())
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
