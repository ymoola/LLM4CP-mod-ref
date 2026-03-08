import traceback


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
    Verify Problem 10 CR1:
    - Base constraints: patient count bounds, one-zone-per-nurse, workload cap
    - CR1 workload definition: type-and-nurse dependent effort matrix
    - Objective consistency terms: total_workload and variance_numerator
    """
    n_nurses = data_dict["n_nurses"]
    min_patients_per_nurse = data_dict["min_patients_per_nurse"]
    max_patients_per_nurse = data_dict["max_patients_per_nurse"]
    max_workload_per_nurse = data_dict["max_workload_per_nurse"]
    patient_type = data_dict["patient_type"]
    patient_zone = data_dict["patient_zone"]
    workload_by_type_nurse = data_dict["workload_by_type_nurse"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_patients = len(patient_type)

    try:
        patient_assignment = hypothesis_solution["patient_assignment"]
        workload = hypothesis_solution["workload"]
        total_workload = hypothesis_solution["total_workload"]
        variance_numerator = hypothesis_solution["variance_numerator"]
    except Exception as e:
        return f"solFormatError: {str(e)}"

    # 1) Basic format checks
    assert isinstance(patient_assignment, list), "patient_assignment must be a list"
    assert isinstance(workload, list), "workload must be a list"
    assert len(patient_assignment) == n_patients, (
        f"Error: Expected patient_assignment length {n_patients}, got {len(patient_assignment)}."
    )
    assert len(workload) == n_nurses, (
        f"Error: Expected workload length {n_nurses}, got {len(workload)}."
    )
    assert isinstance(total_workload, int), "total_workload must be an int"
    assert isinstance(variance_numerator, int), "variance_numerator must be an int"
    assert total_workload >= 0, "total_workload must be non-negative"
    assert variance_numerator >= 0, "variance_numerator must be non-negative"

    # Data consistency checks
    assert len(patient_zone) == n_patients, "patient_type and patient_zone length mismatch"
    n_types = len(workload_by_type_nurse)
    assert n_types > 0, "workload_by_type_nurse must be non-empty"
    for t in range(n_types):
        assert len(workload_by_type_nurse[t]) == n_nurses, (
            f"Error: workload_by_type_nurse[{t}] must have length {n_nurses}."
        )
    for i, t in enumerate(patient_type):
        assert isinstance(t, int) and 0 <= t < n_types, (
            f"Error: patient_type[{i}]={t} out of range [0, {n_types - 1}]."
        )

    # 2) Assignment domain + patient count bounds
    for i, k in enumerate(patient_assignment):
        assert isinstance(k, int), f"Error: patient_assignment[{i}] must be int."
        assert 0 <= k < n_nurses, (
            f"Error: patient_assignment[{i}]={k} out of range [0, {n_nurses - 1}]."
        )

    nurse_counts = [0] * n_nurses
    for k in patient_assignment:
        nurse_counts[k] += 1

    for k in range(n_nurses):
        assert min_patients_per_nurse <= nurse_counts[k] <= max_patients_per_nurse, (
            f"Error: nurse {k} has {nurse_counts[k]} patients; expected in "
            f"[{min_patients_per_nurse}, {max_patients_per_nurse}]."
        )

    # 3) One-zone-per-nurse (base constraint)
    for k in range(n_nurses):
        zones = {patient_zone[i] for i in range(n_patients) if patient_assignment[i] == k}
        assert len(zones) <= 1, f"Error: nurse {k} serves multiple zones: {sorted(zones)}"

    # 4) Recompute type-dependent workloads and compare
    recomputed_workload = [0] * n_nurses
    for i in range(n_patients):
        k = patient_assignment[i]
        t = patient_type[i]
        recomputed_workload[k] += workload_by_type_nurse[t][k]

    for k in range(n_nurses):
        assert isinstance(workload[k], int), f"Error: workload[{k}] must be int."
        assert workload[k] == recomputed_workload[k], (
            f"Error: workload[{k}]={workload[k]}, recomputed={recomputed_workload[k]}."
        )
        assert workload[k] <= max_workload_per_nurse, (
            f"Error: workload cap violated for nurse {k}: {workload[k]} > {max_workload_per_nurse}."
        )
        assert workload[k] >= 0, f"Error: workload[{k}] must be non-negative."

    # 5) Objective term consistency
    recomputed_total = sum(recomputed_workload)
    assert total_workload == recomputed_total, (
        f"Error: total_workload={total_workload}, recomputed={recomputed_total}."
    )

    recomputed_var_num = (
        n_nurses * sum(wk * wk for wk in recomputed_workload)
        - recomputed_total * recomputed_total
    )
    assert variance_numerator == recomputed_var_num, (
        f"Error: variance_numerator={variance_numerator}, recomputed={recomputed_var_num}."
    )

    # 6) Optional optimality tag against scalarized objective used by reference model
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided."
        objective = total_workload + variance_numerator
        sol_opt = "optimal" if objective == ref_opt_val else "sat"

    return "pass", sol_opt
