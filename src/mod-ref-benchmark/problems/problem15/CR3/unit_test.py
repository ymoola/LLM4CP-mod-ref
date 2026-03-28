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
def cr3_verify_func(data_dict, hypothesis_solution):
    n_items = data_dict["n_items"]
    bid_values = data_dict["bid_values"]
    bid_items = data_dict["bid_items"]
    reserve_values = data_dict["reserve_values"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_bids = len(bid_values)

    try:
        selected_bids = hypothesis_solution["selected_bids"]
        reserved_items = hypothesis_solution["reserved_items"]
        revenue = hypothesis_solution["revenue"]
        reserved_value = hypothesis_solution["reserved_value"]
        total_value = hypothesis_solution["total_value"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert isinstance(selected_bids, list), "selected_bids must be a list"
    assert isinstance(reserved_items, list), "reserved_items must be a list"
    assert isinstance(revenue, int), "revenue must be an int"
    assert isinstance(reserved_value, int), "reserved_value must be an int"
    assert isinstance(total_value, int), "total_value must be an int"
    assert revenue >= 0, "revenue must be non-negative"
    assert reserved_value >= 0, "reserved_value must be non-negative"
    assert total_value >= 0, "total_value must be non-negative"

    selected_set = set()
    for idx, b in enumerate(selected_bids):
        assert isinstance(b, int), f"selected_bids[{idx}] must be an int"
        assert 0 <= b < n_bids, f"selected_bids[{idx}]={b} out of range [0, {n_bids - 1}]"
        assert b not in selected_set, f"selected_bids contains duplicate bid index {b}"
        selected_set.add(b)

    reserved_set = set()
    for idx, item in enumerate(reserved_items):
        assert isinstance(item, int), f"reserved_items[{idx}] must be an int"
        assert 1 <= item <= n_items, (
            f"reserved_items[{idx}]={item} out of range [1, {n_items}]"
        )
        assert item not in reserved_set, f"reserved_items contains duplicate item id {item}"
        reserved_set.add(item)

    # 1) Input consistency checks relevant to the CR
    assert len(bid_items) == n_bids, "bid_items must have the same length as bid_values"
    assert len(reserve_values) == n_items, "reserve_values must have length n_items"

    for b in range(n_bids):
        assert len(set(bid_items[b])) == len(bid_items[b]), (
            f"bid_items[{b}] may not contain duplicate items"
        )
        for item in bid_items[b]:
            assert 1 <= item <= n_items, f"bid_items[{b}] contains invalid item {item}"

    # 2) Base compatibility check: accepted bids must be mutually disjoint
    sold_items = set()
    for b in selected_bids:
        for item in bid_items[b]:
            assert item not in sold_items, (
                f"Item {item} appears in more than one accepted bid."
            )
            sold_items.add(item)

    # 3) CR3 reservation check: an item may be sold at most once or reserved, but not both
    for item in range(1, n_items + 1):
        assigned_count = (1 if item in sold_items else 0) + (1 if item in reserved_set else 0)
        assert assigned_count <= 1, (
            f"Item {item} cannot be both sold and reserved."
        )

    # 4) Objective consistency
    recomputed_revenue = sum(bid_values[b] for b in selected_bids)
    recomputed_reserved_value = sum(reserve_values[item - 1] for item in reserved_items)
    recomputed_total_value = recomputed_revenue + recomputed_reserved_value

    assert revenue == recomputed_revenue, (
        f"revenue={revenue}, recomputed={recomputed_revenue}."
    )
    assert reserved_value == recomputed_reserved_value, (
        f"reserved_value={reserved_value}, recomputed={recomputed_reserved_value}."
    )
    assert total_value == recomputed_total_value, (
        f"total_value={total_value}, recomputed={recomputed_total_value}."
    )

    # 5) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if total_value == ref_opt_val else "sat"

    return "pass", sol_opt
