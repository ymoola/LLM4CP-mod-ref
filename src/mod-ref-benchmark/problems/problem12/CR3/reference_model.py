from cpmpy import *
import json


def build_model(capacities, orders):
    """
    Steel Mill Slab Design Problem - CR3

    CR3: Splitting orders of the same colour across multiple slabs incurs
    a unit penalty for each additional slab used by that colour. The
    objective minimizes total waste plus total split penalty.

    capacities: list of allowed slab sizes
    orders: list of {"size": int, "color": int}
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

    # CR3 helper variables
    color_slab_count = intvar(1, n_slabs, shape=n_colors, name="color_slab_count")
    split_penalty = intvar(0, n_slabs - 1, shape=n_colors, name="split_penalty")
    total_split_penalty = intvar(0, n_colors * (n_slabs - 1), name="total_split_penalty")
    total_loss = intvar(0, n_slabs * max(possible_losses), name="total_loss")
    total_objective = intvar(
        0,
        n_slabs * max(possible_losses) + n_colors * (n_slabs - 1),
        name="total_objective"
    )

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
    # 5. CR3: strengthen color linkage so use_color is
    # exact before it is used in the objective
    # ------------------------------------------------
    for j in range(n_slabs):
        for color in all_colors:
            cidx = color_to_idx[color]
            matching_orders = [i for i in range(n_orders) if colors[i] == color]
            model += use_color[j, cidx] <= sum(sb[i] == j for i in matching_orders)

    # ------------------------------------------------
    # 6. CR3: count how many slabs each color uses and
    # penalize every extra slab beyond the first
    # ------------------------------------------------
    for cidx in range(n_colors):
        model += color_slab_count[cidx] == sum(use_color[j, cidx] for j in range(n_slabs))
        model += split_penalty[cidx] == color_slab_count[cidx] - 1

    # ------------------------------------------------
    # 7. CR3: aggregate waste, split penalty, and the
    # combined objective
    # ------------------------------------------------
    model += total_loss == sum(ls)
    model += total_split_penalty == sum(split_penalty)
    model += total_objective == total_loss + total_split_penalty

    # ------------------------------------------------
    # 8. Objective: minimize total waste plus split
    # penalty
    # ------------------------------------------------
    model.minimize(total_objective)

    return model, sb, ld, ls, total_split_penalty, total_loss, total_objective


if __name__ == "__main__":
    with open("input_data.json") as f:
        data = json.load(f)

    model, sb, ld, ls, total_split_penalty, total_loss, total_objective = build_model(
        data["capacities"],
        data["orders"]
    )

    if model.solve(time_limit=10):
        solution = {
            "order_to_slab": sb.value().tolist(),
            "slab_loads": ld.value().tolist(),
            "slab_losses": ls.value().tolist(),
            "total_split_penalty": int(total_split_penalty.value()),
            "total_loss": int(total_loss.value()),
            "total_objective": int(total_objective.value())
        }
        print(json.dumps(solution))
    else:
        print("No solution found")
