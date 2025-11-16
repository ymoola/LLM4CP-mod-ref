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
def cr3_verify_func(data_dict, hypothesis_solution):
    """
    Verify base constraints with relaxed capacities and objective:
    - Demand satisfaction
    - Option consistency
    - Count actual violations against at_most/per_slots
    - Confirm reported and computed total_violations match expected (12)
    """
    at_most = data_dict["at_most"]
    per_slots = data_dict["per_slots"]
    demand = data_dict["demand"]
    requires = np.array(data_dict["requires"])

    try:
        seq = hypothesis_solution["sequence"]
        total_violations = hypothesis_solution["total_violations"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    n_cars = sum(demand)
    n_types = len(demand)
    n_options = len(at_most)

    # 1. Length check
    assert len(seq) == n_cars, f"Error: Expected {n_cars} cars, got {len(seq)}."

    # 2. Demand satisfaction
    counts = Counter(seq)
    for t in range(n_types):
        expected = demand[t]
        actual = counts.get(t, 0)
        assert actual == expected, f"Error: Expected {expected} of type {t}, got {actual}."

    # 3. Option consistency
    for s in range(n_cars):
        for o in range(n_options):
            val = requires[seq[s], o]
            assert val in [0, 1], f"Error: Invalid option flag {val} for type {seq[s]}."

    # 4. Count constraint violations
    computed_viol = 0
    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            window = seq[s:s + per_slots[o]]
            used = sum(requires[t, o] for t in window)
            if used > at_most[o]:
                computed_viol += 1

    # 5. Verify internal consistency
    assert computed_viol == total_violations, (
        f"Error: Reported total_violations={total_violations}, recomputed={computed_viol}."
    )

    # 6. Verify objective matches reference model (expected 12)
    expected_violations = 12
    assert total_violations == expected_violations, (
        f"Error: Expected total_violations={expected_violations}, but got {total_violations}."
    )

    return "pass"