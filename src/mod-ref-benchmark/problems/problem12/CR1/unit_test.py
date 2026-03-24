import traceback


def handle_assertions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            return ("fail", str(e))
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrapper


@handle_assertions
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verify Steel Mill Slab Design CR1:
    - Base constraints: load computation, loss computation, color linkage,
      at-most-two-colors per slab
    - CR1 constraint: no slab contains both colors of any forbidden pair
    """
    capacities = data_dict["capacities"]
    orders = data_dict["orders"]
    forbidden_pairs = data_dict["forbidden_pairs"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_orders = len(orders)
    n_slabs = n_orders
    sizes = [o["size"] for o in orders]
    colors = [o["color"] for o in orders]
    max_capacity = max(capacities)

    # Precompute possible_losses table
    possible_losses = [
        min(c for c in capacities if c >= load) - load
        for load in range(max_capacity + 1)
    ]

    all_colors = sorted(set(colors))
    n_colors = len(all_colors)

    # 1) Extract solution
    try:
        order_to_slab = hypothesis_solution["order_to_slab"]
        slab_loads = hypothesis_solution["slab_loads"]
        slab_losses = hypothesis_solution["slab_losses"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 2) Type and shape checks
    assert isinstance(order_to_slab, list), "order_to_slab must be a list"
    assert len(order_to_slab) == n_orders, (
        f"order_to_slab must have length {n_orders}, got {len(order_to_slab)}"
    )
    for i, v in enumerate(order_to_slab):
        assert isinstance(v, int), f"order_to_slab[{i}] must be an int"
        assert 0 <= v < n_slabs, (
            f"order_to_slab[{i}]={v} out of range [0, {n_slabs - 1}]"
        )

    assert isinstance(slab_loads, list), "slab_loads must be a list"
    assert len(slab_loads) == n_slabs, (
        f"slab_loads must have length {n_slabs}, got {len(slab_loads)}"
    )
    for j, v in enumerate(slab_loads):
        assert isinstance(v, int), f"slab_loads[{j}] must be an int"
        assert 0 <= v <= max_capacity, (
            f"slab_loads[{j}]={v} out of range [0, {max_capacity}]"
        )

    assert isinstance(slab_losses, list), "slab_losses must be a list"
    assert len(slab_losses) == n_slabs, (
        f"slab_losses must have length {n_slabs}, got {len(slab_losses)}"
    )
    for j, v in enumerate(slab_losses):
        assert isinstance(v, int), f"slab_losses[{j}] must be an int"
        assert v >= 0, f"slab_losses[{j}]={v} must be non-negative"

    # 3) Constraint 1: verify slab loads match order assignments
    for j in range(n_slabs):
        recomputed_load = sum(
            sizes[i] for i in range(n_orders) if order_to_slab[i] == j
        )
        assert recomputed_load == slab_loads[j], (
            f"Load mismatch on slab {j}: reported {slab_loads[j]}, "
            f"recomputed {recomputed_load}"
        )

    # 4) Constraint 2: verify slab losses match loads via possible_losses table
    for j in range(n_slabs):
        load = slab_loads[j]
        if load == 0:
            expected_loss = 0
        else:
            feasible = [c for c in capacities if c >= load]
            assert len(feasible) > 0, (
                f"Slab {j} load {load} exceeds all capacities"
            )
            expected_loss = min(feasible) - load
        assert slab_losses[j] == expected_loss, (
            f"Loss mismatch on slab {j}: load={load}, reported loss={slab_losses[j]}, "
            f"expected loss={expected_loss}"
        )

    # 5) Constraint 3 & 4: at most two distinct colors per slab
    for j in range(n_slabs):
        colors_on_slab = set(
            colors[i] for i in range(n_orders) if order_to_slab[i] == j
        )
        assert len(colors_on_slab) <= 2, (
            f"Slab {j} has {len(colors_on_slab)} distinct colors "
            f"{colors_on_slab}, exceeds limit of 2"
        )

    # 6) CR1: no slab may contain both colors of any forbidden pair
    for color_a, color_b in forbidden_pairs:
        for j in range(n_slabs):
            colors_on_slab = set(
                colors[i] for i in range(n_orders) if order_to_slab[i] == j
            )
            assert not (color_a in colors_on_slab and color_b in colors_on_slab), (
                f"CR1 violated on slab {j}: forbidden pair ({color_a}, {color_b}) "
                f"both present in {colors_on_slab}"
            )

    # 7) Objective consistency: recompute total loss
    recomputed_total_loss = sum(slab_losses)

    # 8) Optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if recomputed_total_loss == ref_opt_val else "sat"

    return "pass", sol_opt