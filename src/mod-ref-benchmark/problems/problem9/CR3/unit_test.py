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
    """
    Verify Problem 9 CR3 (subset loading with value maximization):
    - Output format checks
    - Loaded containers are inside deck
    - Loaded container pairs satisfy non-overlap + class separation
    - Reported objective consistency: total_value = sum(priority[i] * load[i])
    """
    deck_width = data_dict["deck_width"]
    deck_length = data_dict["deck_length"]
    n_containers = data_dict["n_containers"]
    width = data_dict["width"]
    length = data_dict["length"]
    classes = data_dict["classes"]
    separation = data_dict["separation"]
    priority = data_dict["priority"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    try:
        x = hypothesis_solution["x"]
        y = hypothesis_solution["y"]
        load = hypothesis_solution["load"]
        total_value = hypothesis_solution["total_value"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic shape checks
    assert len(x) == n_containers, f"Error: x must have length {n_containers}."
    assert len(y) == n_containers, f"Error: y must have length {n_containers}."
    assert len(load) == n_containers, f"Error: load must have length {n_containers}."
    assert len(width) == n_containers, "Error: width length mismatch."
    assert len(length) == n_containers, "Error: length length mismatch."
    assert len(classes) == n_containers, "Error: classes length mismatch."
    assert len(priority) == n_containers, "Error: priority length mismatch."
    assert isinstance(total_value, int), "Error: total_value must be an int."

    n_classes = len(separation)
    for row in separation:
        assert len(row) == n_classes, "Error: separation must be a square matrix."

    # 2) Domain checks + in-deck checks for loaded containers
    load01 = [0] * n_containers
    for i in range(n_containers):
        assert isinstance(x[i], int), f"Error: x[{i}] must be int."
        assert isinstance(y[i], int), f"Error: y[{i}] must be int."
        assert 0 <= x[i] <= deck_width, f"Error: x[{i}] out of deck range."
        assert 0 <= y[i] <= deck_length, f"Error: y[{i}] out of deck range."

        li = load[i]
        if isinstance(li, bool):
            li = int(li)
        assert isinstance(li, int) and li in [0, 1], f"Error: load[{i}] must be 0/1."
        load01[i] = li

        if load01[i] == 1:
            assert x[i] + width[i] <= deck_width, (
                f"Error: loaded container {i} exceeds deck width."
            )
            assert y[i] + length[i] <= deck_length, (
                f"Error: loaded container {i} exceeds deck length."
            )

    # 3) Non-overlap with separation only for loaded pairs
    for i in range(n_containers):
        c1 = classes[i] - 1
        assert 0 <= c1 < n_classes, f"Error: invalid class for container {i}."
        for j in range(i + 1, n_containers):
            if load01[i] == 1 and load01[j] == 1:
                c2 = classes[j] - 1
                assert 0 <= c2 < n_classes, f"Error: invalid class for container {j}."
                sep = separation[c1][c2]
                assert isinstance(sep, int) and sep >= 0, (
                    "Error: separation values must be non-negative integers."
                )

                disjoint = (
                    (x[i] + width[i] + sep <= x[j]) or
                    (x[j] + width[j] + sep <= x[i]) or
                    (y[i] + length[i] + sep <= y[j]) or
                    (y[j] + length[j] + sep <= y[i])
                )
                assert disjoint, (
                    f"Error: loaded containers {i} and {j} overlap or violate separation requirement."
                )

    # 4) Objective consistency
    recomputed_value = sum(priority[i] * load01[i] for i in range(n_containers))
    assert total_value == recomputed_value, (
        f"Error: reported total_value={total_value}, recomputed={recomputed_value}."
    )

    # 5) Optional optimality tag
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided."
        sol_opt = "optimal" if total_value == ref_opt_val else "sat"

    return "pass", sol_opt
