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
def cr2_verify_func(data_dict, hypothesis_solution):
    """
    Verify Problem 10 CR2:
    - Base constraints kept: patient count bounds, workload cap
    - CR2 change: one-zone-per-nurse restriction is removed
    - CR2 objective terms: total_workload and total_travel_cost
    """
    n_nurses = data_dict["n_nurses"]
    min_patients_per_nurse = data_dict["min_patients_per_nurse"]
    max_patients_per_nurse = data_dict["max_patients_per_nurse"]
    max_workload_per_nurse = data_dict["max_workload_per_nurse"]
    patient_acuity = data_dict["patient_acuity"]
    patient_zone = data_dict["patient_zone"]
    zone_distance = data_dict["zone_distance"]
    ref_opt_val = data_dict.get("ref_opt_val", None)

    n_patients = len(patient_acuity)

    try:
        patient_assignment = hypothesis_solution["patient_assignment"]
        workload = hypothesis_solution["workload"]
        total_workload = hypothesis_solution["total_workload"]
        total_travel_cost = hypothesis_solution["total_travel_cost"]
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
    assert isinstance(total_travel_cost, int), "total_travel_cost must be an int"
    assert total_workload >= 0, "total_workload must be non-negative"
    assert total_travel_cost >= 0, "total_travel_cost must be non-negative"

    # 2) Data consistency checks
    assert len(patient_zone) == n_patients, "patient_acuity and patient_zone length mismatch"
    n_zones = len(zone_distance)
    assert n_zones > 0, "zone_distance must be non-empty"
    for z in range(n_zones):
        assert len(zone_distance[z]) == n_zones, "zone_distance must be square"
    for i, z in enumerate(patient_zone):
        assert isinstance(z, int) and 0 <= z < n_zones, (
            f"Error: patient_zone[{i}]={z} out of range [0, {n_zones - 1}]."
        )

    # 3) Assignment domain + patient count bounds
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

    # 4) Recompute workload from patient_acuity and compare
    recomputed_workload = [0] * n_nurses
    for i in range(n_patients):
        k = patient_assignment[i]
        recomputed_workload[k] += patient_acuity[i]

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
    recomputed_total_workload = sum(recomputed_workload)
    assert total_workload == recomputed_total_workload, (
        f"Error: total_workload={total_workload}, recomputed={recomputed_total_workload}."
    )

    recomputed_total_travel = 0
    for i in range(n_patients):
        for j in range(i + 1, n_patients):
            if patient_assignment[i] == patient_assignment[j]:
                recomputed_total_travel += zone_distance[patient_zone[i]][patient_zone[j]]

    assert total_travel_cost == recomputed_total_travel, (
        f"Error: total_travel_cost={total_travel_cost}, recomputed={recomputed_total_travel}."
    )

    # 6) Optional optimality tag against scalarized objective used by reference model
    sol_opt = "sat"
    if ref_opt_val is not None:
        assert isinstance(ref_opt_val, int), "ref_opt_val must be an int when provided."
        objective = total_workload + total_travel_cost
        sol_opt = "optimal" if objective == ref_opt_val else "sat"

    return "pass", sol_opt
