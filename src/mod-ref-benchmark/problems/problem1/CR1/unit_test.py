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
def cr1_verify_func(data_dict, hypothesis_solution):
    """
    Verify base car sequencing constraints + CR1 constraint:
    - Demand satisfaction
    - Option consistency
    - Capacity per option
    - No consecutive identical car types
    """
    # Load parameters
    at_most = data_dict["at_most"]
    per_slots = data_dict["per_slots"]
    demand = data_dict["demand"]
    requires = np.array(data_dict["requires"])

    try:
        seq = hypothesis_solution["sequence"]
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

    # 3. Option capacity
    for o in range(n_options):
        for s in range(n_cars - per_slots[o]):
            window = seq[s:s + per_slots[o]]
            count = sum(requires[t, o] for t in window)
            assert count <= at_most[o], (
                f"Error: Option {o} exceeds limit {at_most[o]} in window starting at {s}."
            )

    # 4. CR1 constraint: no consecutive identical types
    for i in range(len(seq) - 1):
        assert seq[i] != seq[i + 1], f"Error: Found consecutive identical types at positions {i},{i+1}."

    return "pass"