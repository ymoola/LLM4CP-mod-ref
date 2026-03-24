from cpmpy import *
import json


def build_model(capacities, orders, forbidden_pairs):
    """
    Steel Mill Slab Design Problem - CR1

    CR1: Certain colour pairs are forbidden from appearing on the same slab.
    For each forbidden pair (color_a, color_b), no slab may contain orders
    of both colors simultaneously.

    capacities: list of allowed slab sizes
    orders: list of {"size": int, "color": int}
    forbidden_pairs: list of [color_a, color_b] pairs
    """

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
    # 5. Objective: minimize total loss
    # ------------------------------------------------
    model.minimize(sum(ls))

    # ------------------------------------------------
    # 6. CR1: Forbidden colour pairs — no slab may
    # contain orders from both colours in any pair
    # ------------------------------------------------
    for color_a, color_b in forbidden_pairs:
        # Only apply if both colors appear in the orders
        if color_a not in color_to_idx or color_b not in color_to_idx:
            continue
        cidx_a = color_to_idx[color_a]
        cidx_b = color_to_idx[color_b]
        for j in range(n_slabs):
            model += ~(use_color[j, cidx_a] & use_color[j, cidx_b])

    return model, sb, ld, ls


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, sb, ld, ls = build_model(
        data["capacities"],
        data["orders"],
        data["forbidden_pairs"]
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
