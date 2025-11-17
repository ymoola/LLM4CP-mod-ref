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
def cr3_verify_func(data_dict, hypothesis_solution):
    n_slots = data_dict["n_slots"]
    n_templates = data_dict["n_templates"]
    n_var = data_dict["n_var"]
    demand = data_dict["demand"]

    try:
        layout = hypothesis_solution["layout"]
        production = hypothesis_solution["production"]
        max_load = hypothesis_solution["max_load"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    assert len(layout) == n_templates, "Layout row count mismatch."
    assert all(len(row) == n_var for row in layout), "Layout column size mismatch."
    assert len(production) == n_templates, "Production size mismatch."

    # Slot check
    for i in range(n_templates):
        assert sum(layout[i]) == n_slots, f"Template {i} violates slot count."

    # Demand satisfaction
    for v in range(n_var):
        total = sum(production[i] * layout[i][v] for i in range(n_templates))
        assert total >= demand[v], f"Variation {v} demand unmet."

    # CR3: verify max_load
    assert max(production) == max_load, "max_load does not match max(production)"

    return "pass"