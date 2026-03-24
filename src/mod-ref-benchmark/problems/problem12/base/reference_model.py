from cpmpy import *
import json


def build_model(capacities, orders):
    """
    Steel Mill Slab Design Problem, Type 1

    capacities: list of allowed slab sizes
    orders: list of {"size": int, "color": int}
    """

    n_orders = len(orders)
    n_slabs = n_orders

    sizes = [o["size"] for o in orders]
    colors = [o["color"] for o in orders]

    max_capacity = max(capacities)

    # for each possible load, compute smallest feasible loss
    possible_losses = [
        min(c for c in capacities if c >= load) - load
        for load in range(max_capacity + 1)
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
    # 5. Objective: minimize total loss
    # ------------------------------------------------
    model.minimize(sum(ls))

    return model, sb, ld, ls


