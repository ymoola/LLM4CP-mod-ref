import traceback
from collections import Counter

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

    n_slots = data_dict["n_slots"]
    n_templates = data_dict["n_templates"]
    n_var = data_dict["n_var"]
    demand = data_dict["demand"]

    try:
        layout = hypothesis_solution["layout"]
        production = hypothesis_solution["production"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # === 1. Dimension checks ===
    assert len(layout) == n_templates, "Layout row count mismatch."
    assert all(len(row) == n_var for row in layout), "Layout column size mismatch."
    assert len(production) == n_templates, "Production size mismatch."

    # === 2. Slot fill ===
    for i in range(n_templates):
        assert sum(layout[i]) == n_slots, f"Template {i} violates slot count."

    # === 3. Demand satisfaction ===
    for v in range(n_var):
        total = sum(layout[i][v] * production[i] for i in range(n_templates))
        assert total >= demand[v], f"Variation {v} demand unmet."

    # === 4. CR2: Minimum template diversity ===
    for i in range(n_templates):
        distinct = sum(1 for x in layout[i] if x > 0)
        assert distinct >= 3, f"Template {i} contains fewer than 3 variations."

    ref_opt_val = 420

    z = sum(production)
    sol_opt = "optimal" if z ==ref_opt_val else "sat"
    return "pass", sol_opt