import traceback

def handle_assertions(fn):
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            return {
                "err": repr(str(e)),
                "err_trace": repr(''.join(traceback.format_exception(None, e, e.__traceback__)))
            }
    return wrap

@handle_assertions
def cr1_verify_func(data_dict, hypothesis_solution):
    n_slots = data_dict["n_slots"]
    n_templates = data_dict["n_templates"]
    n_var = data_dict["n_var"]
    demand = data_dict["demand"]
    alpha_num = data_dict["alpha_num"]
    alpha_den = data_dict["alpha_den"]

    try:
        production = hypothesis_solution["production"]
        layout = hypothesis_solution["layout"]
    except:
        return "solFormatError"

    # Shape checks
    assert len(layout) == n_templates, "Layout row count mismatch."
    assert all(len(row) == n_var for row in layout), "Layout column size mismatch."
    assert len(production) == n_templates, "Production size mismatch."

    # Slot fill
    for i in range(n_templates):
        assert sum(layout[i]) == n_slots, f"Template {i} violates slot count."

    # Demand satisfaction
    for v in range(n_var):
        total = sum(production[i] * layout[i][v] for i in range(n_templates))
        assert total >= demand[v], f"Variation {v} demand unmet."

    # CR1: load balance constraint
    for i in range(n_templates):
        for j in range(n_templates):
            assert production[i] * alpha_den <= production[j] * alpha_num, f"Template {i} violates load balance constraint"

    ref_opt_val = 723

    z = sum(production)
    sol_opt = "optimal" if z ==ref_opt_val else "sat"
    return "pass", sol_opt