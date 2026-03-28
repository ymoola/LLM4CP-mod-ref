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
def cr2_verify_func(data_dict, hypothesis_solution):
    n_items = data_dict["n_items"]
    bid_values = data_dict["bid_values"]
    bid_items = data_dict["bid_items"]
    bid_variants = data_dict["bid_variants"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_bids = len(bid_values)

    try:
        selected_bids = hypothesis_solution["selected_bids"]
        chosen_variants = hypothesis_solution["chosen_variants"]
        revenue = hypothesis_solution["revenue"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert isinstance(selected_bids, list), "selected_bids must be a list"
    assert isinstance(chosen_variants, list), "chosen_variants must be a list"
    assert len(chosen_variants) == n_bids, (
        f"chosen_variants must have length {n_bids}, got {len(chosen_variants)}"
    )
    assert isinstance(revenue, int), "revenue must be an int"
    assert revenue >= 0, "revenue must be non-negative"

    selected_set = set()
    for idx, b in enumerate(selected_bids):
        assert isinstance(b, int), f"selected_bids[{idx}] must be an int"
        assert 0 <= b < n_bids, f"selected_bids[{idx}]={b} out of range [0, {n_bids - 1}]"
        assert b not in selected_set, f"selected_bids contains duplicate bid index {b}"
        selected_set.add(b)

    # 1) Input consistency checks relevant to the CR
    assert len(bid_items) == n_bids, "bid_items must have the same length as bid_values"
    assert len(bid_variants) == n_bids, "bid_variants must have the same length as bid_values"
    for b in range(n_bids):
        assert bid_variants[b], f"bid_variants[{b}] must be non-empty"
        assert bid_items[b] == bid_variants[b][0], (
            f"bid_items[{b}] must match bid_variants[{b}][0]"
        )

    # 2) CR2 variant-choice validity
    implied_selected = set()
    chosen_bundles = []
    for b in range(n_bids):
        choice = chosen_variants[b]
        assert isinstance(choice, int), f"chosen_variants[{b}] must be an int"
        if choice == -1:
            assert b not in selected_set, (
                f"Bid {b} is marked selected but chosen_variants[{b}] = -1"
            )
            continue

        assert 0 <= choice < len(bid_variants[b]), (
            f"chosen_variants[{b}]={choice} out of range for bid {b}"
        )
        implied_selected.add(b)
        assert b in selected_set, (
            f"Bid {b} has a chosen variant but is missing from selected_bids"
        )
        chosen_bundles.append((b, bid_variants[b][choice]))

    assert implied_selected == selected_set, (
        f"selected_bids={sorted(selected_set)} does not match chosen_variants selection {sorted(implied_selected)}"
    )

    # 3) Global feasibility of the chosen variants
    used_items = set()
    for b, bundle in chosen_bundles:
        for item in bundle:
            assert 1 <= item <= n_items, f"Bid {b} contains invalid item {item}"
            assert item not in used_items, (
                f"Item {item} is used by more than one chosen variant."
            )
            used_items.add(item)

    # 4) Objective consistency
    recomputed_revenue = sum(bid_values[b] for b in selected_bids)
    assert revenue == recomputed_revenue, (
        f"revenue={revenue}, recomputed={recomputed_revenue}."
    )

    # 5) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided"
        sol_opt = "optimal" if revenue == ref_opt_val else "sat"

    return "pass", sol_opt
