import traceback
import numpy as np

def handle_assertions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrapper


@handle_assertions
def cr2_verify_func(data_dict, hypothesis_solution):

    capacities = data_dict["capacities"]
    supply_cost = np.array(data_dict["supply_cost"])
    fixed_cost = data_dict["fixed_cost"]
    allowed = data_dict["allowed"]

    try:
        w = hypothesis_solution["w"]
        o = hypothesis_solution["o"]
        total_cost = hypothesis_solution["total_cost"]
    except Exception as e:
        return f"solFormatError: {e}"

    n_stores = supply_cost.shape[0]
    n_warehouses = supply_cost.shape[1]

    # 1. Length checks
    assert len(w) == n_stores, f"Error: Expected {n_stores} assignments, got {len(w)}"
    assert len(o) == n_warehouses, f"Error: Expected {n_warehouses} open flags, got {len(o)}"


    # 2. Feasibility constraint: allowed[i][w[i]] = 1
    for i in range(n_stores):
        wh = w[i]
        assert 0 <= wh < n_warehouses, f"Error: invalid warehouse index {wh}"
        assert allowed[i][wh] == 1, (
            f"Error: store {i} assigned to warehouse {wh} which is not allowed"
        )


    # 3. Capacity constraints
    for j in range(n_warehouses):
        assigned = sum(w[i] == j for i in range(n_stores))
        assert assigned <= capacities[j], (
            f"Error: warehouse {j} exceeds capacity ({assigned} > {capacities[j]})"
        )


    # 4. Consistency: warehouse must be open
    for j in range(n_warehouses):
        if any(w[i] == j for i in range(n_stores)):
            assert o[j] == 1, f"Error: warehouse {j} serves stores but is not open"


    # 5. Recompute the objective value
    recomputed_supply_cost = sum(supply_cost[i, w[i]] for i in range(n_stores))
    open_cost = sum(o[j] * fixed_cost for j in range(n_warehouses))
    recomputed_total = recomputed_supply_cost + open_cost

    # must match reported cost
    assert recomputed_total == total_cost, (
        f"Error: reported total_cost={total_cost}, recomputed={recomputed_total}"
    )


    # 6. Optimality check
    ref_opt_val = 432
    sol_opt = "optimal" if total_cost == ref_opt_val else "sat"
    return "pass", sol_opt