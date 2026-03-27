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
    n_items = data_dict["n_items"]
    bid_values = data_dict["bid_values"]
    bid_items = data_dict["bid_items"]
    bid_quantities = data_dict["bid_quantities"]
    item_capacities = data_dict["item_capacities"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_bids = len(bid_values)

    try:
        selected_bids = hypothesis_solution["selected_bids"]
        revenue = hypothesis_solution["revenue"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert isinstance(selected_bids, list), "selected_bids must be a list"
    assert isinstance(revenue, int), "revenue must be an int"
    assert revenue >= 0, "revenue must be non-negative"

    seen = set()
    for idx, b in enumerate(selected_bids):
        assert isinstance(b, int), f"selected_bids[{idx}] must be an int"
        assert 0 <= b < n_bids, f"selected_bids[{idx}]={b} out of range [0, {n_bids - 1}]"
        assert b not in seen, f"selected_bids contains duplicate bid index {b}"
        seen.add(b)

    # 1) Input consistency checks relevant to the CR
    assert len(bid_items) == n_bids, "bid_items must have the same length as bid_values"
    assert len(bid_quantities) == n_bids, "bid_quantities must have the same length as bid_values"
    assert len(item_capacities) == n_items, "item_capacities must have length n_items"
    for b in range(n_bids):
        assert len(bid_items[b]) == len(bid_quantities[b]), (
            f"bid_items[{b}] and bid_quantities[{b}] must have the same length"
        )

    # 2) CR1 quantity-capacity feasibility
    used_quantities = [0] * n_items
    for b in selected_bids:
        for item, qty in zip(bid_items[b], bid_quantities[b]):
            assert 1 <= item <= n_items, f"Bid {b} contains invalid item type {item}"
            assert isinstance(qty, int) and qty > 0, (
                f"Bid {b} has invalid quantity {qty}"
            )
            used_quantities[item - 1] += qty

    for item in range(1, n_items + 1):
        assert used_quantities[item - 1] <= item_capacities[item - 1], (
            f"Item type {item} uses {used_quantities[item - 1]} units, "
            f"but only {item_capacities[item - 1]} are available."
        )

    # 3) Objective consistency
    recomputed_revenue = sum(bid_values[b] for b in selected_bids)
    assert revenue == recomputed_revenue, (
        f"revenue={revenue}, recomputed={recomputed_revenue}."
    )

    # 4) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if revenue == ref_opt_val else "sat"

    return "pass", sol_opt
