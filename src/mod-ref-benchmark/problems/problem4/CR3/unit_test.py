import traceback
from collections import Counter
import numpy as np

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
    Verification for Warehouse Location Problem — CR3 (Capacity Expansion).
    """

    capacities = data_dict["capacities"]
    cap_expanded = data_dict["capacity_expanded"]
    upgrade_cost = data_dict["upgrade_cost"]
    fixed_cost = data_dict["fixed_cost"]
    supply_cost = np.array(data_dict["supply_cost"])

    try:
        w = hypothesis_solution["w"]
        o = hypothesis_solution["o"]
        u = hypothesis_solution["upgrade"]
        total_cost = hypothesis_solution["total_cost"]
    except Exception as e:
        return f"solFormatError: {e}"

    n_stores = supply_cost.shape[0]
    n_warehouses = supply_cost.shape[1]

    # 1. Format validation
    assert len(w) == n_stores, (
        f"Error: Expected {n_stores} assignments, got {len(w)}."
    )
    assert len(o) == n_warehouses, (
        f"Error: Expected {n_warehouses} warehouse-open flags, got {len(o)}."
    )
    assert len(u) == n_warehouses, (
        f"Error: Expected {n_warehouses} upgrade flags, got {len(u)}."
    )

    # 2. Opening constraint: o[w[i]] must be 1
    for i in range(n_stores):
        assigned = w[i]
        assert 0 <= assigned < n_warehouses, (
            f"Error: Store {i} assigned to invalid warehouse {assigned}."
        )
        assert o[assigned] == 1, (
            f"Error: Store {i} assigned to warehouse {assigned} but o[{assigned}] = 0."
        )

    # 3. Capacity constraints under upgrades
    for j in range(n_warehouses):
        assigned_count = sum(1 for i in range(n_stores) if w[i] == j)
        cap_normal = capacities[j]
        cap_exp = cap_expanded[j]
        max_cap = cap_normal + u[j] * (cap_exp - cap_normal)

        assert assigned_count <= max_cap, (
            f"Error: Warehouse {j} has {assigned_count} assigned stores "
            f"but capacity is {max_cap} under upgrade flag u[{j}]={u[j]}."
        )

    # ------------------------------
    # 4. Supply-cost correctness
    # ------------------------------
    recomputed_supply_cost = 0
    for i in range(n_stores):
        recomputed_supply_cost += supply_cost[i, w[i]]

    # ------------------------------
    # 5. Opening & upgrade cost correctness
    # ------------------------------
    open_cost_component = sum(o[j] * fixed_cost for j in range(n_warehouses))
    upgrade_cost_component = sum(u[j] * upgrade_cost[j] for j in range(n_warehouses))

    recomputed_total_cost = (
        recomputed_supply_cost +
        open_cost_component +
        upgrade_cost_component
    )

    assert recomputed_total_cost == total_cost, (
        f"Error: Reported total_cost={total_cost}, "
        f"but recomputed={recomputed_total_cost}."
    )

    z = recomputed_total_cost

    ref_opt_val = 392
    sol_opt = "optimal" if z ==ref_opt_val else "sat"
    return "pass", sol_opt