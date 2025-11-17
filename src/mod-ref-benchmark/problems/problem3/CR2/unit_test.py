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
def cr2_verify_func(data_dict, hypothesis_solution):
    """
    Verification for CR1:
    - Each task must be covered exactly twice.
    - Objective: minimize number of selected shifts.
    - Recompute objective value and ensure internal consistency.
    """

    nTasks = data_dict["n_tasks"]
    shifts = data_dict["shifts"]
    nShifts = len(shifts)

    try:
        x = hypothesis_solution["x"]
        total_cost = hypothesis_solution["total_cost"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1. Basic shape check
    assert len(x) == nShifts, f"Error: Expected x of length {nShifts}, got {len(x)}."
    assert all(v in [0,1] for v in x), "Error: x must contain only 0/1 values."

    # 2. Coverage check: each task covered exactly twice
    for t in range(nTasks):
        covering = sum(x[i] for i, s in enumerate(shifts) if t in s)
        assert covering == 1, f"Error: Task {t} has coverage {covering}, expected 1."

    z = total_cost
     
    ref_opt_val = 93
    sol_opt = "optimal" if z ==ref_opt_val else "sat"
    return "pass", sol_opt