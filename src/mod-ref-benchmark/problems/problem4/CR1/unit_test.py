import traceback
from collections import Counter
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
def cr1_verify_func(data_dict, hypothesis_solution):

    fixed_cost = data_dict["fixed_cost"]
    capacities = data_dict["capacities"]
    supply_cost = np.array(data_dict["supply_cost"])
    revenue = np.array(data_dict["revenue"])

    try:
        w = hypothesis_solution["w"]
        o = hypothesis_solution["o"]
        profit = hypothesis_solution["profit"]
    except Exception as e:
        return f"solFormatError: {e}"

    n_stores = supply_cost.shape[0]
    n_warehouses = supply_cost.shape[1]


    # 1. Dimension checks
    assert len(w) == n_stores, f"Error: expected {n_stores} assignments, got {len(w)}"
    assert len(o) == n_warehouses, f"Error: expected {n_warehouses} open flags, got {len(o)}"
    assert len(revenue) == n_stores, "Error: revenue must have one value per store"


    # 2. Validate store assignments
    for i in range(n_stores):
        wh = w[i]
        assert 0 <= wh < n_warehouses, f"Error: invalid warehouse index w[{i}]={wh}"


    # 3. Capacity constraints
    counts = Counter(w)
    for j in range(n_warehouses):
        assigned = counts[j]
        assert assigned <= capacities[j], (
            f"Error: warehouse {j} exceeds capacity {assigned} > {capacities[j]}"
        )


    # 4. Serving warehouse must be open
    for i in range(n_stores):
        assert o[w[i]] == 1, (
            f"Error: store {i} is assigned to warehouse {w[i]} which is closed"
        )


    # 5. Recompute profit
    total_revenue = sum(revenue)
    total_opening_cost = sum(o[j] * fixed_cost for j in range(n_warehouses))
    total_supply_cost = sum(supply_cost[i, w[i]] for i in range(n_stores))

    recomputed_profit = total_revenue - total_opening_cost - total_supply_cost

    assert recomputed_profit == profit, (
        f"Error: reported profit={profit}, recomputed={recomputed_profit}"
    )


    # 6. Optimality check
    ref_opt_val = 537
    sol_opt = "optimal" if profit == ref_opt_val else "sat"

    return "pass", sol_opt