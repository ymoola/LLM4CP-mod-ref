import traceback
from collections import Counter

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

    # Load data
    n_tasks = data_dict["n_tasks"]
    shifts = data_dict["shifts"]
    shift_durations = data_dict["shift_durations"]
    H = data_dict["H"]

    try:
        x = hypothesis_solution["x"]
    except Exception:
        return "solFormatError: missing key 'x'"

    n_shifts = len(shifts)

    # 1. Format checks 
    assert len(x) == n_shifts, f"Error: expected x of length {n_shifts}, got {len(x)}"
    assert all(v in [0,1] for v in x), "Error: x must contain only 0/1 values"

    # 2. Coverage constraint 
    for t in range(n_tasks):
        covering = [i for i in range(n_shifts) if t in shifts[i]]
        assert len(covering) > 0, f"Task {t} has no covering shift"
        covered_count = sum(x[i] for i in covering)
        assert covered_count == 1, f"Task {t} covered {covered_count} times (must be 1)"

    # 3. Duration constraint 
    total_duration = sum(x[i] * shift_durations[i] for i in range(n_shifts))
    assert total_duration <= H, (
        f"Total duration {total_duration} exceeds limit H={H}"
    )

   # 4. Objective recomputation (sum of selected shifts)
    z = sum(x)
     
    ref_opt_val = 7
    sol_opt = "optimal" if z ==ref_opt_val else "sat"
    return "pass", sol_opt